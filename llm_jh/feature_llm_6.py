"""
7. state 기반으로 평가를 위한 이전 질문 추적 방식 변경
"""
import os   
import json
import numpy as np
from dotenv import load_dotenv
from typing import Dict, List, TypedDict, Literal, Any
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from datetime import datetime

class ConversationState(TypedDict):
    messages: List[Dict[str, str]]          
    current_message: str                    
    task_scores: Dict[str, float]          
    selected_task: str                      
    task_message_relevance: float           
    generated_questions: List[str]          
    question_similarities: List[float]     
    selected_question: str                 
    question_message_relevance: float      
    conversation_mode: Literal["assessment", "casual"] 
    ai_response: str                       
    response_type: str                     
    workflow_stage: str                                 
    # 채점 관련 필드
    is_assessment_answer: bool             # 현재 메시지가 assessment 답변인지
    last_assessment_question: str          # 마지막으로 한 assessment 질문
    last_assessment_task: str              # 마지막 assessment의 task 타입
    assessment_score: float                # 답변 점수 (0-1)
    score_details: Dict[str, Any]          # 상세 채점 결과

@dataclass
class ChatbotConfig:
    openai_api_key: str                     
    assessment_threshold: float = 0.3       
    fallback_threshold: float = 0.6         
    model_name: str = "gpt-4o-mini"
    max_retries: int = 2                   

ASSESSMENT_TASKS = {
    "registration_recall": {
        "description": 
        """기억 등록은 즉각적인 기억력을 평가하고, 회상은 기억을 유지하는 능력을 평가하는 항목입니다.
          messages 최근 5개 turn 내에서 동일 선상에서 비교될 수 있는 단어/고유명사가 3개 이상 나오면 본 평가내역을 활용합니다.""",
        "example_questions": [
            "아까 말씀하신 과일 중 사과, 배, 포도를 어릴 때 가장 좋아했던 순서대로 말씀해주세요.",
            "아까 말씀하신 자녀 중 영희, 철수, 길동이를 살가운 순서대로 말씀해주시겠어요?",
            "아까 말씀하신 공책, 필통, 샤프를 어릴 적 갖고 싶었던 순서대로 말씀해주세요.",
            "콩, 생선, 고추들을 어릴 적 싫어했던 순서대로 말씀해주세요.",
            "콩, 생선, 고추들을 요즘 좋아하시는 순서대로 말씀해주세요."
        ],
        "scoring_criteria": {
            "keywords": ["콩", "생선", "고추"],  # 예시 답변 키워드들
            "required_count": 3,  # 필요한 키워드 개수
            "scoring_type": "registration_recall"  # 채점 방식
        }
    },
    "Naming": {
        "description": 
        """표시된 사물의 이름을 기억해내는 능력을 평가합니다. 
        사진데이터에서 위치관계가 명확한 사물이 있을 경우 본 평가 항목을 사용하기 적당합니다.""",
        "example_questions": [
            "사진 속 어린아이가 들고있는 물체를 뭐라고 불러요?",
            "손가락에 끼고 있는 것의 이름은 뭔가요?",
            "친구가 가지고 놀고 있는 물건의 이름은 뭐에요?",
            "사진 속 할머니 옆에 있는 꽃의 이름은 뭔가요?",
            "아이가 안고 있는 동물의 이름은 뭐에요?",
            "케이크 밑에 있는 가구 이름은 뭔가요?"
        ],
        "scoring_criteria": {
            "expected_answers": ["테이블", "탁자", "책상", "식탁"],  # 예상 정답들
            "scoring_type": "Naming"  # 채점 방식
        }
    },
    "time_orientation": {
        "description": 
        """현재 자신이 놓여있는 시간, 날짜, 계절 등의 상황을 올바르게 인식하는 능력을 평가합니다.
        시간 관련 humanmassage가 본 평가항목에 대한 트리거가 됩니다.
        example_questions의 응용을 최소화하여 질문을 생성하세요.
        """,
        "example_questions": [
            "오늘은 몇일 인가요?"
        ],
        "scoring_criteria": {
            "scoring_type": "time_orientation"  # 채점 방식
        }
    }
}

load_dotenv()
API_KEY = os.getenv("GPT_API_KEY")

config = ChatbotConfig(
    openai_api_key=API_KEY,  
    assessment_threshold=0.3,
    fallback_threshold=0.6,
    max_retries=1
)

class LangGraphDementiaChatbot:
    def __init__(self, config: ChatbotConfig):
        self.config = config
        self.llm = ChatOpenAI(
            model=config.model_name,
            openai_api_key=config.openai_api_key,
            temperature=0.3
        )
        self.vectorizer = TfidfVectorizer(stop_words='english')
        
        # 그래프 빌드
        self.graph = self._build_graph()
        print(f"LangGraph 치매 평가 챗봇 초기화 완료 (모델: {config.model_name})")

    def _build_graph(self) -> StateGraph:
        """백그라운드 재시도 + 답변 채점 워크플로우 구성 (피드백 제거)"""
        workflow = StateGraph(ConversationState)
        
        # 노드들 추가
        workflow.add_node("check_if_assessment_answer", self.check_if_assessment_answer)
        workflow.add_node("score_assessment_answer", self.score_assessment_answer)
        workflow.add_node("calculate_task_scores", self.calculate_task_scores)
        workflow.add_node("select_best_task", self.select_best_task)
        workflow.add_node("check_assessment_threshold", self.check_assessment_threshold)
        workflow.add_node("generate_questions", self.generate_questions)
        workflow.add_node("calculate_question_similarities", self.calculate_question_similarities)
        workflow.add_node("select_best_question", self.select_best_question)
        workflow.add_node("check_context_relevance", self.check_context_relevance)
        workflow.add_node("output_assessment_question", self.output_assessment_question)
        workflow.add_node("casual_conversation", self.casual_conversation)
        workflow.add_node("casual_with_background_retry", self.casual_with_background_retry)
        
        # 시작점: 먼저 assessment 답변인지 확인
        workflow.set_entry_point("check_if_assessment_answer")
        
        # Assessment 답변 채점 플로우 (피드백 제거 - 바로 기존 플로우로 이어짐)
        workflow.add_conditional_edges(
            "check_if_assessment_answer",
            self._decide_if_scoring_needed,
            {
                "score_answer": "score_assessment_answer",
                "continue_normal": "calculate_task_scores"
            }
        )
        
        # 채점 후 바로 기존 플로우로 이어짐
        workflow.add_edge("score_assessment_answer", "calculate_task_scores")
        
        # 기본 플로우 
        workflow.add_edge("calculate_task_scores", "select_best_task")
        workflow.add_edge("select_best_task", "check_assessment_threshold")
        
        # Assessment vs Casual 분기
        workflow.add_conditional_edges(
            "check_assessment_threshold",
            self._decide_conversation_mode,
            {
                "assessment": "generate_questions",
                "casual": "casual_conversation"
            }
        )
        
        workflow.add_edge("generate_questions", "calculate_question_similarities")
        workflow.add_edge("calculate_question_similarities", "select_best_question")
        workflow.add_edge("select_best_question", "check_context_relevance")
        
        workflow.add_conditional_edges(
            "check_context_relevance",
            self._decide_final_output,
            {
                "assessment": "output_assessment_question",
                "casual_with_retry": "casual_with_background_retry",
                "casual": "casual_conversation"
            }
        )
        
        # 종료 노드들
        workflow.add_edge("output_assessment_question", END)
        workflow.add_edge("casual_conversation", END)
        workflow.add_edge("casual_with_background_retry", END)
        
        return workflow.compile()

    def check_if_assessment_answer(self, state: ConversationState) -> ConversationState:
        """상태 기반 Assessment 답변 확인"""
        print("답변 확인: 상태 기반 Assessment 답변 체크...")
        
        # 상태에서 직접 확인 (빠름)
        is_assessment_answer = state.get("last_question_type") == "assessment"
        last_assessment_task = state.get("last_assessment_task", "")
        
        # 마지막 AI 메시지도 찾아야 함 (채점에서 사용)
        last_ai_message = ""
        messages = state["messages"]
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], AIMessage):
                last_ai_message = messages[i].content
                break
        
        if is_assessment_answer:
            print(f"상태 추적: Assessment 답변 감지! Task: {last_assessment_task}")
        
        return {
            **state,
            "is_assessment_answer": is_assessment_answer,
            "last_assessment_question": last_ai_message,  # 채점에서 필요
            "last_assessment_task": last_assessment_task
        }

    def score_assessment_answer(self, state: ConversationState) -> ConversationState:
        """Assessment 답변 채점 (피드백 없이 점수만 기록)"""
        print("답변 채점 중...")
        
        current_message = state["current_message"]
        task_name = state["last_assessment_task"]
        last_question = state["last_assessment_question"]
        
        task_info = ASSESSMENT_TASKS.get(task_name, {})
        scoring_criteria = task_info.get("scoring_criteria", {})
        scoring_type = scoring_criteria.get("scoring_type", "general")
        
        score = 0.0
        score_details = {}
        
        try:
            if scoring_type == "registration_recall":
                # 키워드 개수 기반 채점 (registration_recall)
                keywords = scoring_criteria.get("keywords", [])
                required_count = scoring_criteria.get("required_count", len(keywords))
                
                found_keywords = []
                for keyword in keywords:
                    if keyword in current_message:
                        found_keywords.append(keyword)
                
                score = len(found_keywords) / required_count
                score = min(1.0, score)  # 1.0 초과 방지
                
                score_details = {
                    "keywords": keywords,
                    "found_keywords": found_keywords,
                    "found_count": len(found_keywords),
                    "required_count": required_count,
                    "missing_keywords": [k for k in keywords if k not in found_keywords]
                }
                
                print(f"키워드 채점: {len(found_keywords)}/{required_count} = {score:.2f}")
                print(f"발견된 키워드: {found_keywords}")
                
            elif scoring_type == "Naming":
                # 사물 이름 맞추기 채점 (Naming)
                expected_answers = scoring_criteria.get("expected_answers", [])
                
                # LLM으로 답변 적절성 평가
                system_msg = f"""답변이 다음 예상 정답들 중 하나와 의미적으로 일치하는지 평가해주세요.

                예상 정답들: {', '.join(expected_answers)}
                사용자 답변: "{current_message}"

                평가 기준:
                - 정확한 단어 일치: 1.0
                - 사투리나 영어로 답변한 경우: 1.0
                - 완전히 틀린 답변: 0.0

                0.0부터 1.0 사이의 점수만 반환해주세요."""

                response = self.llm.invoke([SystemMessage(content=system_msg)])
                
                numbers = re.findall(r'0\.\d+|1\.0|0\.0', response.content)
                if numbers:
                    score = float(numbers[0])
                else:
                    score = 0.0
                
                score_details = {
                    "expected_answers": expected_answers,
                    "user_answer": current_message,
                    "evaluation_response": response.content
                }
                
                print(f"사물 이름 채점: {score:.2f}")
                
            elif scoring_type == "time_orientation":
                # 날짜 정확성 채점 (time_orientation)
                today = datetime.now()
                
                # 숫자 추출
                numbers = re.findall(r'\d+', current_message)
                
                score = 0.0
                if numbers:
                    try:
                        user_day = int(numbers[0])
                        actual_day = today.day
                        
                        if user_day == actual_day:
                            score = 1.0
                        elif abs(user_day - actual_day) <= 1:  # 1일 차이까지 부분 점수
                            score = 0.5
                        else:
                            score = 0.0
                            
                        score_details = {
                            "user_answer": user_day,
                            "correct_answer": actual_day,
                            "difference": abs(user_day - actual_day)
                        }
                        
                    except ValueError:
                        score = 0.0
                        score_details = {"error": "숫자 추출 실패"}
                else:
                    score = 0.0
                    score_details = {"error": "답변에서 날짜를 찾을 수 없음"}
                
                print(f"날짜 정확성 채점: {score:.2f}")
                
            else:
                # 일반적인 LLM 기반 평가
                system_msg = f"""다음 assessment 질문에 대한 답변을 0-1 사이로 평가해주세요.

                질문: "{last_question}"
                답변: "{current_message}"

                평가 기준:
                - 질문에 직접적으로 답변함: 1.0
                - 질문과 관련없는 답변을 하거나 오답: 0.0

                0.0부터 1.0 사이의 점수만 반환해주세요."""

                response = self.llm.invoke([SystemMessage(content=system_msg)])
                
                numbers = re.findall(r'0\.\d+|1\.0|0\.0', response.content)
                if numbers:
                    score = float(numbers[0])
                else:
                    score = 0.0
                
                score_details = {"llm_evaluation": response.content}
                
        except Exception as e:
            print(f"채점 실패: {e}")
            score = 0.0
            score_details = {"error": str(e)}
        
        # 채점 결과를 상태에 저장만 하고 계속 진행
        return {
            **state,
            "assessment_score": score,
            "score_details": score_details
        }

    # === 기존 메서드들 (변경 없음) ===
    
    def calculate_task_scores(self, state: ConversationState) -> ConversationState:
        message = state["current_message"]
        
        # 모든 태스크를 한 번에 평가
        prompt = f"""사용자 메시지: "{message}"

    다음 평가 영역들과의 관련도를 0-1 사이로 평가해주세요:

    1. registration_recall: 기억 등록은 즉각적인 기억력을 평가하는 항목.
          messages 최근 5개 turn 내에서 동일 선상에서 비교될 수 있는 단어/고유명사가 3개 이상 나오면 본 평가내역을 활용.
    
    2. Naming: 사물 이름 맞추기 (사진 속 객체 언급). 표시된 사물의 이름을 기억해내는 능력을 평가합니다. 
        사진데이터에서 위치관계가 명확한 사물이 있을 경우 본 평가 항목을 사용하기 적당합니다.
    
    3. time_orientation: 현재 자신이 놓여있는 시간, 날짜, 계절 등의 상황을 올바르게 인식하는 능력을 평가합니다.
        시간 관련 humanmassage가 본 평가항목에 대한 트리거가 됩니다.

    JSON 형식으로만 응답:
    {{"registration_recall": 0.0, "Naming": 0.0, "time_orientation": 0.0}}"""

        try:
            response = self.llm.invoke([SystemMessage(content=prompt)])
            import json
            task_scores = json.loads(response.content.strip())
        except:
            task_scores = {"registration_recall": 0.0, "Naming": 0.0, "time_orientation": 0.0}
        
        return {**state, "task_scores": task_scores}

    def select_best_task(self, state: ConversationState) -> ConversationState:
        """2. 최적 태스크 선택"""
        print("2단계: 최적 태스크 선택...")
        task_scores = state["task_scores"]
        
        if not task_scores:
            selected_task = "registration_recall"
            task_relevance = 0.0
        else:
            best_task_item = max(task_scores.items(), key=lambda x: x[1])
            selected_task = best_task_item[0]
            task_relevance = best_task_item[1]
        
        print(f"선택된 태스크: {selected_task} (점수: {task_relevance:.2f})")
        
        return {
            **state, 
            "selected_task": selected_task,
            "task_message_relevance": task_relevance
        }

    def check_assessment_threshold(self, state: ConversationState) -> ConversationState:
        """3. 적합도 threshold 체크"""
        print("3단계: Assessment threshold 체크...")
        relevance = state["task_message_relevance"]
        threshold = self.config.assessment_threshold
        
        if relevance >= threshold:
            mode = "assessment"
            print(f"평가 모드 진입 (적합도 {relevance:.2f} >= 임계값 {threshold})")
        else:
            mode = "casual"
            print(f"일상 대화 모드 (적합도 {relevance:.2f} < 임계값 {threshold})")
        
        return {**state, "conversation_mode": mode}

    def generate_questions(self, state: ConversationState) -> ConversationState:
        """4. 예상 질문 생성"""
        retry_count = state.get("retry_count", 0)
        
        if retry_count > 0:
            print(f"4단계: 평가 질문 재생성 ({retry_count}번째 시도)...")
        else:
            print("4단계: 평가 질문 생성...")
            
        messages = state["messages"]
        current_message = state["current_message"]
        task_name = state["selected_task"]
        task_info = ASSESSMENT_TASKS[task_name]
        
        system_msg = f"""당신은 치매 평가 전문가입니다. 
대화 히스토리를 바탕으로 {task_name} 평가를 위한 자연스러운 질문을 생성해주세요.

평가 영역: {task_name}
예시 질문들:
{chr(10).join(task_info["example_questions"])}

위 대화 맥락을 고려하여, {task_name} 평가를 위한 자연스러운 질문 5개를 생성해주세요.
예시 질문들을 참고하되, 사용자와의 대화 흐름에 자연스럽게 이어지도록 만들어주세요.

각 질문을 새 줄로 구분하여 번호 없이 나열해주세요:"""

        conversation_messages = [SystemMessage(content=system_msg)]
        conversation_messages.extend(messages)
        conversation_messages.append(HumanMessage(content=current_message))
        
        try:
            response = self.llm.invoke(conversation_messages)
            
            generated_questions = [q.strip() for q in response.content.split('\n') if q.strip()]
            print(f"생성된 질문 {len(generated_questions)}개:")
            for i, q in enumerate(generated_questions, 1):
                print(f"  {i}. {q}")
                
        except Exception as e:
            print(f"질문 생성 실패: {e}")
            generated_questions = []
        
        return {**state, "generated_questions": generated_questions}

    def calculate_question_similarities(self, state: ConversationState) -> ConversationState:
        """5. 질문-예시 유사성 평가"""
        print("5단계: 질문-예시 유사성 평가...")
        generated_questions = state["generated_questions"]
        task_name = state["selected_task"]
        example_questions = ASSESSMENT_TASKS[task_name]["example_questions"]
        
        if not generated_questions:
            return {**state, "question_similarities": []}
        
        try:
            all_questions = generated_questions + example_questions
            tfidf_matrix = self.vectorizer.fit_transform(all_questions)
            generated_vectors = tfidf_matrix[:len(generated_questions)]
            example_vectors = tfidf_matrix[len(generated_questions):]
            
            similarity_matrix = cosine_similarity(generated_vectors, example_vectors)
            max_similarities = np.max(similarity_matrix, axis=1).tolist()
            
            print("질문별 유사도 점수:")
            for i, (q, score) in enumerate(zip(generated_questions, max_similarities)):
                print(f"  {score:.3f}: {q}")
                
        except Exception as e:
            print(f"유사도 계산 실패: {e}")
            max_similarities = [0.0] * len(generated_questions)
        
        return {**state, "question_similarities": max_similarities}

    def select_best_question(self, state: ConversationState) -> ConversationState:
        """6. 최적 질문 선택"""
        print("6단계: 최적 질문 선택...")
        generated_questions = state["generated_questions"]
        similarities = state["question_similarities"]
        
        if not generated_questions or not similarities:
            return {**state, "selected_question": ""}
        
        best_idx = np.argmax(similarities)
        selected_question = generated_questions[best_idx]
        
        print(f"선택된 질문 (유사도 {similarities[best_idx]:.3f}): {selected_question}")
        
        return {**state, "selected_question": selected_question}

    def check_context_relevance(self, state: ConversationState) -> ConversationState:
        """7. 맥락 타당도 확인"""
        print("7단계: 맥락 타당도 확인...")
        messages = state["messages"]
        current_message = state["current_message"]
        selected_question = state["selected_question"]
        
        system_msg = f"""당신은 대화 흐름 분석 전문가입니다.
대화 히스토리를 보고, 제안된 질문이 자연스러운 대화 흐름인지 평가해주세요.

제안된 질문: "{selected_question}"

평가 기준:
- 기존 대화의 자연스러운 흐름
- 맥락의 연결성  
- 갑작스럽지 않은 전환
- 노인 사용자가 답변할 수 있는 적절한 질문인지

이 질문이 대화 맥락에 얼마나 자연스러운지 0-1 사이의 점수로 평가해주세요.

중요: 반드시 0.0부터 1.0 사이의 숫자만 반환해주세요. 설명이나 다른 텍스트는 포함하지 마세요.
형식: 0.7 (이런 식으로만 답변)"""

        conversation_messages = [SystemMessage(content=system_msg)]
        conversation_messages.extend(messages)
        conversation_messages.append(HumanMessage(content=current_message))
        
        try:
            response = self.llm.invoke(conversation_messages)
            content = response.content.strip()
            
            import re
            numbers = re.findall(r'0\.\d+|1\.0|0\.0|\d\.\d+', content)
            if numbers:
                question_message_relevance = float(numbers[0])
                question_message_relevance = max(0.0, min(1.0, question_message_relevance))
                print(f"질문-메시지 맥락 점수: {question_message_relevance:.2f}")
            else:
                print(f"점수 추출 실패, 응답: {content[:50]}...")
                question_message_relevance = 0.0
        except Exception as e:
            print(f"맥락 평가 실패: {e}")
            question_message_relevance = 0.0
        
        return {**state, "question_message_relevance": question_message_relevance}

    def output_assessment_question(self, state: ConversationState) -> ConversationState:
        """8. 평가 질문 출력"""
        print("8단계: 평가 질문 출력")
        selected_question = state["selected_question"]
        
        return {
            **state, 
            "ai_response": selected_question,
            "response_type": "assessment",
            "workflow_stage": "assessment_question_output"
        }

    def casual_conversation(self, state: ConversationState) -> ConversationState:
        """일상 대화 처리"""
        print("일상 대화 모드")
        messages = state["messages"]
        current_message = state["current_message"]
        
        system_msg = """
당신은 7~15세 사이 호기심 많고 예의바른 어린이입니다. 노인 사용자와 사진을 보며 대화하고 있습니다.

대화 예시:
사용자: "이 사진 속 강아지가 참 귀엽네"
손자: "정말요! 털이 복슬복슬해서 만지고 싶어요. 어릴 때 키우신 강아지에요?"

할머니: "꽃이 예쁘게 피었구나"  
손자: "진짜요! 향기도 좋을 것 같고요. 꽃 좋아하세요? 저는 좋아해요!"

최대한 사용자가 대화를 주도할 수 있도록 사용자에게 공감하며, 자연스럽고 호기심 어린 반응으로 대화를 이어가세요.
"""

        conversation_messages = [SystemMessage(content=system_msg)]
        conversation_messages.extend(messages)
        conversation_messages.append(HumanMessage(content=current_message))
        
        try:
            response = self.llm.invoke(conversation_messages)
            ai_response = response.content.strip()
            response_type = "casual"
        except Exception as e:
            print(f"일상 대화 생성 실패: {e}")
            ai_response = "응답 생성에 실패했습니다."
            response_type = "error"
        
        return {
            **state,
            "ai_response": ai_response,
            "response_type": response_type,
            "workflow_stage": "casual_chat"
        }

    def casual_with_background_retry(self, state: ConversationState) -> ConversationState:
        """즉시 casual 응답 제공 + 백그라운드에서 assessment 재시도"""
        print("백그라운드 재시도 모드: 즉시 casual 응답 + 백그라운드 assessment 준비")
        
        messages = state["messages"]
        current_message = state["current_message"]
        retry_count = state.get("retry_count", 0)
        
        # 1. 즉시 casual 응답 생성
        casual_system_msg = """
당신은 7~15세 사이 호기심 많고 예의바른 어린이입니다. 노인 사용자와 사진을 보며 대화하고 있습니다.

대화 예시:
사용자: "이 사진 속 강아지가 참 귀엽네"
손자: "정말요! 털이 복슬복슬해서 만지고 싶어요. 어릴 때 키우신 강아지에요?"

할머니: "꽃이 예쁘게 피었구나"  
손자: "진짜요! 향기도 좋을 것 같고요. 꽃 좋아하세요? 저는 좋아해요!"

자연스럽고 호기심 어린 반응으로 대화를 이어가세요.
"""
        casual_messages = [SystemMessage(content=casual_system_msg)]
        casual_messages.extend(messages)
        casual_messages.append(HumanMessage(content=current_message))
        
        try:
            casual_response = self.llm.invoke(casual_messages)
            ai_response = casual_response.content.strip()
            print(f"즉시 제공할 casual 응답: {ai_response}")
        except Exception as e:
            print(f"Casual 응답 생성 실패: {e}")
            ai_response = "그렇군요! 더 얘기해 주세요."
        
        # 2. 백그라운드에서 assessment 질문 재시도
        background_question = ""
        background_score = 0.0
        background_ready = False
        
        try:
            print(f"백그라운드에서 {retry_count + 1}번째 assessment 질문 재시도 중...")
            
            task_name = state["selected_task"]
            task_info = ASSESSMENT_TASKS[task_name]
            
            # 백그라운드 질문 생성
            bg_system_msg = f"""당신은 치매 평가 전문가입니다. 
대화 히스토리를 바탕으로 {task_name} 평가를 위한 자연스러운 질문을 생성해주세요.

평가 영역: {task_name}
예시 질문들:
{chr(10).join(task_info["example_questions"])}

{retry_count + 1}번째 시도: 더 자연스럽고 대화 흐름에 맞는 질문을 생성해주세요.
각 질문을 새 줄로 구분하여 번호 없이 나열해주세요:"""

            bg_messages = [SystemMessage(content=bg_system_msg)]
            bg_messages.extend(messages)
            bg_messages.append(HumanMessage(content=current_message))
            
            bg_response = self.llm.invoke(bg_messages)
            bg_questions = [q.strip() for q in bg_response.content.split('\n') if q.strip()]
            
            if bg_questions:
                # 백그라운드 질문 유사도 계산
                example_questions = task_info["example_questions"]
                all_questions = bg_questions + example_questions
                tfidf_matrix = self.vectorizer.fit_transform(all_questions)
                generated_vectors = tfidf_matrix[:len(bg_questions)]
                example_vectors = tfidf_matrix[len(bg_questions):]
                
                similarity_matrix = cosine_similarity(generated_vectors, example_vectors)
                max_similarities = np.max(similarity_matrix, axis=1)
                best_idx = np.argmax(max_similarities)
                bg_selected_question = bg_questions[best_idx]
                
                # 백그라운드 맥락 적합성 평가
                bg_context_system_msg = f"""대화 히스토리를 보고, 제안된 질문이 자연스러운 대화 흐름인지 평가해주세요.

제안된 질문: "{bg_selected_question}"

이 질문이 대화 맥락에 얼마나 자연스러운지 0-1 사이의 점수로 평가해주세요.
중요: 반드시 0.0부터 1.0 사이의 숫자만 반환해주세요.
형식: 0.7"""

                bg_context_messages = [SystemMessage(content=bg_context_system_msg)]
                bg_context_messages.extend(messages)
                bg_context_messages.append(HumanMessage(content=current_message))
                
                bg_context_response = self.llm.invoke(bg_context_messages)
                import re
                numbers = re.findall(r'0\.\d+|1\.0|0\.0|\d\.\d+', bg_context_response.content.strip())
                if numbers:
                    background_score = float(numbers[0])
                    background_score = max(0.0, min(1.0, background_score))
                    background_question = bg_selected_question
                    background_ready = True
                    print(f"백그라운드 질문 준비 완료 (점수: {background_score:.2f}): {background_question}")
                
        except Exception as e:
            print(f"백그라운드 assessment 재시도 실패: {e}")
        
        return {
            **state,
            "ai_response": ai_response,
            "response_type": "casual_with_background_retry",
            "workflow_stage": "casual_with_background_retry",
            "retry_count": retry_count + 1,
            "background_question": background_question,
            "background_score": background_score,
            "background_ready": background_ready
        }

    # === 조건부 엣지 결정 함수들 ===
    
    def _decide_if_scoring_needed(self, state: ConversationState) -> str:
        """Assessment 답변 채점이 필요한지 결정"""
        return "score_answer" if state["is_assessment_answer"] else "continue_normal"
    
    def _decide_conversation_mode(self, state: ConversationState) -> str:
        """대화 모드 결정"""
        return state["conversation_mode"]

    def _decide_final_output(self, state: ConversationState) -> str:
        """최종 출력 형태 결정"""
        relevance = state["question_message_relevance"]
        threshold = self.config.fallback_threshold
        retry_count = state.get("retry_count", 0)
        max_retries = self.config.max_retries
        
        # 임계값을 넘으면 즉시 assessment 질문 출력
        if relevance >= threshold:
            print(f"평가 질문 출력 (맥락 점수 {relevance:.2f} >= 임계값 {threshold})")
            return "assessment"
        
        # 재시도 가능하면 casual 응답하면서 백그라운드에서 재시도
        if retry_count < max_retries:
            print(f"즉시 casual 응답 + 백그라운드 재시도 ({retry_count + 1}/{max_retries + 1})")
            return "casual_with_retry"
        
        # 재시도 한계 도달 - assessment 모드 포기, 순수 casual 대화
        print(f"재시도 한계 도달 - Assessment 모드 포기, Casual 대화로 전환")
        return "casual"

    # === 메인 실행 함수 ===
    
    def chat_with_history(self, message: str, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """대화 히스토리를 포함한 메시지 처리"""
        print(f"\n{'='*60}")
        print(f"사용자 입력: {message}")
        print(f"대화 히스토리: {len(conversation_history)}개 메시지")
        print(f"{'='*60}")
        
        # 대화 히스토리를 LangChain 메시지 형태로 변환
        messages = []
        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # 초기 상태 설정
        initial_state: ConversationState = {
            "messages": messages,
            "current_message": message,
            "task_scores": {},
            "selected_task": "",
            "task_message_relevance": 0.0,
            "generated_questions": [],
            "question_similarities": [],
            "selected_question": "",
            "question_message_relevance": 0.0,
            "conversation_mode": "assessment",
            "ai_response": "",
            "response_type": "",
            "workflow_stage": "",
            "retry_count": 0,
            "background_question": "",
            "background_score": 0.0,
            "background_ready": False,
            # 채점 관련 필드
            "is_assessment_answer": False,
            "last_assessment_question": "",
            "last_assessment_task": "",
            "assessment_score": 0.0,
            "score_details": {}
        }
        
        # 그래프 실행
        final_state = self.graph.invoke(initial_state)
        
        print(f"\n{'결과':=^60}")
        print(f"AI 응답: {final_state['ai_response']}")
        print(f"응답 타입: {final_state['response_type']}")
        print(f"워크플로우 단계: {final_state['workflow_stage']}")
        print(f"재시도 횟수: {final_state.get('retry_count', 0)}")
        
        # Assessment 답변 채점 결과 출력 (백그라운드)
        if final_state.get('is_assessment_answer', False):
            print(f"Assessment 답변 감지됨!")
            print(f"채점 점수: {final_state.get('assessment_score', 0.0):.2f}/1.0")
            print(f"채점 상세: {final_state.get('score_details', {})}")
        
        # 백그라운드 준비 상태 출력
        if final_state.get('background_ready', False):
            print(f"백그라운드 질문 준비됨 (점수: {final_state.get('background_score', 0.0):.2f})")
        
        return {
            "user_message": message,
            "selected_task": final_state.get("selected_task", ""),
            "task_message_relevance": final_state.get("task_message_relevance", 0.0),
            "generated_questions": final_state.get("generated_questions", []),
            "selected_question": final_state.get("selected_question", ""),
            "question_message_relevance": final_state.get("question_message_relevance", 0.0),
            "response_type": final_state["response_type"],
            "ai_response": final_state["ai_response"],
            "workflow_stage": final_state["workflow_stage"],
            # 채점 결과 (백그라운드에서만 기록)
            "is_assessment_answer": final_state.get("is_assessment_answer", False),
            "last_assessment_question": final_state.get("last_assessment_question", ""),
            "last_assessment_task": final_state.get("last_assessment_task", ""),
            "assessment_score": final_state.get("assessment_score", 0.0),
            "score_details": final_state.get("score_details", {})
        }

# === 테스트 실행 ===

if __name__ == "__main__":
    # LangGraph 챗봇 생성
    chatbot = LangGraphDementiaChatbot(config)
    
    print("=== 테스트 1: Assessment 질문 생성 ===")
    conversation_history = [
        {"role": "user", "content": "안녕하세요. 오늘 날씨가 참 좋네요."},
        {"role": "assistant", "content": "안녕하세요! 정말 좋은 날씨네요. 어떻게 지내셨어요?"},
    ]
    
    new_message = "어제 시장에서 사과, 배, 포도를 샀어요."
    result1 = chatbot.chat_with_history(new_message, conversation_history)
    
    print(f"\n{'테스트 1 결과':=^80}")
    print(f"메시지: '{result1['user_message']}'")
    print(f"선택 태스크: {result1['selected_task']} (점수: {result1['task_message_relevance']:.2f})")
    print(f"AI 응답: {result1['ai_response']}")
    print(f"응답 타입: {result1['response_type']}")
    
    # 테스트 2: Assessment 답변 채점 (백그라운드, 피드백 없음)
    print(f"\n{'=== 테스트 2: Assessment 답변 채점 (피드백 없음) ===':=^80}")
    conversation_history_2 = [
        {"role": "user", "content": "안녕하세요. 오늘 날씨가 참 좋네요."},
        {"role": "assistant", "content": "안녕하세요! 정말 좋은 날씨네요. 어떻게 지내셨어요?"},
        {"role": "user", "content": "어제 시장에서 사과, 배, 포도를 샀어요."},
        {"role": "assistant", "content": "콩, 생선, 고추들을 요즘 좋아하시는 순서대로 말씀해주세요."},
    ]
    
    # 키워드 포함 답변
    answer_message = "콩을 제일 좋아하고, 그 다음에 생선, 마지막에 고추 순서예요."
    result2 = chatbot.chat_with_history(answer_message, conversation_history_2)
    
    print(f"\n{'테스트 2 결과':=^80}")
    print(f"메시지: '{result2['user_message']}'")
    print(f"Assessment 답변 감지: {result2['is_assessment_answer']}")
    print(f"채점 점수 (백그라운드): {result2['assessment_score']:.2f}/1.0")
    print(f"AI 응답: {result2['ai_response']}")
    print(f"응답 타입: {result2['response_type']}")
    print(f"피드백 제공: 없음 (자연스럽게 다음 대화로 이어짐)")
    
    print(f"\n{'전체 테스트 완료':=^80}")