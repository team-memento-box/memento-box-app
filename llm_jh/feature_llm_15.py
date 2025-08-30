"""
15. 코드 정리: Refactored Dementia Assessment Chatbot - Fully optimized with LLM-driven decisions
"""
import os   
import json
import numpy as np
from dotenv import load_dotenv
from typing import Dict, List, TypedDict, Literal, Any
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from datetime import datetime

# ===== CONSTANTS =====
CURRENT_YEAR = 2025
DEFAULT_YEARS_AGO = 20
CACHE_THRESHOLD = 0.3
MAX_CACHE_SIZE = 10
RECALL_DELAY_TURNS = 5

# System prompts
CASUAL_CHAT_SYSTEM_PROMPT = """당신은 7~15세 사이 호기심 많고 예의바른 어린이입니다. 노인 사용자와 사진을 보며 대화하고 있습니다.

대화 예시:
사용자: "이 사진 속 강아지가 참 귀엽네"
손자: "정말요! 털이 복슬복슬해서 만지고 싶어요. 어릴 때 키우신 강아지에요?"

최대한 사용자가 대화를 주도할 수 있도록 사용자에게 공감하며, 자연스럽고 호기심 어린 반응으로 대화를 이어가세요.

구성: 답변에 대한 호응/공감 + 본인의 의견
주의: 대화를 자연스럽고 친근하게 이어가는 것을 최우선으로 생각할 것"""

LIGHTWEIGHT_CHAT_PROMPT = """너는 7~15세 사이 호기심 많고 예의바른 어린이야. 노인 사용자와 사진을 보며 대화하고 있어.
자연스럽고 친근한 응답으로 대화를 이어가세요."""

# Assessment task templates
TIME_ORIENTATION_TEMPLATE = "{years_ago}년 전 그날로 기억 여행을 시작하려고 해요. 이 기록을 시작하는 오늘은 {current_year}년 9월 며칠인가요?"
TIME_TRAVEL_INTRO_TEMPLATE = "{years_ago}년이라는 시간을 거슬러 올라가는 중이에요…{countdown}"
RECALL_QUESTION_TEMPLATE = "{items}들을 {descriptor} 순서대로 말씀해주세요."

# ===== STATE AND CONFIG =====
class ConversationState(TypedDict):
    messages: List[Dict[str, str]]          
    current_message: str                    
    task_scores: Dict[str, float]          
    selected_task: str                      
    task_message_relevance: float           
    generated_questions: List[str]          
    selected_question: str                 
    question_message_relevance: float      
    conversation_mode: Literal["assessment", "casual"] 
    ai_response: str                       
    response_type: str                     
    workflow_stage: str                                 
    # Assessment scoring
    is_assessment_answer: bool             
    last_assessment_question: str          
    last_assessment_task: str              
    assessment_score: float                
    score_details: Dict[str, Any]          
    # Caching
    cached_question_found: bool            
    cached_question_score: float           
    reused_question: str                   
    # Photo metadata
    photo_metadata: Dict[str, Any]         
    # Registration-Recall separation
    turn_counter: int                      
    pending_recall_items: List[str]        
    recall_scheduled_turn: int             
    recall_question_type: str              
    registration_phase: str                

@dataclass
class ChatbotConfig:
    openai_api_key: str                     
    assessment_threshold: float = 0.4     
    fallback_threshold: float = 0.6        
    model_name: str = "gpt-4o-mini"

ASSESSMENT_TASKS = {
    "registration": {
        "description": 
        """기억 등록(Registration): 즉각적인 기억력을 평가합니다.
          messages 최근 5개 turn 내에서 동일 선상에서 비교될 수 있는 단어/고유명사가 3개 이상 나오면 registration 평가를 활용합니다.
          답변을 저장하고 5턴 후 recall 평가를 예약합니다.""",
        "example_questions": [
            "아까 말씀하신 것들을 좋아했던 순서대로 말씀해주세요.",
            "아까 말씀하신 것들을 살가운 순서대로 말씀해주시겠어요?",
            "아까 말씀하신 것들을 가까운 순서대로 말씀해주시겠어요?",
            "아까 말씀하신 것들을 어릴 적 갖고 싶었던 순서대로 말씀해주세요."
        ],
        "scoring_criteria": {
            "scoring_type": "registration",
            "recall_delay_turns": RECALL_DELAY_TURNS
        }
    },
    "recall": {
        "description": 
        """기억 회상(Recall): registration에서 등록된 항목들을 일정 시간 후 다른 조건으로 다시 물어보는 평가입니다.
          registration에서 5턴 전에 저장된 항목들을 사용하여 다른 조건의 질문을 합니다.""",
        "question_template": RECALL_QUESTION_TEMPLATE,
        "scoring_criteria": {
            "scoring_type": "recall"
        }
    },
    "Naming": {
        "description": 
        """표시된 사물의 이름을 기억해내는 능력 평가. 
        사진 메타데이터에서 위치관계가 명확한 사물이나 사물을 포함하는 사람이 언급된 경우 본 평가 항목을 사용.
        주의: 물체가 있는 위치를 기반으로 그 사물의 사전적 이름이 무엇인지 질문해야 합니다.""",
        
        "example_questions": [
            "사진 속 어린아이가 들고있는 물체를 뭐라고 불러요?",
            "손가락에 끼고 있는 것의 이름은 뭔가요?",
            "친구가 가지고 놀고 있는 물건의 이름은 뭐에요?",
            "사진 속 할머니 옆에 있는 꽃의 이름은 뭔가요?",
            "아이가 안고 있는 동물의 이름은 뭐에요?"
        ],
        "scoring_criteria": {
            "scoring_type": "Naming"
        }
    },
    "time_orientation": {
        "description": 
        """현재 자신이 놓여있는 시간, 날짜, 계절 등의 상황을 올바르게 인식하는 능력을 평가합니다.
        매 대화 세션 시작 시 1번만 측정합니다.""",
        "question_template": TIME_ORIENTATION_TEMPLATE,
        "scoring_criteria": {
            "scoring_type": "time_orientation"
        }
    }
}

# ===== MAIN CLASS =====
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
        
        # Lightweight chat for fallback (gpt-5-nano only)
        self.lightweight_llm = ChatOpenAI(
            model="gpt-5-nano",
            openai_api_key=config.openai_api_key,
            temperature=1.0,
            max_tokens=150
        )
        
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.question_cache = {}  # {task_name: [(question, context_score, timestamp), ...]}
        self.graph = self._build_graph()
        print(f"LangGraph 치매 평가 챗봇 초기화 완료 (모델: {config.model_name})")

    def _build_graph(self) -> StateGraph:
        """Optimized workflow with 5 nodes"""
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("check_and_score_assessment", self.check_and_score_assessment)
        workflow.add_node("evaluate_tasks_and_select", self.evaluate_tasks_and_select)
        workflow.add_node("check_cached_questions", self.check_cached_questions)
        workflow.add_node("generate_and_select_question", self.generate_and_select_question)
        workflow.add_node("finalize_response", self.finalize_response)
        
        # Set entry point
        workflow.set_entry_point("check_and_score_assessment")
        
        # Define edges
        workflow.add_edge("check_and_score_assessment", "evaluate_tasks_and_select")
        
        workflow.add_conditional_edges(
            "evaluate_tasks_and_select",
            self._decide_conversation_mode,
            {
                "assessment": "check_cached_questions",
                "casual": "finalize_response"
            }
        )
        
        workflow.add_conditional_edges(
            "check_cached_questions",
            self._decide_cache_usage,
            {
                "use_cached": "finalize_response",
                "generate_new": "generate_and_select_question"
            }
        )
        
        workflow.add_edge("generate_and_select_question", "finalize_response")
        workflow.add_edge("finalize_response", END)
        
        return workflow.compile()

    def check_and_score_assessment(self, state: ConversationState) -> ConversationState:
        """Combined assessment checking and scoring"""
        print("1단계: Assessment 답변 확인 및 채점...")
        
        # Check if this is an assessment answer
        is_assessment_answer = state.get("last_question_type") == "assessment"
        last_assessment_task = state.get("last_assessment_task", "")
        
        # Find last AI message
        last_ai_message = ""
        messages = state["messages"]
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], AIMessage):
                last_ai_message = messages[i].content
                break
        
        # Special handling for time_orientation immersive scenario
        if last_ai_message and "기억 여행을 시작하려고 해요" in last_ai_message and f"{CURRENT_YEAR}년 9월 며칠인가요?" in last_ai_message:
            is_assessment_answer = True
            last_assessment_task = "time_orientation"
            print("몰입감 시나리오 - time_orientation 답변 감지")
        
        # Score if it's an assessment answer
        assessment_score = 0.0
        score_details = {}
        
        if is_assessment_answer and last_assessment_task:
            print(f"Assessment 답변 채점: {last_assessment_task}")
            assessment_score, score_details = self._score_assessment_answer(
                state["current_message"], last_assessment_task, last_ai_message, state
            )
            
            # Handle registration items if needed
            if last_assessment_task == "registration":
                self._process_registration_answer(state)
        
        return {
            **state,
            "is_assessment_answer": is_assessment_answer,
            "last_assessment_question": last_ai_message,
            "last_assessment_task": last_assessment_task,
            "assessment_score": assessment_score,
            "score_details": score_details
        }

    def _score_assessment_answer(self, current_message: str, task_name: str, 
                                last_question: str, state: ConversationState) -> tuple:
        """Score assessment answer based on task type"""
        task_info = ASSESSMENT_TASKS.get(task_name, {})
        scoring_criteria = task_info.get("scoring_criteria", {})
        scoring_type = scoring_criteria.get("scoring_type", "general")
        
        score = 0.0
        score_details = {}
        
        try:
            if scoring_type == "Naming":
                score, score_details = self._score_naming_answer(
                    current_message, last_question, state.get("photo_metadata", {})
                )
            elif scoring_type == "time_orientation":
                score, score_details = self._score_time_orientation_answer(current_message)
            else:
                # General scoring for registration/recall - LLM-based evaluation
                score, score_details = self._score_general_answer(
                    current_message, last_question, task_name
                )
                
        except Exception as e:
            print(f"채점 실패: {e}")
            score_details = {"error": str(e)}
        
        print(f"채점 완료: {score:.2f}/1.0 ({scoring_type})")
        return score, score_details

    def _score_general_answer(self, user_answer: str, question: str, task_name: str) -> tuple:
        """General LLM-based scoring for registration/recall"""
        system_msg = f"""사용자의 {task_name} 평가 답변을 채점해주세요.

        질문: "{question}"
        사용자 답변: "{user_answer}"
        
        평가 기준:
        - 질문에 적절히 응답했는지 (내용의 완성도)
        - 순서나 구조가 있는 답변인지
        - 논리적 일관성
        
        0.0부터 1.0 사이의 점수만 반환해주세요."""
        
        try:
            response = self.llm.invoke([SystemMessage(content=system_msg)])
            numbers = re.findall(r'0\.\d+|1\.0|0\.0', response.content)
            score = float(numbers[0]) if numbers else 0.5
            
            score_details = {
                "user_answer": user_answer,
                "question": question,
                "evaluation_response": response.content
            }
            
            return score, score_details
        except Exception as e:
            return 0.5, {"error": str(e)}

    def _score_naming_answer(self, user_answer: str, question: str, photo_metadata: Dict) -> tuple:
        """Score naming task answer using dynamic photo metadata evaluation"""
        # Extract target object dynamically from photo metadata
        actual_target_object = self._extract_target_object_from_question(question, photo_metadata)
        
        if not actual_target_object:
            # If no clear target, use general evaluation
            return self._score_general_answer(user_answer, question, "Naming")
        
        system_msg = f"""사용자가 다음 질문에 대해 올바르게 답변했는지 평가해주세요.

        질문: "{question}"
        예상 정답: "{actual_target_object}"
        사용자 답변: "{user_answer}"

        평가 기준:
        - 정확한 답변이거나 유사한 의미: 1.0
        - 완전히 틀린 답변: 0.0

        0.0과 1.0만 반환해주세요."""
        
        try:
            response = self.llm.invoke([SystemMessage(content=system_msg)])
            numbers = re.findall(r'0\.\d+|1\.0|0\.0', response.content)
            score = float(numbers[0]) if numbers else 0.0
            
            score_details = {
                "target_object": actual_target_object,
                "user_answer": user_answer,
                "evaluation_response": response.content
            }
            
            return score, score_details
        except Exception as e:
            return 0.0, {"error": str(e)}

    def _score_time_orientation_answer(self, user_answer: str) -> tuple:
        """Score time orientation answer"""
        today = datetime.now()
        numbers = re.findall(r'\d+', user_answer)
        
        score = 0.0
        score_details = {}
        
        if numbers:
            try:
                user_day = int(numbers[0])
                actual_day = today.day
                score = 1.0 if user_day == actual_day else 0.0
                score_details = {
                    "user_answer": user_day,
                    "correct_answer": actual_day,
                    "difference": abs(user_day - actual_day)
                }
            except ValueError:
                score_details = {"error": "숫자 추출 실패"}
        else:
            score_details = {"error": "답변에서 날짜를 찾을 수 없음"}
        
        return score, score_details

    def _process_registration_answer(self, state: ConversationState):
        """Process registration answer: extract items and schedule recall"""
        current_message = state["current_message"]
        current_turn = state.get("turn_counter", 0)
        
        items = self._extract_items_from_registration_answer(current_message)
        
        if len(items) >= 3:
            recall_turn = current_turn + RECALL_DELAY_TURNS
            recall_descriptor = self._select_appropriate_descriptor(items, current_message)
            
            state["pending_recall_items"] = items
            state["recall_scheduled_turn"] = recall_turn
            state["recall_question_type"] = recall_descriptor
            
            print(f"Registration 아이템 저장: {items}")
            print(f"Recall 예약: {recall_turn}턴에 '{recall_descriptor} 순서' 질문 예정")

    def _select_appropriate_descriptor(self, items: List[str], context: str = "") -> str:
        """LLM-based selection of appropriate descriptor for recall question"""
        try:
            items_context = ', '.join(items)
            
            prompt = f"""다음 registration에서 등록된 아이템들에 대해 recall 질문에 사용할 가장 적절한 형용사를 선택해주세요.

            등록된 아이템들: {items_context}
            대화 맥락: {context}
            
            아이템의 종류에 따라 적절한 형용사 예시:
            - 음식류: 좋아하는, 싫어하는, 자주 먹는, 달콤한, 맛있는
            - 사람들: 친한, 가까이 사는, 자주 만나는, 살가운
            - 물건들: 자주 사용하는, 좋아하는, 비싼, 유용한
            - 장소들: 자주 가는, 좋아하는, 가까운, 편한
            
            위 아이템들의 특성을 참고해서 현재 대화와 어울리는 형용사를 반환해주세요.
            형용사만 반환하고 다른 설명은 하지 마세요."""
            
            response = self.llm.invoke([SystemMessage(content=prompt)])
            descriptor = response.content.strip().replace('"', '').replace("'", "")
            
            # Validate descriptor
            if len(descriptor) > 20 or len(descriptor) < 2:
                return "좋아하는"  # Safe fallback
            
            print(f"LLM 선택 형용사: '{descriptor}' (아이템: {items_context})")
            return descriptor
            
        except Exception as e:
            print(f"형용사 선택 실패: {e}, 기본값 사용")
            return "좋아하는"

    def _extract_items_from_registration_answer(self, answer: str) -> List[str]:
        """Extract items from registration answer using LLM only"""
        try:
            system_msg = f"""사용자의 registration 답변에서 3개 아이템을 순서대로 추출해주세요.
            
            사용자 답변: "{answer}"
            
            JSON 배열 형태로만 반환해주세요: ["아이템1", "아이템2", "아이템3"]
            """
            
            response = self.llm.invoke([SystemMessage(content=system_msg)])
            items_text = response.content.strip()
            
            if items_text.startswith('[') and items_text.endswith(']'):
                items = json.loads(items_text)
                return [str(item).strip() for item in items if item]
            else:
                items = [item.strip('"').strip() for item in items_text.split(',')]
                return items[:3]
                
        except Exception as e:
            print(f"아이템 추출 실패: {e}")
            return []  # Return empty to trigger casual conversation

    def evaluate_tasks_and_select(self, state: ConversationState) -> ConversationState:
        """Evaluate tasks and select best one with turn management"""
        print("2단계: 태스크 평가 및 선택...")
        
        # Update turn counter
        current_turn = state.get("turn_counter", 0) + 1
        state["turn_counter"] = current_turn
        
        message = state["current_message"]
        messages = state["messages"]
        photo_metadata = state.get("photo_metadata", {})
        
        # Check for recall scheduling
        recall_scheduled_turn = state.get("recall_scheduled_turn", -1)
        pending_recall_items = state.get("pending_recall_items", [])
        
        if recall_scheduled_turn > 0 and current_turn >= recall_scheduled_turn and pending_recall_items:
            print(f"Recall 시간 도래! {len(pending_recall_items)}개 아이템으로 recall 평가 시작")
            task_scores = {"registration": 0.0, "recall": 1.0, "Naming": 0.0, "time_orientation": 0.0}
            selected_task = "recall"
            task_relevance = 1.0
            state["registration_phase"] = "recall"
        else:
            # Check if first session
            user_message_count = len([msg for msg in messages if isinstance(msg, HumanMessage)])
            is_first_session = user_message_count <= 1
            
            if is_first_session:
                print(f"세션 시작 감지 - time_orientation 우선 평가")
                task_scores = {"registration": 0.0, "recall": 0.0, "Naming": 0.0, "time_orientation": 1.0}
                selected_task = "time_orientation"
                task_relevance = 1.0
                state["registration_phase"] = "none"
            else:
                # Regular task evaluation using LLM
                task_scores = self._evaluate_task_relevance(message, messages, photo_metadata)
                task_scores["time_orientation"] = 0.0  # Not first session
                if not (recall_scheduled_turn > 0 and current_turn >= recall_scheduled_turn and pending_recall_items):
                    task_scores["recall"] = 0.0
                
                # Select best task or fall back to casual
                if max(task_scores.values()) > 0:
                    best_task_item = max(task_scores.items(), key=lambda x: x[1])
                    selected_task = best_task_item[0]
                    task_relevance = best_task_item[1]
                else:
                    selected_task = ""
                    task_relevance = 0.0
        
        # Determine conversation mode
        conversation_mode = "assessment" if task_relevance >= self.config.assessment_threshold else "casual"
        
        print(f"선택된 태스크: {selected_task} (점수: {task_relevance:.2f})")
        print(f"대화 모드: {conversation_mode}")
        
        return {
            **state,
            "task_scores": task_scores,
            "selected_task": selected_task,
            "task_message_relevance": task_relevance,
            "conversation_mode": conversation_mode
        }

    def _evaluate_task_relevance(self, message: str, messages: List, photo_metadata: Dict) -> Dict[str, float]:
        """LLM-based task relevance evaluation"""
        naming_objects = self._extract_naming_objects_from_photo(photo_metadata)
        
        prompt = f"""사용자 메시지: "{message}"
        대화 턴 수: {len(messages)}
        사진 메타데이터에서 위치관계가 명확한 사물들: {naming_objects}

        다음 평가 영역들과의 관련도를 0-1 사이로 평가해주세요:

        1. registration: 기억 등록 평가 - 최근 대화에서 동일 선상에서 비교될 수 있는 단어/고유명사가 3개 이상 나왔을 때 사용

        2. Naming: 사물 이름 맞추기 - 사진 메타데이터에서 위치관계가 명확한 사물이 언급된 경우 사용
        현재 사진에서 naming 평가 가능한 객체들: {naming_objects}

        JSON 형식으로만 응답:
        {{"registration": 0.0, "recall": 0.0, "Naming": 0.0, "time_orientation": 0.0}}"""

        try:
            response = self.llm.invoke([SystemMessage(content=prompt)])
            task_scores = json.loads(response.content.strip())
            return task_scores
        except Exception as e:
            print(f"태스크 점수 계산 실패: {e} - casual 대화로 전환")
            return {"registration": 0.0, "recall": 0.0, "Naming": 0.0, "time_orientation": 0.0}

    def _extract_naming_objects_from_photo(self, photo_metadata: Dict[str, Any]) -> List[str]:
        """Extract objects with clear positional relationships from photo metadata"""
        naming_objects = []
        
        try:
            # Extract from objects array
            objects = photo_metadata.get("objects", [])
            for obj in objects:
                if isinstance(obj, dict):
                    obj_name = obj.get("name", "")
                    obj_relation = obj.get("relation", {})
                    
                    if obj_name and obj_relation:
                        has_clear_relation = any(key in ["on_top", "nearby", "worn_by", "in_front_of", "behind", "next_to"] 
                                               for key in obj_relation.keys())
                        if has_clear_relation:
                            naming_objects.append(obj_name)
            
            # Extract from people's items
            people = photo_metadata.get("people", [])
            for person in people:
                if isinstance(person, dict):
                    items = person.get("items", [])
                    for item in items:
                        if item and item not in naming_objects:
                            naming_objects.append(item)
            
        except Exception as e:
            print(f"사진 메타데이터에서 naming 객체 추출 실패: {e}")
        
        return naming_objects

    def check_cached_questions(self, state: ConversationState) -> ConversationState:
        """Check and evaluate cached questions for reuse"""
        print("3단계: 캐시된 질문 확인...")
        
        current_message = state["current_message"]
        selected_task = state["selected_task"]
        
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
        
        best_cached_question = ""
        best_relevance_score = 0.0
        
        for question, original_score, timestamp in cached_questions:
            relevance_score = self._evaluate_cached_question_relevance(current_message, question)
            
            if relevance_score > best_relevance_score:
                best_relevance_score = relevance_score
                best_cached_question = question
        
        if best_relevance_score >= CACHE_THRESHOLD:
            print(f"재사용할 캐시 질문 발견! (점수: {best_relevance_score:.2f})")
            return {
                **state,
                "cached_question_found": True,
                "cached_question_score": best_relevance_score,
                "reused_question": best_cached_question,
                "selected_question": best_cached_question,
                "question_message_relevance": best_relevance_score
            }
        else:
            print(f"적합한 캐시 질문 없음 (최고점수: {best_relevance_score:.2f} < 임계값 {CACHE_THRESHOLD})")
            return {
                **state,
                "cached_question_found": False,
                "cached_question_score": best_relevance_score,
                "reused_question": ""
            }

    def _evaluate_cached_question_relevance(self, current_message: str, cached_question: str) -> float:
        """Simple keyword-based relevance evaluation for cached questions"""
        try:
            current_words = set(current_message.lower().split())
            question_words = set(cached_question.lower().split())
            
            if len(question_words) == 0:
                return 0.0
                
            common_words = current_words.intersection(question_words)
            keyword_similarity = len(common_words) / len(question_words)
            
            length_ratio = min(len(current_message), len(cached_question)) / max(len(current_message), len(cached_question))
            
            final_score = (keyword_similarity * 0.7) + (length_ratio * 0.3)
            return min(1.0, final_score)
            
        except Exception as e:
            print(f"캐시 질문 관련성 평가 실패: {e}")
            return 0.0

    def generate_and_select_question(self, state: ConversationState) -> ConversationState:
        """Generate questions and select the best one with similarity evaluation"""
        print("4단계: 질문 생성 및 선택...")
        
        messages = state["messages"]
        current_message = state["current_message"]
        task_name = state["selected_task"]
        photo_metadata = state.get("photo_metadata", {})
        
        # Generate questions based on task type - all go to casual if failed
        generated_questions = []
        
        if task_name == "recall":
            generated_questions = self._generate_recall_questions(state)
        elif task_name == "Naming":
            generated_questions = self._generate_naming_questions_from_photo(photo_metadata)
        elif task_name == "time_orientation":
            generated_questions = self._generate_time_orientation_question(photo_metadata)
        elif task_name == "registration":
            generated_questions = self._generate_registration_questions(messages, current_message)
        
        # If no questions generated, trigger casual conversation
        if not generated_questions:
            print("질문 생성 실패 - casual 대화로 전환")
            return {
                **state,
                "generated_questions": [],
                "selected_question": "",
                "question_message_relevance": 0.0,  # Low score to trigger casual
                "conversation_mode": "casual"  # Force casual mode
            }
        
        # Calculate similarities and select best question
        selected_question, relevance_score = self._select_best_question_with_similarity(
            generated_questions, task_name, current_message, messages
        )
        
        print(f"생성된 질문 {len(generated_questions)}개 중 선택: {selected_question[:50]}...")
        print(f"맥락 관련성 점수: {relevance_score:.2f}")
        
        return {
            **state,
            "generated_questions": generated_questions,
            "selected_question": selected_question,
            "question_message_relevance": relevance_score
        }

    def _generate_recall_questions(self, state: ConversationState) -> List[str]:
        """Generate recall questions using pending items with LLM-determined descriptors"""
        pending_items = state.get("pending_recall_items", [])
        
        if not pending_items:
            print("Recall 아이템이 없어서 casual 대화로 전환")
            return []  # Return empty to trigger casual conversation
        
        items_str = ', '.join(pending_items)
        recall_descriptor = state.get("recall_question_type", "좋아하는")
        
        # Generate single recall question using template
        question = RECALL_QUESTION_TEMPLATE.format(items=items_str, descriptor=recall_descriptor)
        
        print(f"Recall 질문 생성: {question}")
        return [question]

    def _generate_naming_questions_from_photo(self, photo_metadata: Dict[str, Any]) -> List[str]:
        """Generate naming questions based on photo metadata - return empty list if no suitable objects"""
        naming_objects = self._extract_naming_objects_from_photo(photo_metadata)
        
        if not naming_objects:
            print("사진에서 naming 가능한 객체를 찾을 수 없음 - casual 대화로 전환")
            return []  # Return empty to trigger casual conversation
        
        try:
            # Use LLM with JSON dump approach
            prompt = f"""사진 메타데이터를 바탕으로 자연스러운 사물 이름 맞추기 질문을 3개 생성해주세요.
            
            사진 정보: {json.dumps(photo_metadata, ensure_ascii=False)}
            
            요구사항:
            1. 위치관계를 활용한 구체적인 질문
            2. 자연스러운 대화체로 질문
            3. 객체의 구체적인 이름을 미리 말하지 말고, 위치나 상황만으로 물어보세요
            
            각 질문을 새 줄로 구분하여 번호 없이 나열해주세요:"""
            
            response = self.llm.invoke([SystemMessage(content=prompt)])
            generated_questions = [q.strip() for q in response.content.split('\n') if q.strip()]
            
            if len(generated_questions) >= 2:
                return generated_questions[:3]
            else:
                print(f"생성된 질문이 부족함 ({len(generated_questions)}개) - casual 대화로 전환")
                return []
                
        except Exception as e:
            print(f"Naming 질문 생성 실패: {e} - casual 대화로 전환")
            return []

    def _generate_time_orientation_question(self, photo_metadata: Dict[str, Any]) -> List[str]:
        """Generate time_orientation question with dynamic years"""
        years_ago = self._calculate_years_ago(photo_metadata)
        question = TIME_ORIENTATION_TEMPLATE.format(
            years_ago=years_ago, 
            current_year=CURRENT_YEAR
        )
        return [question]

    def _generate_registration_questions(self, messages: List, current_message: str) -> List[str]:
        """Generate registration questions based on conversation context"""
        try:
            system_msg = f"""당신은 치매 평가 전문가입니다. 
대화 히스토리를 바탕으로 registration 평가를 위한 자연스러운 질문을 생성해주세요.

평가 영역: registration
설명: {ASSESSMENT_TASKS['registration']['description']}

예시 질문 구조를 참고하여 대화 맥락에 자연스럽게 이어지는 질문 3개를 생성해주세요.
각 질문을 새 줄로 구분하여 번호 없이 나열해주세요:"""

            conversation_messages = [SystemMessage(content=system_msg)]
            conversation_messages.extend(messages)
            conversation_messages.append(HumanMessage(content=current_message))
            
            response = self.llm.invoke(conversation_messages)
            generated_questions = [q.strip() for q in response.content.split('\n') if q.strip()]
            
            if len(generated_questions) >= 2:
                return generated_questions[:3]
            else:
                print(f"Registration 질문 생성 부족 ({len(generated_questions)}개) - casual 대화로 전환")
                return []
                
        except Exception as e:
            print(f"Registration 질문 생성 실패: {e} - casual 대화로 전환")
            return []

    def _select_best_question_with_similarity(self, questions: List[str], task_name: str, 
                                            current_message: str, messages: List) -> tuple:
        """Select best question using TF-IDF similarity and context relevance"""
        if not questions:
            return "", 0.0
        
        # For single question tasks, evaluate context directly
        if len(questions) == 1:
            selected_question = questions[0]
            context_relevance = self._evaluate_question_context_relevance(
                selected_question, current_message, messages
            )
            return selected_question, context_relevance
        
        # For multiple questions, use TF-IDF similarity
        try:
            example_questions = ASSESSMENT_TASKS[task_name].get("example_questions", [])
            if not example_questions:
                # If no examples, just pick first and evaluate context
                selected_question = questions[0]
                context_relevance = self._evaluate_question_context_relevance(
                    selected_question, current_message, messages
                )
                return selected_question, context_relevance
            
            all_questions = questions + example_questions
            tfidf_matrix = self.vectorizer.fit_transform(all_questions)
            generated_vectors = tfidf_matrix[:len(questions)]
            example_vectors = tfidf_matrix[len(questions):]
            
            similarity_matrix = cosine_similarity(generated_vectors, example_vectors)
            max_similarities = np.max(similarity_matrix, axis=1).tolist()
            
            # Select question with highest similarity to examples
            best_idx = np.argmax(max_similarities)
            selected_question = questions[best_idx]
            
            # Evaluate context relevance
            context_relevance = self._evaluate_question_context_relevance(
                selected_question, current_message, messages
            )
            
            return selected_question, context_relevance
            
        except Exception as e:
            print(f"질문 선택 실패: {e}")
            selected_question = questions[0]
            context_relevance = self._evaluate_question_context_relevance(
                selected_question, current_message, messages
            )
            return selected_question, context_relevance

    def _evaluate_question_context_relevance(self, question: str, current_message: str, messages: List) -> float:
        """Evaluate how well the question fits the conversation context"""
        system_msg = f"""대화 흐름을 분석하여 제안된 질문의 자연스러움을 평가해주세요.

제안된 질문: "{question}"

평가 기준:
- 기존 대화의 자연스러운 흐름
- 맥락의 연결성  
- 노인 사용자가 답변할 수 있는 적절한 질문인지

이 질문이 대화 맥락에 얼마나 자연스러운지 0-1 사이의 점수로 평가해주세요.
숫자만 반환해주세요."""

        conversation_messages = [SystemMessage(content=system_msg)]
        conversation_messages.extend(messages)
        conversation_messages.append(HumanMessage(content=current_message))
        
        try:
            response = self.llm.invoke(conversation_messages)
            content = response.content.strip()
            numbers = re.findall(r'0\.\d+|1\.0|0\.0|\d\.\d+', content)
            
            if numbers:
                relevance = float(numbers[0])
                return max(0.0, min(1.0, relevance))
            else:
                return 0.5
        except Exception as e:
            print(f"맥락 평가 실패: {e}")
            return 0.5

    def finalize_response(self, state: ConversationState) -> ConversationState:
        """Finalize response based on conversation mode and context"""
        print("5단계: 최종 응답 결정...")
        
        conversation_mode = state["conversation_mode"]
        
        if conversation_mode == "assessment":
            return self._generate_assessment_response(state)
        else:
            return self._generate_casual_response(state)

    def _generate_assessment_response(self, state: ConversationState) -> ConversationState:
        """Generate assessment response with immersive scenarios"""
        selected_task = state["selected_task"]
        selected_question = state["selected_question"]
        question_relevance = state["question_message_relevance"]
        
        # Check if question meets threshold
        if question_relevance < self.config.fallback_threshold:
            # Cache the question and fall back to casual conversation
            if selected_question and selected_task:
                self._cache_question(selected_task, selected_question, question_relevance)
                print(f"질문 캐시 저장 후 casual 대화로 전환 (점수: {question_relevance:.2f})")
            return self._generate_casual_response(state)
        
        # Special handling for time_orientation with immersive scenario
        if selected_task == "time_orientation":
            return {
                **state,
                "ai_response": selected_question,
                "response_type": "assessment_immersive",
                "workflow_stage": "immersive_time_orientation"
            }
        
        # Regular assessment response
        return {
            **state,
            "ai_response": selected_question,
            "response_type": "assessment",
            "workflow_stage": "assessment_question_output"
        }

    def _generate_casual_response(self, state: ConversationState) -> ConversationState:
        """Generate casual conversation response"""
        print("Casual 대화 모드")
        
        messages = state["messages"]
        current_message = state["current_message"]
        
        # Special handling for time_orientation assessment answer
        if state.get("is_assessment_answer", False) and state.get("last_assessment_task") == "time_orientation":
            return self._generate_time_travel_transition(state)
        
        # Determine if lightweight chat should be used
        use_lightweight = (state.get("question_message_relevance", 1.0) < self.config.fallback_threshold or
                          "cached" in str(state.get("selected_question", "")).lower())
        
        if use_lightweight:
            print("경량 대화 시스템 사용 (gpt-5-nano)")
            ai_response = self._lightweight_chat(current_message)
            response_type = "casual_lightweight"
        else:
            print("일반 casual 대화 모드")
            ai_response = self._standard_casual_chat(current_message, messages)
            response_type = "casual"
        
        return {
            **state,
            "ai_response": ai_response,
            "response_type": response_type,
            "workflow_stage": "casual_chat"
        }

    def _generate_time_travel_transition(self, state: ConversationState) -> ConversationState:
        """Generate time travel transition after time_orientation assessment"""
        current_message = state["current_message"]
        photo_metadata = state.get("photo_metadata", {})
        
        # Extract date info from user response
        date_info = self._extract_date_from_message(current_message)
        years_ago = self._calculate_years_ago(photo_metadata)
        
        # Generate time travel intro
        time_travel_intro = self._generate_time_travel_intro(date_info, years_ago)
        
        # Generate photo-based question using JSON dump
        photo_question = self._generate_photo_based_question(photo_metadata)
        
        immersive_transition = f"{time_travel_intro} {photo_question}"
        
        return {
            **state,
            "ai_response": immersive_transition,
            "response_type": "immersive_transition",
            "workflow_stage": "time_travel_transition"
        }

    def _generate_time_travel_intro(self, date_info: tuple, years_ago: int) -> str:
        """Generate time travel introduction based on user date response"""
        date_type, date_value = date_info
        
        if date_type == "unclear":
            return f"괜찮아요! 정확한 날짜가 기억나지 않으셔도 돼요. {TIME_TRAVEL_INTRO_TEMPLATE.format(years_ago=years_ago)} 3... 2...1"
        elif date_type == "specific":
            return f"오늘은 {CURRENT_YEAR}년 9월 {date_value}일... {TIME_TRAVEL_INTRO_TEMPLATE.format(years_ago=years_ago)} 3... 2...1"
        else:
            return f"그럼 이제 {TIME_TRAVEL_INTRO_TEMPLATE.format(years_ago=years_ago)} 3... 2...1"

    def _extract_date_from_message(self, message: str) -> tuple:
        """Extract date information from user message"""
        # Specific date patterns
        date_patterns = [r'9월\s*(\d{1,2})일', r'(\d{1,2})일']
        
        for pattern in date_patterns:
            match = re.search(pattern, message)
            if match:
                day = int(match.group(1))
                if 1 <= day <= 31:
                    return ("specific", day)
        
        # Unclear expressions
        unclear_patterns = [r'모르겠어|기억.*안.*나|잘.*모르겠어|확실하지.*않아']
        
        for pattern in unclear_patterns:
            if re.search(pattern, message):
                return ("unclear", None)
        
        return ("none", None)

    def _generate_photo_based_question(self, photo_metadata: Dict[str, Any]) -> str:
        """Generate photo-based question using simple JSON dump"""
        prompt = f"""다음 사진 정보를 바탕으로 할머니, 할아버지가 추억을 회상할 수 있는 따뜻하고 자연스러운 질문을 1개 생성해주세요.

        사진 정보: {json.dumps(photo_metadata, ensure_ascii=False)}

        요구사항:
        1. 부드럽고 따뜻한 말투로 질문
        2. 구체적인 사진 속 요소를 언급
        3. 감정과 추억을 자연스럽게 이끌어낼 수 있는 질문
        4. 한 문장으로 간단명료하게

        질문:"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            generated_question = response.content.strip()
            
            if ":" in generated_question:
                generated_question = generated_question.split(":", 1)[1].strip()
            
            return generated_question
        except Exception as e:
            print(f"질문 생성 중 오류: {e}")
            return "이 사진을 보니 어떤 기억이 떠오르시나요?"

    def _calculate_years_ago(self, photo_metadata: Dict[str, Any]) -> int:
        """Calculate years ago from photo metadata"""
        if 'year' in photo_metadata:
            photo_year = photo_metadata['year']
        elif 'date_taken' in photo_metadata:
            try:
                photo_year = int(photo_metadata['date_taken'][:4])
            except (ValueError, TypeError):
                photo_year = CURRENT_YEAR - DEFAULT_YEARS_AGO
        elif 'time_period' in photo_metadata:
            time_period = photo_metadata['time_period']
            if '1990년대 후반' in time_period:
                photo_year = 1998
            elif '1990년대 전반' in time_period:
                photo_year = 1993
            elif '2000년대 초반' in time_period:
                photo_year = 2003
            else:
                photo_year = CURRENT_YEAR - DEFAULT_YEARS_AGO
        else:
            photo_year = CURRENT_YEAR - DEFAULT_YEARS_AGO
        
        years_ago = CURRENT_YEAR - photo_year
        return max(1, years_ago)

    def _lightweight_chat(self, current_message: str) -> str:
        """Lightweight chat using gpt-5-nano"""
        try:
            simple_message = f"{LIGHTWEIGHT_CHAT_PROMPT}\n\n사용자 메시지: {current_message}\n\n자연스럽게 응답해주세요:"
            response = self.lightweight_llm.invoke([HumanMessage(content=simple_message)])
            return response.content
        except Exception as e:
            print(f"경량 대화 실패: {e}")
            return "네, 맞아요. 계속 얘기해주세요!"

    def _standard_casual_chat(self, current_message: str, messages: List) -> str:
        """Standard casual conversation"""
        conversation_messages = [SystemMessage(content=CASUAL_CHAT_SYSTEM_PROMPT)]
        conversation_messages.extend(messages)
        conversation_messages.append(HumanMessage(content=current_message))
        
        try:
            response = self.llm.invoke(conversation_messages)
            return response.content.strip()
        except Exception as e:
            print(f"일반 대화 생성 실패: {e}")
            return self._lightweight_chat(current_message)

    def _extract_target_object_from_question(self, question: str, photo_metadata: Dict[str, Any]) -> str:
        """Extract target object from naming question using LLM analysis"""
        try:
            all_objects = []
            
            # Extract from objects
            objects = photo_metadata.get("objects", [])
            for obj in objects:
                if isinstance(obj, dict):
                    obj_name = obj.get("name", "")
                    if obj_name:
                        all_objects.append(obj_name)
            
            # Extract from people's items
            people = photo_metadata.get("people", [])
            for person in people:
                if isinstance(person, dict):
                    items = person.get("items", [])
                    all_objects.extend(items)
            
            all_objects = list(set([obj for obj in all_objects if obj]))
            
            if not all_objects:
                return ""
            
            system_msg = f"""다음 질문에서 실제로 답변을 요구하는 객체가 무엇인지 찾아주세요.
            
            질문: "{question}"
            사진에 있는 가능한 객체들: {', '.join(all_objects)}
            
            질문에서 직접적으로 묻고 있는 객체의 이름만 반환해주세요.
            객체 이름만 반환:"""
            
            response = self.llm.invoke([SystemMessage(content=system_msg)])
            target_object = response.content.strip().strip('"\'')
            
            if target_object in all_objects:
                return target_object
            else:
                for obj in all_objects:
                    if obj in target_object or target_object in obj:
                        return obj
                return ""
                
        except Exception as e:
            print(f"질문에서 타겟 객체 추출 실패: {e}")
            return ""

    def _cache_question(self, task_name: str, question: str, context_score: float):
        """Cache question for future reuse"""
        timestamp = datetime.now().timestamp()
        
        if task_name not in self.question_cache:
            self.question_cache[task_name] = []
        
        self.question_cache[task_name].append((question, context_score, timestamp))
        
        if len(self.question_cache[task_name]) > MAX_CACHE_SIZE:
            self.question_cache[task_name].sort(key=lambda x: x[2])
            removed_question = self.question_cache[task_name].pop(0)
            print(f"캐시 크기 초과: 오래된 질문 삭제 - {removed_question[0][:50]}...")
        
        print(f"질문 캐시됨 ({task_name}): {question[:50]}... (점수: {context_score:.2f})")

    # === Conditional edge decision functions ===
    
    def _decide_conversation_mode(self, state: ConversationState) -> str:
        """Decide conversation mode"""
        return state["conversation_mode"]

    def _decide_cache_usage(self, state: ConversationState) -> str:
        """Decide whether to use cached questions"""
        return "use_cached" if state.get("cached_question_found", False) else "generate_new"

    # === Main execution functions ===
    
    def start_conversation(self, photo_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start conversation with dynamic time_orientation question"""
        years_ago = self._calculate_years_ago(photo_metadata or {})
        
        time_orientation_question = TIME_ORIENTATION_TEMPLATE.format(
            years_ago=years_ago, 
            current_year=CURRENT_YEAR
        )

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
        """Process message with conversation history"""
        print(f"\n{'='*60}")
        print(f"사용자 입력: {message}")
        print(f"대화 히스토리: {len(conversation_history)}개 메시지")
        if photo_metadata:
            print(f"사진 메타데이터: {len(photo_metadata)}개 필드")
        print(f"{'='*60}")
        
        # Convert conversation history to LangChain messages
        messages = []
        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Initialize state
        initial_state: ConversationState = {
            "messages": messages,
            "current_message": message,
            "task_scores": {},
            "selected_task": "",
            "task_message_relevance": 0.0,
            "generated_questions": [],
            "selected_question": "",
            "question_message_relevance": 0.0,
            "conversation_mode": "assessment",
            "ai_response": "",
            "response_type": "",
            "workflow_stage": "",
            "is_assessment_answer": False,
            "last_assessment_question": "",
            "last_assessment_task": "",
            "assessment_score": 0.0,
            "score_details": {},
            "cached_question_found": False,
            "cached_question_score": 0.0,
            "reused_question": "",
            "photo_metadata": photo_metadata or {},
            "turn_counter": 0,
            "pending_recall_items": [],
            "recall_scheduled_turn": -1,
            "recall_question_type": "좋아하는",
            "registration_phase": "none"
        }
        
        # Execute graph
        final_state = self.graph.invoke(initial_state)
        
        print(f"\n{'결과':=^60}")
        print(f"AI 응답: {final_state['ai_response']}")
        print(f"응답 타입: {final_state['response_type']}")
        print(f"워크플로우 단계: {final_state['workflow_stage']}")
        
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
            "is_assessment_answer": final_state.get("is_assessment_answer", False),
            "last_assessment_question": final_state.get("last_assessment_question", ""),
            "last_assessment_task": final_state.get("last_assessment_task", ""),
            "assessment_score": final_state.get("assessment_score", 0.0),
            "score_details": final_state.get("score_details", {})
        }

    def get_cache_status(self):
        """Get cache status for debugging"""
        if not self.question_cache:
            return "캐시가 비어있습니다."
        
        status = "=== 질문 캐시 상태 ===\n"
        for task_name, questions in self.question_cache.items():
            status += f"\n{task_name}: {len(questions)}개 질문\n"
            for i, (question, score, timestamp) in enumerate(questions, 1):
                time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
                status += f"  {i}. {question[:60]}... (점수: {score:.2f}, 시간: {time_str})\n"
        
        return status

# === Test execution ===

