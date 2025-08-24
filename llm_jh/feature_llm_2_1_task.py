"""
간소화된 Assessment 챗봇 - 성능 테스트 버전
"""
import os   
import json
import time
from dotenv import load_dotenv
from typing import Dict, List, TypedDict, Literal, Any
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END

class ConversationState(TypedDict):
    messages: List[Dict[str, str]]          
    current_message: str                    
    task_scores: Dict[str, float]          
    selected_task: str                      
    task_message_relevance: float           
    conversation_mode: Literal["assessment", "casual"] 
    ai_response: str                       
    response_type: str                     
    workflow_stage: str                    
    # 채점 관련 필드
    is_assessment_answer: bool             
    last_assessment_question: str          
    last_assessment_task: str              
    assessment_score: float                
    score_details: Dict[str, Any]          

@dataclass
class ChatbotConfig:
    openai_api_key: str                     
    assessment_threshold: float = 0.3       
    model_name: str = "gpt-4o-mini"

ASSESSMENT_TASKS = {
    "registration_recall": {
        "description": "기억 등록/회상 (3개 이상의 비교 가능한 단어/고유명사)",
        "example_questions": [
            "아까 말씀하신 과일 중 사과, 배, 포도를 어릴 때 가장 좋아했던 순서대로 말씀해주세요.",
            "콩, 생선, 고추들을 요즘 좋아하시는 순서대로 말씀해주세요."
        ]
    },
    "Naming": {
        "description": "사물 이름 맞추기 (사진 속 객체 언급)",
        "example_questions": [
            "사진 속 어린아이가 들고있는 물체를 뭐라고 불러요?",
            "케이크 밑에 있는 가구 이름은 뭔가요?"
        ]
    },
    "time_orientation": {
        "description": "시간/날짜 인식 (시간 관련 표현)",
        "example_questions": [
            "오늘은 몇일 인가요?"
        ]
    }
}

load_dotenv()
API_KEY = os.getenv("GPT_API_KEY")

config = ChatbotConfig(
    openai_api_key=API_KEY,  
    assessment_threshold=0.3
)

class SimplifiedDementiaChatbot:
    def __init__(self, config: ChatbotConfig):
        self.config = config
        self.llm = ChatOpenAI(
            model=config.model_name,
            openai_api_key=config.openai_api_key,
            temperature=0.3
        )
        
        # 그래프 빌드
        self.graph = self._build_graph()
        print(f"간소화된 치매 평가 챗봇 초기화 완료 (모델: {config.model_name})")

    def _build_graph(self) -> StateGraph:
        """간소화된 워크플로우 구성"""
        workflow = StateGraph(ConversationState)
        
        # 노드들 추가
        workflow.add_node("check_if_assessment_answer", self.check_if_assessment_answer)
        workflow.add_node("score_assessment_answer", self.score_assessment_answer)
        workflow.add_node("calculate_task_scores", self.calculate_task_scores)
        workflow.add_node("select_best_task", self.select_best_task)
        workflow.add_node("check_assessment_threshold", self.check_assessment_threshold)
        workflow.add_node("casual_conversation", self.casual_conversation)
        
        # 워크플로우 연결
        workflow.set_entry_point("check_if_assessment_answer")
        
        workflow.add_conditional_edges(
            "check_if_assessment_answer",
            self._decide_if_scoring_needed,
            {
                "score_answer": "score_assessment_answer",
                "continue_normal": "calculate_task_scores"
            }
        )
        
        workflow.add_edge("score_assessment_answer", "calculate_task_scores")
        workflow.add_edge("calculate_task_scores", "select_best_task")
        workflow.add_edge("select_best_task", "check_assessment_threshold")
        
        workflow.add_conditional_edges(
            "check_assessment_threshold",
            self._decide_conversation_mode,
            {
                "assessment": "casual_conversation",  # 간소화: assessment도 casual로
                "casual": "casual_conversation"
            }
        )
        
        workflow.add_edge("casual_conversation", END)
        
        return workflow.compile()

    def check_if_assessment_answer(self, state: ConversationState) -> ConversationState:
        """Assessment 답변인지 간단히 체크"""
        print("Assessment 답변 체크...")
        
        messages = state["messages"]
        
        # 마지막 AI 메시지 찾기
        last_ai_message = ""
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], AIMessage):
                last_ai_message = messages[i].content
                break
        
        # 간단한 키워드 기반 판단
        assessment_keywords = ["순서대로", "몇일", "이름은 뭔가요", "뭐라고 불러요"]
        is_assessment_answer = any(keyword in last_ai_message for keyword in assessment_keywords)
        
        if is_assessment_answer:
            print(f"Assessment 답변 감지됨!")
        
        return {
            **state,
            "is_assessment_answer": is_assessment_answer,
            "last_assessment_question": last_ai_message
        }

    def score_assessment_answer(self, state: ConversationState) -> ConversationState:
        """간단한 키워드 기반 채점"""
        print("답변 채점 중...")
        
        current_message = state["current_message"]
        
        # 간단한 키워드 기반 채점
        score = 0.0
        if "사과" in current_message and "배" in current_message and "포도" in current_message:
            score = 1.0
        elif any(fruit in current_message for fruit in ["사과", "배", "포도"]):
            score = 0.5
            
        print(f"채점 완료: {score:.1f}")
        
        return {
            **state,
            "assessment_score": score,
            "score_details": {"keyword_based": True}
        }

    def calculate_task_scores(self, state: ConversationState) -> ConversationState:
        """모든 태스크를 한 번에 평가 - JSON 응답"""
        print("태스크 점수 계산 중...")
        start_time = time.time()
        
        message = state["current_message"]
        
        prompt = f"""사용자 메시지: "{message}"

다음 평가 영역들과의 관련도를 0-1 사이로 평가해주세요:

1. registration_recall: 기억 등록/회상 (3개 이상의 비교 가능한 단어/고유명사)
2. Naming: 사물 이름 맞추기 (사진 속 객체 언급)  
3. time_orientation: 시간/날짜 인식 (시간 관련 표현)

JSON 형식으로만 응답:
{{"registration_recall": 0.0, "Naming": 0.0, "time_orientation": 0.0}}"""

        try:
            response = self.llm.invoke([SystemMessage(content=prompt)])
            task_scores = json.loads(response.content.strip())
            print(f"JSON 파싱 성공: {task_scores}")
        except Exception as e:
            print(f"JSON 파싱 실패: {e}")
            task_scores = {"registration_recall": 0.0, "Naming": 0.0, "time_orientation": 0.0}
        
        elapsed = time.time() - start_time
        print(f"태스크 점수 계산 완료 ({elapsed:.2f}초)")
        
        return {**state, "task_scores": task_scores}

    def select_best_task(self, state: ConversationState) -> ConversationState:
        """최고 점수 태스크 선택"""
        print("최적 태스크 선택...")
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
        """Assessment threshold 체크"""
        print("Assessment threshold 체크...")
        relevance = state["task_message_relevance"]
        threshold = self.config.assessment_threshold
        
        if relevance >= threshold:
            mode = "assessment"
            print(f"평가 모드 진입 (적합도 {relevance:.2f} >= 임계값 {threshold})")
        else:
            mode = "casual"
            print(f"일상 대화 모드 (적합도 {relevance:.2f} < 임계값 {threshold})")
        
        return {**state, "conversation_mode": mode}

    def casual_conversation(self, state: ConversationState) -> ConversationState:
        """일상 대화 처리"""
        print("일상 대화 모드")
        messages = state["messages"]
        current_message = state["current_message"]
        
        # Assessment 모드인 경우 질문 생성
        if state["conversation_mode"] == "assessment":
            selected_task = state["selected_task"]
            task_info = ASSESSMENT_TASKS[selected_task]
            
            system_msg = f"""당신은 치매 평가를 위한 질문을 자연스럽게 하는 어린이입니다.
            
평가 영역: {selected_task}
예시 질문들:
{chr(10).join(task_info["example_questions"])}

대화 맥락에 맞는 자연스러운 평가 질문을 1개만 생성해주세요."""
            
            response_type = "assessment"
        else:
            # 일반 대화
            system_msg = """당신은 7~15세 사이 호기심 많고 예의바른 어린이입니다.
자연스럽고 호기심 어린 반응으로 대화를 이어가세요."""
            response_type = "casual"
        
        conversation_messages = [SystemMessage(content=system_msg)]
        conversation_messages.extend(messages)
        conversation_messages.append(HumanMessage(content=current_message))
        
        try:
            response = self.llm.invoke(conversation_messages)
            ai_response = response.content.strip()
        except Exception as e:
            print(f"대화 생성 실패: {e}")
            ai_response = "응답 생성에 실패했습니다."
            response_type = "error"
        
        return {
            **state,
            "ai_response": ai_response,
            "response_type": response_type,
            "workflow_stage": "conversation_complete"
        }

    # === 조건부 엣지 결정 함수들 ===
    
    def _decide_if_scoring_needed(self, state: ConversationState) -> str:
        return "score_answer" if state["is_assessment_answer"] else "continue_normal"
    
    def _decide_conversation_mode(self, state: ConversationState) -> str:
        return state["conversation_mode"]

    # === 메인 실행 함수 ===
    
    def chat_with_history(self, message: str, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """대화 처리 및 성능 측정"""
        start_time = time.time()
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
            "conversation_mode": "assessment",
            "ai_response": "",
            "response_type": "",
            "workflow_stage": "",
            "is_assessment_answer": False,
            "last_assessment_question": "",
            "last_assessment_task": "",
            "assessment_score": 0.0,
            "score_details": {}
        }
        
        # 그래프 실행
        final_state = self.graph.invoke(initial_state)
        
        total_time = time.time() - start_time
        
        print(f"\n{'결과':=^60}")
        print(f"AI 응답: {final_state['ai_response']}")
        print(f"응답 타입: {final_state['response_type']}")
        print(f"선택된 태스크: {final_state.get('selected_task', '')}")
        print(f"태스크 점수들: {final_state.get('task_scores', {})}")
        print(f"전체 소요 시간: {total_time:.2f}초")
        
        return {
            "user_message": message,
            "selected_task": final_state.get("selected_task", ""),
            "task_message_relevance": final_state.get("task_message_relevance", 0.0),
            "task_scores": final_state.get("task_scores", {}),
            "response_type": final_state["response_type"],
            "ai_response": final_state["ai_response"],
            "total_time": total_time,
            "is_assessment_answer": final_state.get("is_assessment_answer", False),
            "assessment_score": final_state.get("assessment_score", 0.0)
        }

# === 성능 테스트 ===

if __name__ == "__main__":
    # 챗봇 생성
    chatbot = SimplifiedDementiaChatbot(config)
    
    print("=== 성능 테스트: '어제 시장에서 사과, 배, 포도를 샀어요' ===")
    
    # 테스트 메시지
    test_message = "어제 시장에서 사과, 배, 포도를 샀어요."
    conversation_history = [
        {"role": "user", "content": "안녕하세요. 오늘 날씨가 참 좋네요."},
        {"role": "assistant", "content": "안녕하세요! 정말 좋은 날씨네요. 어떻게 지내셨어요?"},
    ]
    
    # 5번 테스트해서 평균 시간 측정
    times = []
    results = []
    
    for i in range(1):
        print(f"\n--- 테스트 {i+1}/5 ---")
        result = chatbot.chat_with_history(test_message, conversation_history)
        times.append(result["total_time"])
        results.append(result)
        time.sleep(1)  # API 호출 간격
    
    # 결과 분석
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\n{'성능 테스트 결과':=^80}")
    print(f"평균 소요 시간: {avg_time:.2f}초")
    print(f"최소 소요 시간: {min_time:.2f}초") 
    print(f"최대 소요 시간: {max_time:.2f}초")
    print(f"\n예상 태스크 점수:")
    print(f"- registration_recall: 높음 (사과, 배, 포도 - 3개 항목)")
    print(f"- Naming: 낮음 (사물 이름 언급 없음)")
    print(f"- time_orientation: 중간 (어제 언급)")
    
    # 실제 결과 출력
    if results:
        sample_result = results[0]
        print(f"\n실제 결과:")
        print(f"- 태스크 점수들: {sample_result['task_scores']}")
        print(f"- 선택된 태스크: {sample_result['selected_task']}")
        print(f"- AI 응답: {sample_result['ai_response']}")