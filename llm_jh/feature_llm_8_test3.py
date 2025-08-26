"""
3. 모듈 기반 LangGraphDementiaChatbot 캐싱폴백 동작 테스트
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
conversation_history = []

def run_turn(user_message: str, simulate_response: bool = False):
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
    print(f"🤖 AI: {result['ai_response']}")
    print(f"⏱ 처리 시간: {elapsed:.2f}초")
    print(f"🗂 캐시 여부: {result.get('cached_question_found')}")
    if result.get("cached_question_found"):
        print(f"   ↳ 재사용 질문: {result.get('reused_question')}")
        print(f"   ↳ 캐시 점수: {result.get('cached_question_score'):.3f}")
    
    # AI 자동 응답 시뮬레이션 (평가 질문인 경우만)
    if simulate_response and result.get("response_type") == "assessment":
        print(f"\n🤖 AI 답변 시뮬레이션 시작...")
        simulated_answer = bot.simulate_user_response(
            result["ai_response"], 
            conversation_history
        )
        print(f"👴 시뮬레이션된 사용자 답변: {simulated_answer}")
        
        # 시뮬레이션된 답변으로 다시 한 턴 실행
        run_turn(simulated_answer)
    
    return result

def print_history():
    print("\n=== 전체 대화 히스토리 ===")
    for msg in conversation_history:
        role = "USER" if isinstance(msg, HumanMessage) else "AI"
        print(f"{role}: {msg.content}")

# === 턴별 실행 ===
if __name__ == "__main__":
    print("🚀 AI끼리 대화 시뮬레이션 시작!")
    print("=" * 60)
    
    # 턴1: 고양이 언급 → AI가 질문 생성 → AI가 자동으로 적절한 답변 생성
    print("\n📍 AI끼리 완전 자동 대화")
    print("사용자 입력 → 질문 생성 → AI 답변 → 채점 → 캐시 저장 → 다음 턴에서 캐시 활용")
    
    # 첫 턴에서 자동으로 질문 생성하고 AI가 답변까지 생성
    run_turn("고양이, 염소, 강아지를 길렀어", simulate_response=True)

    print("\n" + "=" * 60)
    # 전체 히스토리 확인
    print_history()
    
    print("\n🎉 AI끼리 대화 시뮬레이션 완료!")
    print("첫 번째 입력에서 질문이 생성되고, AI가 자동으로 답변을 만들어 채점까지 완료되었습니다.")
