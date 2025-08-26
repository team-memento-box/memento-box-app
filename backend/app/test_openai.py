#!/usr/bin/env python3
"""
OpenAI API 연동 테스트 스크립트
"""

import asyncio
import os
from dotenv import load_dotenv
from services.openai_story import OpenAIService, ChatRequest, ChatMessage

# .env 파일 로드
load_dotenv()

async def test_openai_service():
    """OpenAI 서비스 테스트"""
    
    print("🧪 OpenAI API 연동 테스트 시작...")
    
    # API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY=your_api_key_here 를 추가해주세요.")
        return False
    
    print(f"✅ API 키 확인됨: {api_key[:10]}...")
    
    try:
        # OpenAI 서비스 초기화
        service = OpenAIService()
        print("✅ OpenAI 서비스 초기화 완료")
        
        # 1. 간단한 채팅 테스트
        print("\n📝 간단한 채팅 테스트...")
        response = await service.simple_chat("안녕하세요!")
        print(f"응답: {response}")
        
        # 2. Chat Completion 테스트
        print("\n🤖 Chat Completion 테스트...")
        messages = [
            ChatMessage(role="system", content="당신은 도움이 되는 AI 어시스턴트입니다."),
            ChatMessage(role="user", content="오늘 날씨에 대해 간단히 말해주세요.")
        ]
        
        request = ChatRequest(
            messages=messages,
            model="gpt-3.5-turbo",
            max_tokens=100,
            temperature=0.7
        )
        
        response = await service.chat_completion(request)
        print(f"응답: {response.response}")
        print(f"사용된 토큰: {response.usage}")
        print(f"모델: {response.model}")
        
        # 3. 스토리 생성 테스트
        print("\n📖 스토리 생성 테스트...")
        conversation_data = [
            {"question": "어떤 음식을 좋아하세요?", "answer": "김치찌개를 좋아해요"},
            {"question": "언제 주로 드시나요?", "answer": "추운 겨울날에 자주 먹어요"},
            {"question": "누구와 함께 드시나요?", "answer": "가족들과 함께 먹으면 더 맛있어요"}
        ]
        
        story = await service.generate_story(conversation_data)
        print(f"생성된 스토리:\n{story}")
        
        print("\n🎉 모든 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openai_service())
    if success:
        print("\n✅ OpenAI API 연동이 정상적으로 작동합니다.")
    else:
        print("\n❌ OpenAI API 연동에 문제가 있습니다.")