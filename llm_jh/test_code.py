# start_chat.py
import os
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

from feature_llm_16 import LangGraphDementiaChatbot, ChatbotConfig, ConversationState

def main():
    """
    사용자와 AI가 실시간으로 대화하는 메인 함수
    """
    # .env 파일에서 API 키를 로드합니다.
    load_dotenv()
    api_key = os.getenv("GPT_API_KEY")

    # 2. 챗봇 인스턴스를 생성합니다.
    config = ChatbotConfig(openai_api_key=api_key)
    chatbot = LangGraphDementiaChatbot(config)

    # 3. 대화의 전체 상태를 저장할 변수를 초기화합니다.
    #    코드가 사진 메타데이터를 기반으로 동작하므로, 가상의 데이터를 설정합니다.
    conversation_state = ConversationState(
        messages=[],
        current_message="",
        turn_counter=0,
        photo_metadata=
{
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
      "items": ["생일 모자 착용"]
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
  ]
},
        # 나머지 상태는 기본값으로 시작
        task_scores={}, selected_task="", task_message_relevance=0.0,
        generated_questions=[], selected_question="", question_message_relevance=0.0,
        conversation_mode="casual", ai_response="", response_type="",
        workflow_stage="", is_assessment_answer=False, last_assessment_question="",
        last_assessment_task="", assessment_score=0.0, score_details={},
        cached_question_found=False, cached_question_score=0.0,
        reused_question="", pending_recall_items=[], recall_scheduled_turn=-1,
        recall_question_type="", registration_phase="none"
    )

    # 4. 사용자가 '종료'를 입력할 때까지 무한 반복하는 대화 루프
    while True:
        try:
            # 사용자 입력 받기
            user_input = input("나 (User) > ")

            if user_input.lower() in ["종료", "exit", "quit"]:
                print("🤖 대화를 종료합니다. 이용해주셔서 감사합니다.")
                break
            
            # 입력받은 메시지로 대화 상태 업데이트
            conversation_state["current_message"] = user_input
            conversation_state["messages"].append(HumanMessage(content=user_input))

            # 5. LangGraph 체인 실행
            #    현재 대화 상태를 입력으로 넣어 AI의 다음 행동과 응답을 생성합니다.
            print("🤖 (생각 중...)")
            final_state = chatbot.graph.invoke(conversation_state)

            # AI의 응답 추출 및 출력
            ai_response = final_state.get("ai_response", "죄송해요, 응답을 생성하는 데 실패했어요.")
            print(f"AI > {ai_response}")

            # 6. 다음 턴을 위해 대화 상태를 최신으로 업데이트
            #    - AI의 응답을 메시지 기록에 추가
            #    - LangGraph가 변경한 모든 상태 값을 그대로 이어받음
            final_state["messages"].append(AIMessage(content=ai_response))
            conversation_state = final_state
        
        except KeyboardInterrupt:
            print("\n🤖 대화를 강제 종료합니다.")
            break
        except Exception as e:
            print(f"오류가 발생했습니다: {e}")
            break

if __name__ == "__main__":
    main()