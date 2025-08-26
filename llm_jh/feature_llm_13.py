"""
13.
"""
import os   
import json
import numpy as np
import openai
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
    # 사진 메타데이터 관련 필드
    photo_metadata: Dict[str, Any]         # 사진 메타데이터 (caption, objects, people 등)

@dataclass
class ChatbotConfig:
    openai_api_key: str                     
    assessment_threshold: float = 0.0       
    fallback_threshold: float = 1.0         
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
        매 대화 세션 시작 시 1번만 측정합니다. (대화 시작 후 첫에만 출력)
        example_questions의 응용을 최소화하여 질문을 생성하세요.
        """,
        "example_questions": [
            "20년 전 그날로 기억 여행을 시작하려고 해요. 이 기록을 시작하는 오늘은 2025년 9월 며칠인가요?"
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
    assessment_threshold=0.0,
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
        # 경량 대화용 빠른 LLM 초기화 (LangChain)
        self.lightweight_llm = ChatOpenAI(
            model="gpt-3.5-turbo",  # LangChain 호환성을 위해 임시로 3.5 turbo 사용
            openai_api_key=config.openai_api_key,
            temperature=0.7,
            max_tokens=150  # 빠른 응답을 위해 토큰 제한
        )
        
        # AI 답변 시뮬레이터 (노인 사용자 역할)
        self.response_simulator_llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            openai_api_key=config.openai_api_key,
            temperature=0.7,
            max_tokens=200
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
        
        # time_orientation 몰입감 시나리오 후 특별 처리 (동적 연도 지원)
        if last_ai_message and "기억 여행을 시작하려고 해요" in last_ai_message and "2025년 9월 며칠인가요?" in last_ai_message:
            is_assessment_answer = True
            last_assessment_task = "time_orientation"
            print("몰입감 시나리오 - time_orientation 답변 감지")
        
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
        messages = state["messages"]
        
        # 첫 턴 정확히 감지 (전체 메시지 히스토리가 비어있거나, 사용자 메시지가 없는 경우)
        user_message_count = len([msg for msg in messages if isinstance(msg, HumanMessage)])
        total_message_count = len(messages)
        is_first_session = total_message_count == 0 or user_message_count == 0
        
        if is_first_session or (user_message_count <= 1 and message):
            # 세션 시작이거나 첫 사용자 메시지일 때 time_orientation을 강제로 최고 점수 부여
            print(f"세션 시작 감지 - time_orientation 우선 평가 (전체 메시지: {total_message_count}, 사용자 메시지: {user_message_count})")
            return {
                **state, 
                "task_scores": {
                    "registration_recall": 0.0, 
                    "Naming": 0.0, 
                    "time_orientation": 1.0
                }
            }
        
        # 첫 턴이 아닌 경우 기존 로직 실행
        print(f"일반 태스크 평가 (사용자 메시지 수: {user_message_count})")
        
        prompt = f"""사용자 메시지: "{message}"
        대화 턴 수: {len(messages)}

        다음 평가 영역들과의 관련도를 0-1 사이로 평가해주세요:

        1. registration_recall: 기억 등록은 즉각적인 기억력을 평가하는 항목.
        messages 최근 5개 turn 내에서 동일 선상에서 비교될 수 있는 단어/고유명사가 3개 이상 나오면 본 평가내역을 활용.

        2. Naming: 사물 이름 맞추기 (사진 속 객체 언급). 표시된 사물의 이름을 기억해내는 능력을 평가합니다. 
        사진데이터에서 위치관계가 명확한 사물이 있을 경우 본 평가 항목을 사용하기 적당합니다.

        3. time_orientation: 현재 세션 중간이므로 측정하지 않습니다. (점수: 0.0)

        JSON 형식으로만 응답:
        {{"registration_recall": 0.0, "Naming": 0.0, "time_orientation": 0.0}}"""

        try:
            response = self.llm.invoke([SystemMessage(content=prompt)])
            import json
            task_scores = json.loads(response.content.strip())
            
            # 첫 턴이 아닐 때는 time_orientation 강제로 0.0 설정
            task_scores["time_orientation"] = 0.0
            
        except Exception as e:
            print(f"태스크 점수 계산 실패: {e}")
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
        print("캐시된 질문 확인 중...")
        
        current_message = state["current_message"]
        selected_task = state["selected_task"]
        
        # 캐시에 해당 태스크의 질문이 있는지 확인
        if selected_task not in self.question_cache or not self.question_cache[selected_task]:
            print(f"{selected_task} 태스크의 캐시된 질문 없음")
            return {
                **state,
                "cached_question_found": False,
                "cached_question_score": 0.0,
                "reused_question": ""
            }
        
        cached_questions = self.question_cache[selected_task]
        print(f"{selected_task} 태스크에서 {len(cached_questions)}개 캐시된 질문 발견")
        
        # 현재 메시지와 캐시된 질문들의 적합성 재평가
        best_cached_question = ""
        best_relevance_score = 0.0
        
        for question, original_score, timestamp in cached_questions:
            # 간단한 키워드 매칭으로 현재 맥락과의 관련성 평가
            relevance_score = self._evaluate_cached_question_relevance(current_message, question)
            
            print(f"  캐시 질문: {question[:50]}... (원래점수: {original_score:.2f}, 현재점수: {relevance_score:.2f})")
            
            if relevance_score > best_relevance_score:
                best_relevance_score = relevance_score
                best_cached_question = question
        
        # 적절한 캐시 질문이 발견되었는지 확인 (임계값: 0.3)
        cache_threshold = 0.3
        if best_relevance_score >= cache_threshold:
            print(f"재사용할 캐시 질문 발견! (점수: {best_relevance_score:.2f})")
            print(f"선택된 질문: {best_cached_question}")
            return {
                **state,
                "cached_question_found": True,
                "cached_question_score": best_relevance_score,
                "reused_question": best_cached_question,
                "selected_question": best_cached_question,
                "question_message_relevance": best_relevance_score
            }
        else:
            print(f"적합한 캐시 질문 없음 (최고점수: {best_relevance_score:.2f} < 임계값 {cache_threshold})")
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
            print(f"캐시 질문 관련성 평가 실패: {e}")
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
        """8. 평가 질문 출력 - 몰입감 향상 시나리오 포함"""
        print("8단계: 평가 질문 출력")
        selected_question = state["selected_question"]
        selected_task = state["selected_task"]
        
        # time_orientation 평가일 때 몰입감 향상 시나리오 추가
        if selected_task == "time_orientation":
            # 먼저 사용자가 날짜를 말할 수 있도록 유도하는 대화
            immersive_intro = """20년 전 그날로 기억 여행을 시작하려고 해요. 이 기록을 시작하는 오늘은 2025년 9월 며칠인가요?"""
            
            # 사용자 응답 후 카운트다운과 시간 여행 몰입 효과 추가
            immersive_response = f"""(AI) "{immersive_intro}"
(사용자 응답 대기)

(AI) 오늘은 2025년 9월 {{사용자_응답}}일... 20년이라는 시간을 거슬러 올라가는 중이에요…3…2..1

(AI) 사진 속의 어린아이는 누구인가요? 환하게 웃고 있는 아이요"""
            
            print("시간 지남력 평가 - 몰입감 향상 시나리오 적용")
            return {
                **state, 
                "ai_response": immersive_intro,
                "response_type": "assessment_immersive",
                "workflow_stage": "immersive_time_orientation"
            }
        else:
            # 기존 다른 평가들은 그대로 진행
            return {
                **state, 
                "ai_response": selected_question,
                "response_type": "assessment",
                "workflow_stage": "assessment_question_output"
            }

    def casual_conversation(self, state: ConversationState) -> ConversationState:
        """일상 대화 처리 - 개선된 시간 여행 로직"""
        messages = state["messages"]
        current_message = state["current_message"]
        
        # time_orientation 평가 후 몰입감 시간 여행 효과 확인
        if state.get("is_assessment_answer", False) and state.get("last_assessment_task") == "time_orientation":
            print("time_orientation 평가 후 몰입감 시간 여행 효과 적용")
            
            # 사용자 답변에서 날짜 추출 시도
            user_date = self._extract_date_from_message(current_message)
            
            # 사진 메타데이터에서 연도 정보 추출
            photo_metadata = state.get("photo_metadata", {})
            years_ago = self._calculate_years_ago(photo_metadata)
            
            # 시간 여행 시나리오 생성
            time_travel_intro = self._generate_time_travel_intro(user_date, years_ago)
            
            # 사진 메타데이터 기반 질문 생성
            photo_question = self._generate_photo_based_question(photo_metadata)
            
            immersive_transition = f"""{time_travel_intro}

    {photo_question}"""
            
            return {
                **state,
                "ai_response": immersive_transition,
                "response_type": "immersive_transition",
                "workflow_stage": "time_travel_transition"
            }
    

        
        # 워크플로우 단계 확인으로 캐싱 후 상황인지 판단
        workflow_stage = state.get("workflow_stage", "")
        
        # 캐싱 후 casual 대화면 경량 시스템 사용
        if "cached" in str(state.get("selected_question", "")).lower() or \
           state.get("question_message_relevance", 1.0) < self.config.fallback_threshold:
            print("캐싱 후 경량 대화 모드")
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

구성:
- 답변에 대한 호응/공감 
- 본인의 의견

주의: 대화를 자연스럽고 친근하게 하게 이어가는 것을 최우선으로 생각할 것

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
    
    # == 날짜 계산 시스템
    def _calculate_years_ago(self, photo_metadata: Dict[str, Any]) -> int:
        """사진 메타데이터에서 몇 년 전 사진인지 계산"""
        current_year = datetime.now().year
        
        # 메타데이터에서 연도 정보 찾기
        possible_year_fields = [
            'year', 'photo_year', 'taken_year', 'date_taken',
            'exif_year', 'creation_year', 'timestamp_year'
        ]
        
        photo_year = None
        
        # 메타데이터에서 연도 추출 시도
        for field in possible_year_fields:
            if field in photo_metadata:
                try:
                    value = photo_metadata[field]
                    if isinstance(value, str):
                        # 문자열에서 4자리 연도 추출
                        year_match = re.search(r'(19|20)\d{2}', str(value))
                        if year_match:
                            photo_year = int(year_match.group())
                            break
                    elif isinstance(value, (int, float)):
                        year = int(value)
                        if 1900 <= year <= current_year:
                            photo_year = year
                            break
                except (ValueError, TypeError):
                    continue
        
        # 메타데이터에서 연도를 찾지 못한 경우 기본값
        if photo_year is None:
            # caption이나 description에서 연도 추출 시도
            text_fields = ['caption', 'description', 'alt_text', 'title']
            for field in text_fields:
                if field in photo_metadata:
                    text = str(photo_metadata[field])
                    year_matches = re.findall(r'(19|20)\d{2}', text)
                    if year_matches:
                        try:
                            photo_year = int(year_matches[-1])  # 마지막 연도 사용
                            break
                        except ValueError:
                            continue
        
        # 여전히 연도를 찾지 못한 경우
        if photo_year is None:
            print("사진 연도 정보를 찾을 수 없음 - 기본값 20년 전 사용")
            return 20
        
        years_ago = current_year - photo_year
        
        # 합리적인 범위 체크 (0-100년)
        if years_ago < 0:
            years_ago = 5  # 미래 연도면 최근으로 처리
        elif years_ago > 100:
            years_ago = 50  # 너무 오래전이면 적당히 조정
        
        print(f"사진 연도: {photo_year}, 현재로부터 {years_ago}년 전")
        return years_ago

    def _generate_time_travel_intro(self, date_info: tuple, years_ago: int) -> str:
        """개선된 시간 여행 도입부 생성"""
        date_type, date_value = date_info
        
        if date_type == "unclear":
            # 사용자가 날짜를 모를 때 우회 처리
            return f"괜찮아요! 정확한 날짜가 기억나지 않으셔도 돼요. {years_ago}년이라는 시간을 거슬러 올라가는 중이에요…3…2..1"
        
        elif date_type == "specific":
            # 구체적 날짜를 말했을 때
            return f"오늘은 2025년 9월 {date_value}일... {years_ago}년이라는 시간을 거슬러 올라가는 중이에요…3…2..1"
        
        else:
            # 날짜 언급이 없을 때
            return f"그럼 이제 {years_ago}년이라는 시간을 거슬러 올라가는 중이에요…3…2..1"

    def _calculate_years_ago(self, photo_metadata: Dict[str, Any]) -> int:
        """사진 메타데이터에서 연도를 추출하여 현재(2025)와의 차이 계산"""
        current_year = 2025
        
        # photo_metadata에서 연도 정보 추출
        if 'year' in photo_metadata:
            photo_year = photo_metadata['year']
        elif 'date_taken' in photo_metadata:
            # "1998-09-15" 형식에서 연도 추출
            try:
                photo_year = int(photo_metadata['date_taken'][:4])
            except (ValueError, TypeError):
                photo_year = current_year - 20  # 기본값: 20년 전
        elif 'time_period' in photo_metadata:
            # "1990년대 후반" 같은 형식에서 연도 추출
            time_period = photo_metadata['time_period']
            if '1990년대 후반' in time_period:
                photo_year = 1998
            elif '1990년대 전반' in time_period:
                photo_year = 1993
            elif '2000년대 초반' in time_period:
                photo_year = 2003
            else:
                photo_year = current_year - 20  # 기본값
        else:
            photo_year = current_year - 20  # 기본값: 20년 전
        
        years_ago = current_year - photo_year
        return max(1, years_ago)  # 최소 1년 전
    
    def _extract_date_from_message(self, message: str) -> tuple:
        """사용자 메시지에서 날짜 정보 추출"""
        import re
        
        # 구체적인 날짜 (9월 15일, 15일 등)
        date_patterns = [
            r'9월\s*(\d{1,2})일',
            r'(\d{1,2})일',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, message)
            if match:
                day = int(match.group(1))
                if 1 <= day <= 31:
                    return ("specific", day)
        
        # 모름/기억 안남 표현
        unclear_patterns = [
            r'모르겠어|기억.*안.*나|잘.*모르겠어|확실하지.*않아'
        ]
        
        for pattern in unclear_patterns:
            if re.search(pattern, message):
                return ("unclear", None)
        
        # 날짜 언급 없음
        return ("none", None)
    
    def _generate_photo_based_question(self, photo_metadata: Dict[str, Any]) -> str:
        """사진 메타데이터를 기반으로 LLM을 사용하여 자연스러운 질문 생성"""
        
        prompt = f"""
        다음 사진 정보를 바탕으로 할머니, 할아버지가 추억을 회상할 수 있는 따뜻하고 자연스러운 질문을 1개 생성해주세요.

        사진 정보:
        - 설명: {photo_metadata.get('caption', '사진 정보 없음')}
        - 세부 내용: {', '.join(photo_metadata.get('dense_captions', []))}
        - 분위기: {photo_metadata.get('mood', '알 수 없음')}
        - 시기: {photo_metadata.get('time_period', '알 수 없음')}
        - 주요 물건들: {', '.join(photo_metadata.get('key_objects', []))}
        - 사람들: {photo_metadata.get('people_description', '알 수 없음')}
        - 시간대: {photo_metadata.get('time_of_day', '알 수 없음')}

        요구사항:
        1. 부드럽고 따뜻한 말투로 질문
        2. 구체적인 사진 속 요소를 언급
        3. 감정과 추억을 자연스럽게 이끌어낼 수 있는 질문
        4. 한 문장으로 간단명료하게

        질문:
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            generated_question = response.content.strip()
            
            # 응답에서 "질문:" 등의 접두사 제거
            if ":" in generated_question:
                generated_question = generated_question.split(":", 1)[1].strip()
            
            return generated_question
        except Exception as e:
            print(f"질문 생성 중 오류: {e}")
            # 기본 질문 반환
            return "이 사진을 보니 어떤 기억이 떠오르시나요?"

    # time_orientation 시작 질문도 개선
    def start_conversation(self, photo_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """대화를 AI가 먼저 시작하는 함수 - 개선된 시나리오"""
        print("=== AI 주도 대화 시작 ===")
        
        # 사진 연도에 따른 동적 질문 생성
        years_ago = self._calculate_years_ago(photo_metadata or {})
        
        # 연도에 맞춘 질문 생성
        time_orientation_question = f"{years_ago}년 전 그날로 기억 여행을 시작하려고 해요. 이 기록을 시작하는 오늘은 2025년 9월 며칠인가요?"
        
        print(f"\n{'AI 주도 시작 결과':=^60}")
        print(f"AI 응답: {time_orientation_question}")
        print(f"사진 연도: {years_ago}년 전")
        print(f"응답 타입: assessment_immersive")
        if photo_metadata:
            print(f"사진 메타데이터: {len(photo_metadata)}개 필드")
        
        return {
            "user_message": "",
            "selected_task": "time_orientation",
            "task_message_relevance": 1.0,
            "generated_questions": [time_orientation_question],
            "selected_question": time_orientation_question,
            "question_message_relevance": 1.0,
            "response_type": "assessment_immersive",
            "ai_response": time_orientation_question,
            "workflow_stage": "immersive_time_orientation",
            "is_assessment_answer": False,
            "last_assessment_question": "",
            "last_assessment_task": "",
            "assessment_score": 0.0,
            "score_details": {},
            "photo_metadata": photo_metadata or {}
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

    
    def _get_fallback_photo_question(self, photo_metadata: Dict[str, Any]) -> str:
        """메타데이터 기반 폴백 질문 생성"""
        key_objects = photo_metadata.get("key_objects", [])
        people_count = photo_metadata.get("people_count", 0)
        
        if people_count > 0:
            if people_count == 1:
                return "사진 속 분은 누구세요?"
            else:
                return f"사진 속 {people_count}분은 누구누구세요?"
        elif key_objects:
            # 첫 번째 객체를 이용한 질문
            obj = key_objects[0]
            return f"사진 속 {obj}에 대해 얘기해주세요!"
        else:
            return "이 사진을 보니 어떤 기억이 떠오르세요?"

    def lightweight_chat(self, current_message: str, messages: List = None) -> str:
        """경량 대화 시스템 - 직접 OpenAI 클라이언트로 gpt-5-nano 사용"""
        print("경량 대화 시스템 활성화 (gpt-5-nano via Direct OpenAI)")
        
        # 향상된 프롬프트 - 전체 히스토리 활용
        enhanced_prompt = """너는 7~15세 사이 호기심 많고 예의바른 어린이입니다. 노인 사용자와 사진을 보며 대화하고 있습니다.
자연스럽고 친근한 응답으로 대화를 이어가세요. "다음 메시지를 보내주시면" 같은 불필요한 안내는 하지 마세요."""
        
        # LangSmith 추적을 위해 ChatOpenAI 사용 (gpt-5-nano 시도)
        try:
            # gpt-5-nano로 시도 (간단한 메시지 구조)
            nano_llm = ChatOpenAI(
                model="gpt-5-nano",
                openai_api_key=self.config.openai_api_key,
                temperature=1.0,  # gpt-5-nano는 기본값 1만 지원
                max_tokens=1000
            )
            
            simple_message = f"사용자 메시지에 자연스럽게 응답해주세요: {current_message}"
            nano_response = nano_llm.invoke([HumanMessage(content=simple_message)])
            
            print(f"gpt-5-nano (ChatOpenAI) 호출 성공: {nano_response.content}")
            return nano_response.content
            
        except Exception as nano_error:
            print(f"gpt-5-nano (ChatOpenAI) 실패: {nano_error}")
            print("   gpt-3.5-turbo 폴백으로 전환...")
            
            # 폴백: LangChain으로 gpt-3.5-turbo 사용
            try:
                conversation_messages = [SystemMessage(content=enhanced_prompt)]
                if messages:
                    conversation_messages.extend(messages[::-2])
                conversation_messages.append(HumanMessage(content=current_message))
                
                response = self.lightweight_llm.invoke(conversation_messages)
                fallback_response = response.content.strip()
                
                print(f"LangChain 폴백 성공: {fallback_response}")
                return fallback_response
                
            except Exception as e2:
                print(f"LangChain 폴백도 실패: {e2}")
                # 최종 폴백 응답들
                fallback_responses = [
                    "그렇구나! 더 얘기해 주세요~",
                    "정말요? 재미있네요!",
                    "우와! 그런 일이 있었구나!",
                    "그래요? 신기해요!",
                    "맞아요! 저도 그런 것 같아요!"
                ]
                import random
                return random.choice(fallback_responses)

    # (임시) 노인 mimic 답변 노드
    def simulate_user_response(self, ai_question: str, conversation_context: List = None) -> str:
        """AI 시뮬레이터: 평가 질문에 대한 노인 사용자의 답변 생성"""
        print("AI 답변 시뮬레이터 활성화 (노인 사용자 역할)")
        
        # 노인 사용자 역할 프롬프트
        user_simulation_prompt = """당신은 75세 할머니/할아버지 역할입니다. 손자와 대화하고 있습니다.

특징:
- 자연스럽고 따뜻한 말투
- 때로는 기억이 완벽하지 않을 수 있음
- 단순하고 솔직한 답변
- 50-100자 내외의 적당한 길이

평가 질문에 대해 노인이 실제로 답변할 법한 자연스러운 응답을 해주세요.
완벽한 정답이 아니어도 괜찮습니다. 노인의 실제 반응처럼 답변해주세요.

예시:
질문: "아까 말씀하신 과일 중 사과, 배, 포도를 좋아하시는 순서대로 말씀해주세요."
답변: "음... 사과를 제일 좋아하고, 그 다음에... 배였나? 포도도 달콤해서 좋아해요."

질문: "사진 속 아이가 들고 있는 물건의 이름은 뭐에요?"
답변: "저건 공이네요. 빨간색 공 같은데 예쁘네요."

질문: "오늘은 몇일인가요?"
답변: "오늘이... 25일이었나요? 정확히는 잘 모르겠어요."
"""

        try:
            # 대화 히스토리 구성
            conversation_messages = [SystemMessage(content=user_simulation_prompt)]
            
            if conversation_context:
                # 최근 3턴 정도만 참조
                recent_context = conversation_context[-3:] if len(conversation_context) >= 3 else conversation_context
                conversation_messages.extend(recent_context)
            
            # AI 질문 추가
            conversation_messages.append(HumanMessage(content=f"질문: {ai_question}"))
            
            # (임시) 노인 사용자 답변 생성 
            response = self.response_simulator_llm.invoke(conversation_messages)
            simulated_response = response.content.strip()
            
            print(f"시뮬레이션 답변 생성: {simulated_response}")
            return simulated_response
            
        except Exception as e:
            print(f"답변 시뮬레이션 실패: {e}")
            # 폴백 답변들 (노인 스타일)
            fallback_responses = [
                "그렇네요... 잘 기억이 안 나네요.",
                "음... 뭐라고 해야 할까요?",
                "아, 그거 말이지요... 생각이 안 나네요.",
                "맞아요, 그런 것 같아요.",
                "글쎄요... 정확히는 모르겠어요."
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
            print("캐시된 질문 재사용")
            return "use_cached"
        else:
            print("새로운 질문 생성 필요")
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
    
    def start_conversation(self, photo_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """대화를 AI가 먼저 시작하는 함수 - 개선된 동적 연도 시나리오"""
        print("=== AI 주도 대화 시작 ===")
        
        # 사진 연도에 따른 동적 질문 생성
        years_ago = self._calculate_years_ago(photo_metadata or {})
        
        # 연도에 맞춘 질문 생성
        time_orientation_question = f"{years_ago}년 전 그날로 기억 여행을 시작하려고 해요. 이 기록을 시작하는 오늘은 2025년 9월 며칠인가요?"
        
        print(f"\n{'AI 주도 시작 결과':=^60}")
        print(f"AI 응답: {time_orientation_question}")
        print(f"사진 연도: {years_ago}년 전")
        print(f"응답 타입: assessment_immersive")
        if photo_metadata:
            print(f"사진 메타데이터: {len(photo_metadata)}개 필드")
        
        return {
            "user_message": "",
            "selected_task": "time_orientation",
            "task_message_relevance": 1.0,
            "generated_questions": [time_orientation_question],
            "selected_question": time_orientation_question,
            "question_message_relevance": 1.0,
            "response_type": "assessment_immersive",
            "ai_response": time_orientation_question,
            "workflow_stage": "immersive_time_orientation",
            "is_assessment_answer": False,
            "last_assessment_question": "",
            "last_assessment_task": "",
            "assessment_score": 0.0,
            "score_details": {},
            "photo_metadata": photo_metadata or {}
        }
    
    def chat_with_history(self, message: str, conversation_history: List[Dict[str, str]], photo_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """대화 히스토리를 포함한 메시지 처리"""
        print(f"\n{'='*60}")
        print(f"사용자 입력: {message}")
        print(f"대화 히스토리: {len(conversation_history)}개 메시지")
        if photo_metadata:
            print(f"사진 메타데이터: {len(photo_metadata)}개 필드")
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
            "reused_question": "",
            # 사진 메타데이터
            "photo_metadata": photo_metadata or {}
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
    pass