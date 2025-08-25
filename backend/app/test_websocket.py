#!/usr/bin/env python3
"""
WebSocket 테스트 스크립트
로컬에서 대화 워크플로우 테스트
"""
import asyncio
import websockets
import json
import uuid

async def test_websocket_chat():
    """WebSocket 대화 테스트"""
    conversation_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/ws/chat/{conversation_id}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ WebSocket 연결 성공: {conversation_id}")
            
            # 테스트 메시지들
            test_messages = [
                {
                    "user_id": "test_user_001",
                    "message": "안녕하세요! 이 사진을 보고 있어요.",
                    "photo_context": {
                        "description": "가족 사진",
                        "location": "집 앞마당"
                    }
                },
                {
                    "user_id": "test_user_001", 
                    "message": "네, 이 사진은 작년 여름에 찍었어요.",
                    "photo_context": {}
                },
                {
                    "user_id": "test_user_001",
                    "message": "잘 기억이 안 나네요... 언제였지?",
                    "photo_context": {}
                }
            ]
            
            for i, test_msg in enumerate(test_messages, 1):
                print(f"\n📤 메시지 {i} 전송: {test_msg['message']}")
                await websocket.send(json.dumps(test_msg))
                
                # 응답 대기
                response = await websocket.recv()
                response_data = json.loads(response)
                
                print(f"📥 응답 받음:")
                print(f"   타입: {response_data.get('type')}")
                print(f"   내용: {response_data.get('data', {}).get('response_text', '')}")
                
                # 잠깐 대기
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"❌ WebSocket 테스트 실패: {e}")

def run_test():
    """테스트 실행"""
    print("🧪 WebSocket 대화 워크플로우 테스트 시작")
    print("=" * 50)
    asyncio.run(test_websocket_chat())
    print("=" * 50)
    print("✅ 테스트 완료")

if __name__ == "__main__":
    run_test()