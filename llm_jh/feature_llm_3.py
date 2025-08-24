"""
3. fallback 구현
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
    conversation_mode: Literal["assessment", "casual", "fallback"] 
    ai_response: str                       
    response_type: str                     
    workflow_stage: str                    
    retry_count: int                       # 재시도 횟수 추가
    best_question: str                     # 최선의 질문 저장
    best_score: float                      # 최선의 점수 저장

@dataclass
class ChatbotConfig:
    openai_api_key: str                     
    assessment_threshold: float = 0.5       
    fallback_threshold: float = 0.7         
    model_name: str = "gpt-4o-mini"
    max_retries: int = 2                   # 최대 재시도 횟수

ASSESSMENT_TASKS = {
    "registration_recall": {
        "description": 
        """기억 등록은 즉각적인 기억력을 평가하고, 회상은 기억을 유지하는 능력을 평가하는 항목입니다.
          messages 최근 5개 turn 내에서 동일 선상에서 비교될 수 있는 단어/고유명사가 3개 이상 나오면 본 평가내역을 활용할 수 있습니다.""",
        "example_questions": [
            "아까 말씀하신 과일 중 사과, 배, 포도를 어릴 때 가장 좋아했던 순서대로 말씀해주세요.",
            "아까 말씀하신 자녀 중 영희, 철수, 길동이를 살가운 순서대로 말씀해주시겠어요?",
            "아까 말씀하신 공책, 필통, 샤프를 어릴 적 갖고 싶었던 순서대로 말씀해주세요.",
            "콩, 생선, 고추들을 어릴 적 싫어했던 순서대로 말씀해주세요.",
            "콩, 생선, 고추들을 요즘 좋아하시는 순서대로 말씀해주세요."
        ]
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
        ]
    },
    "time_orientation": {
        "description": 
        """현재 자신이 놓여있는 시간, 날짜, 계절 등의 상황을 올바르게 인식하는 능력을 평가합니다.
        시간 관련 humanmassage가 본 평가항목에 대한 트리거가 됩니다.
        example_questions의 응용을 최소화하여 질문을 생성하세요.
        """,
        "example_questions": [
            "올해는 몇년도인가요?"
        ]
    }
}

load_dotenv()
API_KEY = os.getenv("GPT_API_KEY")

config = ChatbotConfig(
    openai_api_key=API_KEY,  
    assessment_threshold=0.8,
    fallback_threshold=0.7,
    max_retries=2
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
        """LangGraph 워크플로우 구성 - 기존 노드 재활용"""
        workflow = StateGraph(ConversationState)
        
        # 기존 노드들만 사용
        workflow.add_node("calculate_task_scores", self.calculate_task_scores)
        workflow.add_node("select_best_task", self.select_best_task)
        workflow.add_node("check_assessment_threshold", self.check_assessment_threshold)
        workflow.add_node("generate_questions", self.generate_questions)
        workflow.add_node("calculate_question_similarities", self.calculate_question_similarities)
        workflow.add_node("select_best_question", self.select_best_question)
        workflow.add_node("check_context_relevance", self.check_context_relevance)
        workflow.add_node("output_assessment_question", self.output_assessment_question)
        workflow.add_node("casual_conversation", self.casual_conversation)
        workflow.add_node("fallback_conversation", self.fallback_conversation)
        
        # 시작점 설정
        workflow.set_entry_point("calculate_task_scores")
        
        # 기본 엣지
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
        
        # 핵심: check_context_relevance에서 3가지 분기
        workflow.add_conditional_edges(
            "check_context_relevance",
            self._decide_final_output,
            {
                "assessment": "output_assessment_question",
                "retry": "generate_questions",  # 기존 노드 재활용!
                "fallback": "fallback_conversation"
            }
        )
        
        # 종료 노드들
        workflow.add_edge("output_assessment_question", END)
        workflow.add_edge("casual_conversation", END)
        workflow.add_edge("fallback_conversation", END)
        
        return workflow.compile()

    def calculate_task_scores(self, state: ConversationState) -> ConversationState:
        """1. 각 태스크별 적합도 계산 - example_questions와의 유사도 기반"""
        print("1단계: 태스크별 적합도 계산...")
        current_message = state["current_message"]
        task_scores = {}
        
        for task_name, task_info in ASSESSMENT_TASKS.items():
            try:
                example_questions = task_info["example_questions"]
                
                if not example_questions:
                    task_scores[task_name] = 0.0
                    continue
                
                # 현재 메시지와 각 예시 질문들과의 유사도 계산
                all_texts = [current_message] + example_questions
                
                # TF-IDF 벡터화
                tfidf_matrix = self.vectorizer.fit_transform(all_texts)
                
                # 현재 메시지 벡터 (첫 번째)
                message_vector = tfidf_matrix[0:1]
                
                # 예시 질문들 벡터 (나머지)
                example_vectors = tfidf_matrix[1:]
                
                # 코사인 유사도 계산
                similarity_scores = cosine_similarity(message_vector, example_vectors).flatten()
                
                # 최대 유사도를 해당 태스크의 점수로 사용
                max_similarity = float(np.max(similarity_scores))
                task_scores[task_name] = max_similarity
                
                print(f"  {task_name}: {max_similarity:.2f}")
                
            except Exception as e:
                print(f"  {task_name}: 평가 실패 ({e})")
                task_scores[task_name] = 0.0
        
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
        
        system_msg = """당신은 친근하고 따뜻한 대화 상대입니다.
사용자와 자연스럽고 편안한 대화를 나누며, 노인 분들이 좋아할 만한 친근한 응답을 해주세요.
대화 히스토리를 참고하여 맥락에 맞는 자연스러운 응답을 해주세요."""

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

    def fallback_conversation(self, state: ConversationState) -> ConversationState:
        """폴백 대화 처리 - 간접적 평가 포함 대화"""
        print("폴백 대화 모드")
        messages = state["messages"]
        current_message = state["current_message"]
        
        system_msg = f"""당신은 친근한 대화 상대입니다. 
현재 사용자와 자연스러운 대화를 이어가면서, 향후 {state['selected_task']} 평가를 위한 
정보를 간접적으로 수집할 수 있는 대화를 해주세요.

직접적인 평가 질문보다는 자연스러운 대화를 통해 관련 정보를 얻을 수 있도록 해주세요."""

        conversation_messages = [SystemMessage(content=system_msg)]
        conversation_messages.extend(messages)
        conversation_messages.append(HumanMessage(content=current_message))
        
        try:
            response = self.llm.invoke(conversation_messages)
            ai_response = response.content.strip()
            response_type = "fallback"
            workflow_stage = "fallback_conversation"
        except Exception as e:
            print(f"폴백 대화 생성 실패: {e}")
            ai_response = "그렇군요. 더 자세히 얘기해 주세요."
            response_type = "error"
            workflow_stage = "error"
        
        return {
            **state,
            "ai_response": ai_response,
            "response_type": response_type,
            "workflow_stage": workflow_stage
        }

    # === 조건부 엣지 결정 함수들 ===
    
    def _decide_conversation_mode(self, state: ConversationState) -> str:
        """대화 모드 결정"""
        return state["conversation_mode"]

    def _decide_final_output(self, state: ConversationState) -> str:
        """최종 출력 형태 결정 - 3가지 분기"""
        relevance = state["question_message_relevance"]
        threshold = self.config.fallback_threshold
        retry_count = state.get("retry_count", 0)
        max_retries = self.config.max_retries
        
        # 임계값을 넘으면 즉시 출력
        if relevance >= threshold:
            print(f"평가 질문 출력 (맥락 점수 {relevance:.2f} >= 임계값 {threshold})")
            return "assessment"
        
        # 재시도 한계 확인
        if retry_count < max_retries:
            print(f"질문 재생성 시도 ({retry_count + 1}/{max_retries + 1})")
            # retry_count 증가
            state["retry_count"] = retry_count + 1
            return "retry"
        
        # 재시도 한계 도달
        print(f"재시도 한계 도달 - 폴백 모드")
        return "fallback"

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
            "best_question": "",  # 사용하지 않지만 호환성을 위해 유지
            "best_score": 0.0     # 사용하지 않지만 호환성을 위해 유지
        }
        
        # 그래프 실행
        final_state = self.graph.invoke(initial_state)
        
        print(f"\n{'결과':=^60}")
        print(f"AI 응답: {final_state['ai_response']}")
        print(f"응답 타입: {final_state['response_type']}")
        print(f"워크플로우 단계: {final_state['workflow_stage']}")
        print(f"재시도 횟수: {final_state.get('retry_count', 0)}")
        
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
            "retry_count": final_state.get("retry_count", 0),
            "best_question": final_state.get("best_question", ""),
            "best_score": final_state.get("best_score", 0.0)
        }

# === 테스트 실행 ===

if __name__ == "__main__":
    # LangGraph 챗봇 생성
    chatbot = LangGraphDementiaChatbot(config)
    
    # 테스트
    conversation_history = [
        {"role": "user", "content": "안녕하세요. 오늘 날씨가 참 좋네요."},
        {"role": "assistant", "content": "안녕하세요! 정말 좋은 날씨네요. 어떻게 지내셨어요?"},
    ]
    
    new_message = "어제 시장에서 사과, 배, 포도를 샀어요."
    
    result = chatbot.chat_with_history(new_message, conversation_history)
    
    # 결과 출력
    print(f"\n{'테스트 결과':=^80}")
    print(f"메시지: '{result['user_message']}'")
    print(f"선택 태스크: {result['selected_task']} (점수: {result['task_message_relevance']:.2f})")
    print(f"질문 맥락 점수: {result['question_message_relevance']:.2f}")
    print(f"응답 타입: {result['response_type']}")
    print(f"워크플로우 단계: {result['workflow_stage']}")
    print(f"재시도 횟수: {result['retry_count']}")
    print(f"최선 질문 점수: {result['best_score']:.2f}")
    print(f"AI 응답: {result['ai_response']}")
    
    if result['generated_questions']:
        print(f"\n생성된 질문들:")
        for i, q in enumerate(result['generated_questions'], 1):
            print(f"  {i}. {q}")
    
    if result['best_question']:
        print(f"\n최선의 질문: {result['best_question']}")
    
    print(f"워크플로우 설명':=^80")
    print("간소화된 Fallback 시스템:")
    print("1. Task 적합도 → Assessment 모드 진입")
    print("2. 질문 생성 → 맥락 적합성 평가")
    print("3. 임계값 미달시 → 재시도 (최대 2번)")
    print("4. 재시도 한계 후 → 간접적 평가 포함 Casual 대화")
    print("5. Delayed assessment 제거로 단순화")