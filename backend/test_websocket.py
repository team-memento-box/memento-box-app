#!/usr/bin/env python3
"""
WebSocket 연결 테스트 스크립트
FastAPI 백엔드의 WebSocket 엔드포인트를 테스트합니다.
"""

import asyncio
import json
import websockets
from datetime import datetime
import uuid

async def test_websocket_connection():
    """WebSocket 연결 및 메시지 송수신 테스트"""
    
    # 임시 대화 ID 생성
    conversation_id = str(uuid.uuid4())
    
    # WebSocket URL
    websocket_url = f"ws://localhost:8000/ws/chat/{conversation_id}"
    
    print(f"🔗 WebSocket 연결 테스트 시작")
    print(f"📍 URL: {websocket_url}")
    print(f"🆔 대화 ID: {conversation_id}")
    print("-" * 50)
    
    try:
        # WebSocket 연결
        async with websockets.connect(websocket_url) as websocket:
            print("✅ WebSocket 연결 성공!")
            
            # 테스트 메시지들
            test_messages = [
                "안녕하세요! 테스트 메시지입니다.",
                "이 사진에 대해 설명해 주세요.",
                "감사합니다."
            ]
            
            for i, message in enumerate(test_messages, 1):
                print(f"\n📤 메시지 {i} 전송: {message}")
                
                # 메시지 구성
                message_data = {
                    "user_id": "test_user_001",
                    "message": message,
                    "photo_context": {
                        "photo_id": "test-photo-id",
                        "photo_url": "https://example.com/photo.jpg",
                        "description": "테스트 사진입니다."
                    }
                }
                
                # 메시지 전송
                await websocket.send(json.dumps(message_data))
                
                # 응답 대기 (처리 메시지 + 최종 응답)
                response_count = 0
                while response_count < 2:  # processing + response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        response_data = json.loads(response)
                        
                        message_type = response_data.get("type", "unknown")
                        
                        if message_type == "processing":
                            print(f"⏳ 처리 중: {response_data.get('message', '')}")
                        elif message_type == "response":
                            ai_response = response_data.get("data", {}).get("response_text", "")
                            print(f"📥 AI 응답: {ai_response}")
                            break
                        elif message_type == "error":
                            print(f"❌ 오류: {response_data.get('message', '')}")
                            break
                        
                        response_count += 1
                        
                    except asyncio.TimeoutError:
                        print("⏰ 응답 타임아웃")
                        break
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON 파싱 오류: {e}")
                        break
                
                # 잠시 대기
                await asyncio.sleep(1)
            
            print("\n✅ 모든 테스트 메시지 완료!")
            
    except ConnectionRefusedError:
        print("❌ 서버에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인해주세요.")
        print("💡 서버 시작: uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")

async def test_health_check():
    """헬스체크 엔드포인트 테스트"""
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print("🏥 헬스체크 결과:")
                    print(f"  - 상태: {data.get('status')}")
                    print(f"  - OpenAI 설정: {'✅' if data.get('openai_configured') else '❌'}")
                    print(f"  - Supabase 설정: {'✅' if data.get('supabase_configured') else '❌'}")
                    print(f"  - 시간: {data.get('timestamp')}")
                    return True
                else:
                    print(f"❌ 헬스체크 실패 (상태 코드: {response.status})")
                    return False
    except ImportError:
        print("⚠️  aiohttp가 설치되지 않아 헬스체크를 건너뜁니다.")
        print("💡 설치: pip install aiohttp")
        return True
    except Exception as e:
        print(f"❌ 헬스체크 오류: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("🚀 Memento Box AI API WebSocket 테스트")
    print("=" * 50)
    
    # 헬스체크 먼저 실행
    health_ok = await test_health_check()
    
    if health_ok:
        print("\n")
        await test_websocket_connection()
    else:
        print("⚠️  헬스체크 실패로 인해 WebSocket 테스트를 건너뜁니다.")
    
    print("\n🏁 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())