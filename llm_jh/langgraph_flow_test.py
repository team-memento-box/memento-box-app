"""15번 파일 테스트"""
# 1. 챗봇 초기화
chatbot = LangGraphDementiaChatbot(config)

# 2. 초기 대화 상태 정의
initial_state = {
    "messages": [],
    "current_message": "안녕하세요! 오늘 기분이 어떠세요?",
    "task_scores": {},
    "selected_task": "",
    "task_message_relevance": 0.0,
    "generated_questions": [],
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
    "reused_question": "",
    "photo_metadata": {
        "objects": [{"name": "강아지", "relation": {"on_top": "바닥"}}],
        "people": [{"name": "할머니", "items": ["모자", "가방"]}]
    },
    "turn_counter": 0,
    "pending_recall_items": [],
    "recall_scheduled_turn": -1,
    "recall_question_type": "",
    "registration_phase": "none"
}

# 3. 새 메시지를 처리
state_after_turn = chatbot.graph.run(initial_state)

# 4. AI 응답 확인
print("AI Response:", state_after_turn["ai_response"])
print("Response Type:", state_after_turn["response_type"])

