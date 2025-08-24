"""
8. 캐싱폴백 구현
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
    # 캐시 관련 필드
    cached_question_found: bool            # 캐시된 질문을 찾았는지
    cached_question_score: float           # 캐시된 질문의 관련성 점수
    reused_question: str                   # 재사용된 질문

@dataclass
class ChatbotConfig:
    openai_api_key: str                     
    assessment_threshold: float = 0.3       
    fallback_threshold: float = 0.6         
    model_name: str = "gpt-4o-mini"

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
    fallback_threshold=0.6
)

class LangGraphDementiaChatbot:
    def __init__(self, config: ChatbotConfig):
        self.config = config
        self.llm = ChatOpenAI(
            model=config.model_name,
            openai_api_key=config.openai_api_key,
            temperature=0.3
        )
        # 경량 대화용 빠른 LLM 초기화
        self.lightweight_llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            openai_api_key=config.openai_api_key,
            temperature=0.7,
            max_tokens=150  # 빠른 응답을 위해 토큰 제한
        )
        self.vectorizer = TfidfVectorizer(stop_words='english')
        
        # 질문 캐시 초기화
        self.question_cache = {}  # {task_name: [(question, context_score, timestamp), ...]}
        
        # 그래프 빌드
        self.graph = self._build_graph()
        print(f"LangGraph 치매 평가 챗봇 초기화 완료 (모델: {config.model_name})")

    def _build_graph(self) -> StateGraph:
        """단순화된 워크플로우 구성"""
        workflow = StateGraph(ConversationState)
        
        # 노드들 추가
        workflow.add_node("check_if_assessment_answer", self.check_if_assessment_answer)
        workflow.add_node("score_assessment_answer", self.score_assessment_answer)
        workflow.add_node("calculate_task_scores", self.calculate_task_scores)
        workflow.add_node("select_best_task", self.select_best_task)
        workflow.add_node("check_assessment_threshold", self.check_assessment_threshold)
        workflow.add_node("check_cached_questions", self.check_cached_questions)  # 새 노드 추가
        workflow.add_node("generate_questions", self.generate_questions)
        workflow.add_node("calculate_question_similarities", self.calculate_question_similarities)
        workflow.add_node("select_best_question", self.select_best_question)
        workflow.add_node("check_context_relevance", self.check_context_relevance)
        workflow.add_node("output_assessment_question", self.output_assessment_question)
        workflow.add_node("casual_conversation", self.casual_conversation)
        
        # 시작점: 먼저 assessment 답변인지 확인
        workflow.set_entry_point("check_if_assessment_answer")
        
        # Assessment 답변 채점 플로우
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
                "assessment": "check_cached_questions",  # 캐시 확인 단계로 변경
                "casual": "casual_conversation"
            }
        )
        
        # 캐시된 질문 확인 후 분기
        workflow.add_conditional_edges(
            "check_cached_questions",
            self._decide_cache_usage,
            {
                "use_cached": "output_assessment_question",  # 캐시 질문 바로 사용
                "generate_new": "generate_questions"  # 새 질문 생성
            }
        )
        
        workflow.add_edge("generate_questions", "calculate_question_similarities")
        workflow.add_edge("calculate_question_similarities", "select_best_question")
        workflow.add_edge("select_best_question", "check_context_relevance")
        
        # threshold 체크 후 최종 분기 (단순화)
        workflow.add_conditional_edges(
            "check_context_relevance",
            self._decide_final_output,
            {
                "assessment": "output_assessment_question",
                "casual": "casual_conversation"
            }
        )
        
        # 종료 노드들
        workflow.add_edge("output_assessment_question", END)
        workflow.add_edge("casual_conversation", END)
        
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

    def check_cached_questions(self, state: ConversationState) -> ConversationState:
        """캐시된 질문 확인 및 재사용 검토"""
        print("🔍 캐시된 질문 확인 중...")
        
        current_message = state["current_message"]
        selected_task = state["selected_task"]
        
        # 캐시에 해당 태스크의 질문이 있는지 확인
        if selected_task not in self.question_cache or not self.question_cache[selected_task]:
            print(f"❌ {selected_task} 태스크의 캐시된 질문 없음")
            return {
                **state,
                "cached_question_found": False,
                "cached_question_score": 0.0,
                "reused_question": ""
            }
        
        cached_questions = self.question_cache[selected_task]
        print(f"📚 {selected_task} 태스크에서 {len(cached_questions)}개 캐시된 질문 발견")
        
        # 현재 메시지와 캐시된 질문들의 적합성 재평가
        best_cached_question = ""
        best_relevance_score = 0.0
        
        for question, original_score, timestamp in cached_questions:
            # 간단한 키워드 매칭으로 현재 맥락과의 관련성 평가
            relevance_score = self._evaluate_cached_question_relevance(current_message, question)
            
            print(f"  📝 캐시 질문: {question[:50]}... (원래점수: {original_score:.2f}, 현재점수: {relevance_score:.2f})")
            
            if relevance_score > best_relevance_score:
                best_relevance_score = relevance_score
                best_cached_question = question
        
        # 적절한 캐시 질문이 발견되었는지 확인 (임계값: 0.3)
        cache_threshold = 0.3
        if best_relevance_score >= cache_threshold:
            print(f"✅ 재사용할 캐시 질문 발견! (점수: {best_relevance_score:.2f})")
            print(f"📋 선택된 질문: {best_cached_question}")
            return {
                **state,
                "cached_question_found": True,
                "cached_question_score": best_relevance_score,
                "reused_question": best_cached_question,
                "selected_question": best_cached_question,
                "question_message_relevance": best_relevance_score
            }
        else:
            print(f"❌ 적합한 캐시 질문 없음 (최고점수: {best_relevance_score:.2f} < 임계값 {cache_threshold})")
            return {
                **state,
                "cached_question_found": False,
                "cached_question_score": best_relevance_score,
                "reused_question": ""
            }

    def _evaluate_cached_question_relevance(self, current_message: str, cached_question: str) -> float:
        """캐시된 질문과 현재 메시지의 관련성 간단 평가"""
        try:
            # 키워드 기반 유사도 계산
            current_words = set(current_message.lower().split())
            question_words = set(cached_question.lower().split())
            
            # 공통 키워드 비율
            if len(question_words) == 0:
                return 0.0
                
            common_words = current_words.intersection(question_words)
            keyword_similarity = len(common_words) / len(question_words)
            
            # 길이 유사성 (너무 다르면 관련성 낮음)
            length_ratio = min(len(current_message), len(cached_question)) / max(len(current_message), len(cached_question))
            
            # 최종 점수 (키워드 70% + 길이 30%)
            final_score = (keyword_similarity * 0.7) + (length_ratio * 0.3)
            
            return min(1.0, final_score)
            
        except Exception as e:
            print(f"❌ 캐시 질문 관련성 평가 실패: {e}")
            return 0.0

    def generate_questions(self, state: ConversationState) -> ConversationState:
        """4. 예상 질문 생성"""
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
        """일상 대화 처리 - 캐싱 후엔 경량 시스템 사용"""
        messages = state["messages"]
        current_message = state["current_message"]
        
        # 워크플로우 단계 확인으로 캐싱 후 상황인지 판단
        workflow_stage = state.get("workflow_stage", "")
        
        # 캐싱 후 casual 대화면 경량 시스템 사용
        if "cached" in str(state.get("selected_question", "")).lower() or \
           state.get("question_message_relevance", 1.0) < self.config.fallback_threshold:
            print("🚀 캐싱 후 경량 대화 모드")
            ai_response = self.lightweight_chat(current_message, messages)
            response_type = "casual_lightweight"
        else:
            # 일반 casual 대화 (기존 방식)
            print("일반 casual 대화 모드")
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
                # 실패 시 경량 시스템으로 폴백
                ai_response = self.lightweight_chat(current_message, messages)
                response_type = "casual_fallback"
        
        return {
            **state,
            "ai_response": ai_response,
            "response_type": response_type,
            "workflow_stage": "casual_chat"
        }

    # === 캐싱 시스템 ===
    
    def _cache_question(self, task_name: str, question: str, context_score: float):
        """질문을 캐시에 저장"""
        timestamp = datetime.now().timestamp()
        
        if task_name not in self.question_cache:
            self.question_cache[task_name] = []
        
        # 새 질문 추가
        self.question_cache[task_name].append((question, context_score, timestamp))
        
        # 태스크당 최대 10개까지만 유지 (오래된 것부터 삭제)
        if len(self.question_cache[task_name]) > 10:
            self.question_cache[task_name].sort(key=lambda x: x[2])  # timestamp 기준 정렬
            removed_question = self.question_cache[task_name].pop(0)  # 가장 오래된 것 제거
            print(f"캐시 크기 초과: 오래된 질문 삭제 - {removed_question[0][:50]}...")
        
        print(f"질문 캐시됨 ({task_name}): {question[:50]}... (점수: {context_score:.2f})")
        print(f"현재 {task_name} 캐시 크기: {len(self.question_cache[task_name])}")

    def get_cache_status(self):
        """캐시 상태 조회"""
        if not self.question_cache:
            return "캐시가 비어있습니다."
        
        status = "=== 질문 캐시 상태 ===\n"
        for task_name, questions in self.question_cache.items():
            status += f"\n{task_name}: {len(questions)}개 질문\n"
            for i, (question, score, timestamp) in enumerate(questions, 1):
                time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
                status += f"  {i}. {question[:60]}... (점수: {score:.2f}, 시간: {time_str})\n"
        
        return status

    def lightweight_chat(self, current_message: str, messages: List = None) -> str:
        """경량 대화 시스템 - 캐싱 후 즉시 빠른 응답"""
        print("💬 경량 대화 시스템 활성화 (gpt-3.5-turbo)")
        
        # 간단한 대화 프롬프트
        lightweight_prompt = """당신은 7~12세 호기심 많은 어린이입니다. 할머니/할아버지와 자연스럽게 대화하세요.

특징:
- 짧고 친근한 말투
- 호기심과 공감 표현
- 자연스러운 대화 이어가기
- 50자 이내 간결한 응답

대화 예시:
할머니: "오늘 날씨가 좋네"
손자: "정말요! 밖에 나가고 싶어져요~"

할머니: "꽃이 예쁘게 피었구나"
손자: "우와! 어떤 색깔이에요? 향기도 좋을 것 같아요!"
"""
        
        try:
            # 대화 히스토리 구성 (최근 2턴만 사용해서 빠르게)
            conversation_messages = [SystemMessage(content=lightweight_prompt)]
            
            if messages:
                # 최근 2턴만 사용 (성능 최적화)
                recent_messages = messages[-2:] if len(messages) >= 2 else messages
                conversation_messages.extend(recent_messages)
            
            conversation_messages.append(HumanMessage(content=current_message))
            
            # 빠른 응답 생성
            response = self.lightweight_llm.invoke(conversation_messages)
            lightweight_response = response.content.strip()
            
            print(f"💬 경량 응답 생성 완료: {lightweight_response}")
            return lightweight_response
            
        except Exception as e:
            print(f"❌ 경량 대화 생성 실패: {e}")
            # 폴백 응답들
            fallback_responses = [
                "그렇구나! 더 얘기해 주세요~",
                "정말요? 재미있네요!",
                "우와! 그런 일이 있었구나!",
                "그래요? 신기해요!",
                "맞아요! 저도 그런 것 같아요!"
            ]
            import random
            return random.choice(fallback_responses)

    # === 조건부 엣지 결정 함수들 ===
    
    def _decide_if_scoring_needed(self, state: ConversationState) -> str:
        """Assessment 답변 채점이 필요한지 결정"""
        return "score_answer" if state["is_assessment_answer"] else "continue_normal"
    
    def _decide_conversation_mode(self, state: ConversationState) -> str:
        """대화 모드 결정"""
        return state["conversation_mode"]

    def _decide_cache_usage(self, state: ConversationState) -> str:
        """캐시된 질문 사용 여부 결정"""
        cached_question_found = state.get("cached_question_found", False)
        
        if cached_question_found:
            print("🔄 캐시된 질문 재사용")
            return "use_cached"
        else:
            print("🆕 새로운 질문 생성 필요")
            return "generate_new"

    def _decide_final_output(self, state: ConversationState) -> str:
        """최종 출력 형태 결정 + 캐싱 로직"""
        relevance = state["question_message_relevance"]
        threshold = self.config.fallback_threshold
        
        # threshold를 넘으면 assessment 질문 출력
        if relevance >= threshold:
            print(f"평가 질문 출력 (맥락 점수 {relevance:.2f} >= 임계값 {threshold})")
            return "assessment"
        else:
            # threshold 미만이면 질문을 캐시에 저장하고 casual 대화로 종결
            print(f"맥락 점수 부족 - casual 대화로 종결 (점수: {relevance:.2f} < 임계값 {threshold})")
            
            # 생성된 질문을 캐시에 저장
            selected_question = state.get("selected_question", "")
            selected_task = state.get("selected_task", "")
            
            if selected_question and selected_task:
                self._cache_question(selected_task, selected_question, relevance)
            
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
            # 채점 관련 필드
            "is_assessment_answer": False,
            "last_assessment_question": "",
            "last_assessment_task": "",
            "assessment_score": 0.0,
            "score_details": {},
            # 캐시 관련 필드 초기화
            "cached_question_found": False,
            "cached_question_score": 0.0,
            "reused_question": ""
        }
        
        # 그래프 실행
        final_state = self.graph.invoke(initial_state)
        
        print(f"\n{'결과':=^60}")
        print(f"AI 응답: {final_state['ai_response']}")
        print(f"응답 타입: {final_state['response_type']}")
        print(f"워크플로우 단계: {final_state['workflow_stage']}")
        
        # Assessment 답변 채점 결과 출력 (백그라운드)
        if final_state.get('is_assessment_answer', False):
            print(f"Assessment 답변 감지됨!")
            print(f"채점 점수: {final_state.get('assessment_score', 0.0):.2f}/1.0")
            print(f"채점 상세: {final_state.get('score_details', {})}")
        
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
    
    # 테스트 3: Task threshold를 만족하지 않을 때 casual 대화
    print(f"\n{'=== 테스트 3: Task threshold 미만 -> Casual 대화 ===':=^80}")
    conversation_history_3 = [
        {"role": "user", "content": "안녕하세요."},
        {"role": "assistant", "content": "안녕하세요! 어떻게 지내셨어요?"},
    ]
    
    casual_message = "오늘 기분이 좋아요."
    result3 = chatbot.chat_with_history(casual_message, conversation_history_3)
    
    print(f"\n{'테스트 3 결과':=^80}")
    print(f"메시지: '{result3['user_message']}'")
    print(f"선택 태스크: {result3['selected_task']} (점수: {result3['task_message_relevance']:.2f})")
    print(f"AI 응답: {result3['ai_response']}")
    print(f"응답 타입: {result3['response_type']}")
    
    # 테스트 4: Assessment 모드에서 질문 맥락 점수 부족 -> Casual 대화
    print(f"\n{'=== 테스트 4: Assessment 질문 맥락 점수 부족 -> Casual 대화 ===':=^80}")
    conversation_history_4 = [
        {"role": "user", "content": "좋은 하루였어요."},
        {"role": "assistant", "content": "정말 좋네요! 무엇이 좋았나요?"},
    ]
    
    # 시간 관련이지만 맥락상 어색할 수 있는 메시지
    time_message = "지금 몇 시인지 궁금해요."
    result4 = chatbot.chat_with_history(time_message, conversation_history_4)
    
    print(f"\n{'테스트 4 결과':=^80}")
    print(f"메시지: '{result4['user_message']}'")
    print(f"선택 태스크: {result4['selected_task']} (점수: {result4['task_message_relevance']:.2f})")
    print(f"질문-메시지 맥락 점수: {result4['question_message_relevance']:.2f}")
    print(f"AI 응답: {result4['ai_response']}")
    print(f"응답 타입: {result4['response_type']}")
    
    print(f"\n{'전체 테스트 완료':=^80}")