"""
13. test for naming evaluation with img_description.py integration
"""

import os
import time
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from feature_llm_14 import LangGraphDementiaChatbot, ChatbotConfig

load_dotenv()
API_KEY = os.getenv("GPT_API_KEY")

config = ChatbotConfig(openai_api_key=API_KEY)
bot = LangGraphDementiaChatbot(config)

# === 대화 시뮬레이션 ===
# 빈 대화 히스토리로 처음 시작
conversation_history = []
turn_count = 0
MAX_TURNS = 3  # Naming 평가 테스트를 위해 턴 수 증가

# 샘플 사진 메타데이터 (img_description.py 형식으로 수정 - Naming 테스트용)
sample_photo_metadata = {
    "scene": {
        "location": "실내 거실 (생일 파티용으로 꾸며짐)",
        "event": "생일 파티",
        "core_point": "한 아이의 생일을 가족이 축하하는 장면"
    },
    "social_context": {
        "atmosphere": "즐겁고 따뜻한 가족 중심의 축제 분위기",
        "core_point": "가족이 함께 생일을 축하하며 행복한 시간을 보냄"
    },
    "people": [
        {
            "role": "성인 여성 (어머니 추정)",
            "action": "어린이를 옆에서 지켜봄",
            "expression": "미소",
            "items": []
        },
        {
            "role": "성인 남성 (아버지 추정)",
            "action": "아이 옆에 서서 축하 참여",
            "expression": "웃음",
            "items": []
        },
        {
            "role": "어린이 A (생일 주인공)",
            "action": "케이크 앞에 앉아 있음, 소원을 빌 준비",
            "expression": "기대, 즐거움",
            "items": ["생일 모자"]
        },
        {
            "role": "어린이 B (형제/자매)",
            "action": "옆에서 함께 축하",
            "expression": "미소",
            "items": ["파티 모자"]
        }
    ],
    "objects": [
        {
            "name": "생일 케이크",
            "location": "테이블 중앙",
            "relation": {
                "on_top": ["초 5개"],
                "nearby": ["선물 상자 2개", "쿠키 접시", "오렌지 주스 컵 2개"]
            }
        },
        {
            "name": "풍선",
            "location": "배경 벽 장식",
            "relation": {}
        },
        {
            "name": "파티 모자",
            "location": "각 인물 머리",
            "relation": {"worn_by": ["어린이 A", "어린이 B", "어머니", "아버지"]}
        }
    ],
    # 연도 정보 추가
    "year": 2003,
    "date_taken": "2003-09-15"
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
    print(f"선택된 태스크: {result.get('selected_task')}")
    print(f"태스크 관련성: {result.get('task_message_relevance', 0.0):.3f}")
    print(f"캐시 여부: {result.get('cached_question_found')}")
    if result.get("cached_question_found"):
        print(f"   ↳ 재사용 질문: {result.get('reused_question')}")
        print(f"   ↳ 캐시 점수: {result.get('cached_question_score'):.3f}")
    
    # 생성된 질문들 출력 (Naming 테스트)
    if result.get('generated_questions'):
        print(f"생성된 질문 수: {len(result.get('generated_questions'))}")
        for i, q in enumerate(result.get('generated_questions', []), 1):
            print(f"   {i}. {q}")
    
    # Assessment 답변 관련 정보 출력
    if result.get('is_assessment_answer'):
        print(f"Assessment 답변 감지: {result.get('last_assessment_task')}")
        print(f"채점 점수: {result.get('assessment_score', 0.0):.2f}/1.0")
        score_details = result.get('score_details', {})
        if score_details:
            print(f"채점 세부사항: {score_details}")
    
    # Naming 평가 관련 특별 정보 출력
    if result.get('selected_task') == 'Naming':
        print("=== Naming 평가 특별 정보 ===")
        # 사진에서 추출된 naming 객체들 출력
        naming_objects = bot._extract_naming_objects_from_photo(sample_photo_metadata)
        print(f"사진에서 추출된 naming 객체들: {naming_objects}")
        if result.get('selected_question'):
            print(f"최종 선택된 질문: {result.get('selected_question')}")
            print(f"질문-메시지 관련성: {result.get('question_message_relevance', 0.0):.3f}")
    
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
    print("\nAI끼리 완전 자동 대화 시작 - Naming 평가 테스트")
    print("처음 대화 시작부터 Naming 평가 질문 생성과 채점 확인...")

    # AI가 먼저 대화 시작 (time_orientation 몰입감 시나리오)
    print("=== AI 주도 대화 시작 테스트 ===")
    print(f"사진 메타데이터 정보: {len(sample_photo_metadata)}개 필드")
    
    # naming 객체들 미리 확인
    naming_objects = bot._extract_naming_objects_from_photo(sample_photo_metadata)
    print(f"  - Naming 가능한 객체들: {naming_objects}")
    print(f"  - 사진 장소: {sample_photo_metadata['scene']['location']}")
    print(f"  - 사진 이벤트: {sample_photo_metadata['scene']['event']}")
    print(f"  - 인물 수: {len(sample_photo_metadata['people'])}명")
    
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
    
    # Naming 평가 특별 테스트 추가 
    print("\n" + "=" * 60)
    print("=== Naming 평가 특별 테스트 ===")
    print("사진에서 객체를 직접 언급하여 Naming 평가 트리거 테스트")
    
    # 직접 케이크나 촛불을 언급하는 메시지로 Naming 평가 유도
    naming_trigger_messages = [
        "사진에 케이크가 보이네요!",  
        "촛불이 몇 개나 있을까요?",
        "생일 모자를 쓴 아이가 귀여워요",
        "이 파티 분위기가 좋네요!"
    ]
    
    for i, msg in enumerate(naming_trigger_messages, 1):
        print(f"\n--- Naming 트리거 테스트 {i}/{len(naming_trigger_messages)} ---")
        print(f"테스트 메시지: {msg}")
        
        # 새로운 대화 히스토리로 테스트 (기존 히스토리 백업)
        backup_history = conversation_history.copy()
        backup_turn_count = turn_count
        
        # 테스트를 위한 초기화
        conversation_history.clear()
        globals()['turn_count'] = 0
        
        # 테스트 실행
        result = run_turn(msg, simulate_response=False)
        
        print(f"결과 - 선택된 태스크: {result.get('selected_task')}")
        print(f"결과 - 태스크 관련성: {result.get('task_message_relevance', 0.0):.3f}")
        
        if result.get('selected_task') == 'Naming':
            print("✅ Naming 평가 성공적으로 트리거됨!")
            if result.get('generated_questions'):
                print(f"생성된 Naming 질문 수: {len(result.get('generated_questions'))}")
                print("생성된 질문들:")
                for j, q in enumerate(result.get('generated_questions', []), 1):
                    print(f"  {j}. {q}")
        else:
            print("❌ Naming 평가 트리거되지 않음")
        
        # 히스토리 복원
        conversation_history = backup_history
        globals()['turn_count'] = backup_turn_count
    
    print("\n=== Naming 평가 특별 테스트 완료 ===")
    print("Naming 평가 통합 테스트가 모두 완료되었습니다.")
