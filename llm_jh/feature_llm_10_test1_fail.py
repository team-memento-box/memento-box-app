"""
10. test for gpt-5-nano 응답 시간 단축
"""

import os
import time
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from feature_llm_8 import LangGraphDementiaChatbot, ChatbotConfig

load_dotenv()
API_KEY = os.getenv("GPT_API_KEY")

config = ChatbotConfig(openai_api_key=API_KEY)
bot = LangGraphDementiaChatbot(config)

# === 대화 시뮬레이션 ===
# 초기 대화 히스토리 설정
conversation_history = [
    HumanMessage(content="이건 애들 어릴 때 마당에서 찍은 사진이야."),
    AIMessage(content="오른쪽에 강아지가 있네요."),
    HumanMessage(content="응 강아지 이름은 아롱이야."),
    AIMessage(content="와 강아지를 기르셨군요.")
]
turn_count = 0
MAX_TURNS = 2  # 최대 턴 제한

def run_turn(user_message: str, simulate_response: bool = False):
    global turn_count
    turn_count += 1
    
    # 최대 턴 수 체크
    if turn_count > MAX_TURNS:
        print(f"\n최대 턴 수 ({MAX_TURNS}) 도달. 대화를 종료합니다.")
        return None
    
    print(f"\n턴 {turn_count}/{MAX_TURNS}")
    
    state = {
        "messages": conversation_history.copy(),
        "current_message": user_message,
        "task_scores": {},
        "selected_task": "",
        "task_message_relevance": 0.0,
        "generated_questions": [],
        "question_similarities": [],
        "selected_question": "",
        "question_message_relevance": 0.0,
        "conversation_mode": "casual",
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
        "reused_question": ""
    }

    print(f"\n=== 사용자 입력: {user_message} ===")

    start_time = time.time()
    result = bot.graph.invoke(state)
    elapsed = time.time() - start_time

    # 히스토리 업데이트
    conversation_history.append(HumanMessage(content=user_message))
    if result.get("ai_response"):
        conversation_history.append(AIMessage(content=result["ai_response"]))

    # 응답 출력
    print(f"AI: {result['ai_response']}")
    print(f"처리 시간: {elapsed:.2f}초")
    print(f"캐시 여부: {result.get('cached_question_found')}")
    if result.get("cached_question_found"):
        print(f"   ↳ 재사용 질문: {result.get('reused_question')}")
        print(f"   ↳ 캐시 점수: {result.get('cached_question_score'):.3f}")
    
    # AI 자동 응답 시뮬레이션 (모든 응답에 대해 작동)
    if simulate_response:
        print(f"\nAI 답변 시뮬레이션 시작...")
        
        # 평가 질문인 경우와 일반 대화인 경우 구분
        if result.get("response_type") == "assessment":
            simulated_answer = bot.simulate_user_response(
                result["ai_response"], 
                conversation_history
            )
            print(f"평가 질문에 대한 답변: {simulated_answer}")
        else:
            # 일반 대화인 경우도 AI가 계속 대화 이어가도록
            simulated_answer = bot.simulate_user_response(
                result["ai_response"], 
                conversation_history
            )
            print(f"일반 대화 응답: {simulated_answer}")
        
        # 시뮬레이션된 답변으로 다시 한 턴 실행
        print(f"\n시뮬레이션된 답변으로 다음 턴 진행...")
        next_result = run_turn(simulated_answer, simulate_response=True)
        
        # None 반환시 (최대 턴 도달) 종료
        if next_result is None:
            return result
    
    return result

def print_history():
    print("\n=== 전체 대화 히스토리 ===")
    for msg in conversation_history:
        role = "USER" if isinstance(msg, HumanMessage) else "AI"
        print(f"{role}: {msg.content}")

# === 턴별 실행 ===
if __name__ == "__main__":
    
    print("AI끼리 대화 시뮬레이션 시작!")
    print("=" * 60)
    
    # 초기 히스토리 확인
    print("\n초기 대화 히스토리:")
    print_history()
    
    print("\n" + "=" * 60)
    print("\nAI끼리 완전 자동 대화 시작")
    print("이전 대화 맥락을 바탕으로 새로운 입력 처리...")

    # 기존 히스토리를 바탕으로 새로운 대화 진행
    run_turn("응 집에 고양이, 염소, 강아지를 길렀어", simulate_response=True)
    
    print("\n" + "=" * 60)

    # 전체 히스토리 확인 (초기 + 새로 생성된 대화)
    print("\n전체 대화 히스토리 (초기 + 생성된 대화):")
    print_history()
    
    print("\nAI끼리 대화 시뮬레이션 완료!")
