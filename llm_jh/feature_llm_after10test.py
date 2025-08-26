"""
10. test for gpt-5-nano 응답 시간 단축
"""

import os
import time
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from feature_llm_12 import LangGraphDementiaChatbot, ChatbotConfig

load_dotenv()
API_KEY = os.getenv("GPT_API_KEY")

config = ChatbotConfig(openai_api_key=API_KEY)
bot = LangGraphDementiaChatbot(config)

# === 대화 시뮬레이션 ===
# 빈 대화 히스토리로 처음 시작
conversation_history = []
turn_count = 0
MAX_TURNS = 2  # 최대 턴 제한 (몰입감 시나리오 확인을 위해 증가)

# 샘플 사진 메타데이터 (전역 변수)
sample_photo_metadata = {
    "caption": "공원에서 강아지와 함께 놀고 있는 어린 아이들의 모습",
    "dense_captions": [
        "빨간색 공을 들고 있는 아이", 
        "갈색 강아지가 꼬리를 흔들며 뛰어다니는 모습",
        "나무 그늘 아래 벤치에 앉아 있는 어른들"
    ],
    "mood": "즐겁고 평화로운",
    "time_period": "1990년대 후반",
    "key_objects": ["빨간 공", "강아지", "벤치", "나무"],
    "people_description": "7-8세 정도의 어린 아이 2명과 성인 2명",
    "people_count": 4,
    "time_of_day": "오후",
    # 연도 정보 추가
    "year": 1998,
    "date_taken": "1998-09-15"
}

def run_turn(user_message: str, simulate_response: bool = False):
    global turn_count
    turn_count += 1
    
    # 최대 턴 수 체크
    if turn_count > MAX_TURNS:
        print(f"\n최대 턴 수 ({MAX_TURNS}) 도달. 대화를 종료합니다.")
        return None
    
    print(f"\n턴 {turn_count}/{MAX_TURNS}")
    
    # 이전 AI 메시지에서 상태 정보 추출
    last_ai_message = ""
    if conversation_history:
        for msg in reversed(conversation_history):
            if isinstance(msg, AIMessage):
                last_ai_message = msg.content
                break
    
    # 상태 설정 - time_orientation 관련 체크
    is_time_orientation_answer = "20년 전 그날로 기억 여행을 시작하려고 해요" in last_ai_message
    
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
        "is_assessment_answer": is_time_orientation_answer,
        "last_assessment_question": last_ai_message,
        "last_assessment_task": "time_orientation" if is_time_orientation_answer else "",
        "assessment_score": 0.0,
        "score_details": {},
        "cached_question_found": False,
        "cached_question_score": 0.0,
        "reused_question": "",
        # 상태 추적을 위한 추가 정보
        "last_question_type": "assessment" if is_time_orientation_answer else "casual",
        # 사진 메타데이터 (전역 변수에서 가져오기)
        "photo_metadata": globals().get('sample_photo_metadata', {})
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
    print(f"응답 타입: {result.get('response_type')}")
    print(f"워크플로우 단계: {result.get('workflow_stage')}")
    print(f"캐시 여부: {result.get('cached_question_found')}")
    if result.get("cached_question_found"):
        print(f"   ↳ 재사용 질문: {result.get('reused_question')}")
        print(f"   ↳ 캐시 점수: {result.get('cached_question_score'):.3f}")
    
    # 몰입감 시나리오 관련 정보 출력
    if result.get('is_assessment_answer'):
        print(f"Assessment 답변 감지: {result.get('last_assessment_task')}")
        print(f"채점 점수: {result.get('assessment_score', 0.0):.2f}/1.0")
    
    # AI 자동 응답 시뮬레이션 (모든 응답에 대해 작동)
    if simulate_response:
        print(f"\nAI 답변 시뮬레이션 시작...")
        
        # 평가 질문인 경우와 일반 대화인 경우 구분
        if result.get("response_type") in ["assessment", "assessment_immersive"]:
            simulated_answer = bot.simulate_user_response(
                result["ai_response"], 
                conversation_history
            )
            print(f"평가 질문에 대한 답변: {simulated_answer}")
        elif result.get("response_type") == "immersive_transition":
            # 몰입감 시간 여행 효과 후에는 일반 대화로 계속
            simulated_answer = bot.simulate_user_response(
                result["ai_response"], 
                conversation_history
            )
            print(f"몰입감 전환 후 응답: {simulated_answer}")
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
    print("\nAI끼리 완전 자동 대화 시작 - 몰입감 시나리오 테스트")
    print("처음 대화 시작부터 time_orientation 평가와 몰입감 효과 확인...")

    # AI가 먼저 대화 시작 (time_orientation 몰입감 시나리오)
    print("=== AI 주도 대화 시작 테스트 ===")
    print(f"사진 메타데이터 정보: {len(sample_photo_metadata)}개 필드")
    print(f"  - 주요 객체: {sample_photo_metadata['key_objects']}")
    print(f"  - 인물 수: {sample_photo_metadata['people_count']}명")
    
    start_result = bot.start_conversation(sample_photo_metadata)
    print(f"AI 시작 메시지: {start_result['ai_response']}")
    
    # AI 시작 메시지를 히스토리에 추가
    conversation_history.append(AIMessage(content=start_result["ai_response"]))
    
    # 사용자가 AI 시작 메시지에 응답 (날짜 답변 시뮬레이션)
    simulated_date_response = bot.simulate_user_response(
        start_result["ai_response"], 
        conversation_history
    )
    print(f"시뮬레이션된 날짜 답변: {simulated_date_response}")
    
    # 날짜 답변으로 다음 턴 진행
    run_turn(simulated_date_response, simulate_response=True)
    
    print("\n" + "=" * 60)

    # 전체 히스토리 확인 (초기 + 새로 생성된 대화)
    print("\n전체 대화 히스토리 (초기 + 생성된 대화):")
    print_history()
    
    print("\nAI끼리 대화 시뮬레이션 완료!")
