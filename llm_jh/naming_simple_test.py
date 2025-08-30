"""
Naming 평가 간단 테스트
"""

import os
from dotenv import load_dotenv
from feature_llm_13 import LangGraphDementiaChatbot, ChatbotConfig

load_dotenv()
API_KEY = os.getenv("GPT_API_KEY")

config = ChatbotConfig(openai_api_key=API_KEY)
bot = LangGraphDementiaChatbot(config)

# 생일파티 사진 메타데이터 (img_description.py 형식)
photo_metadata = {
    "objects": [
        {
            "name": "생일 케이크",
            "location": "테이블 중앙",
            "relation": {
                "on_top": ["초 5개"],
                "nearby": ["선물 상자", "접시"]
            }
        },
        {
            "name": "파티 모자",
            "location": "아이 머리",
            "relation": {"worn_by": ["생일 주인공"]}
        }
    ],
    "people": [
        {
            "role": "어린이 (생일 주인공)",
            "items": ["생일 모자"]
        }
    ],
    "year": 2003
}

def test_naming_simple():
    print("=== Naming 평가 간단 테스트 ===\n")
    
    # 1. 객체 추출 테스트
    naming_objects = bot._extract_naming_objects_from_photo(photo_metadata)
    print(f"1. 추출된 naming 객체들: {naming_objects}")
    
    # 2. Naming 질문 생성 테스트
    questions = bot._generate_naming_questions_from_photo(photo_metadata, [], "케이크가 보이네요")
    print(f"\n2. 생성된 Naming 질문들:")
    for i, q in enumerate(questions, 1):
        print(f"   {i}. {q}")
    
    # 3. 실제 대화 테스트
    print(f"\n3. 실제 대화 테스트:")
    
    test_messages = [
        "사진에 케이크가 보이네요!",
        "초가 몇 개인지 궁금해요",
        "아이가 머리에 뭘 쓰고 있나요?"
    ]
    
    for msg in test_messages:
        print(f"\n--- 테스트 메시지: '{msg}' ---")
        
        result = bot.chat_with_history(msg, [], photo_metadata)
        
        print(f"선택된 태스크: {result.get('selected_task')}")
        print(f"태스크 관련성: {result.get('task_message_relevance', 0.0):.3f}")
        print(f"AI 응답: {result.get('ai_response')}")
        
        if result.get('selected_task') == 'Naming':
            print("✅ Naming 평가 성공!")
        else:
            print("❌ Naming 평가 실패")
        print("-" * 50)

if __name__ == "__main__":
    test_naming_simple()