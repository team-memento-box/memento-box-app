import asyncio
from dialogue_workflow import DialogueWorkflow
import sys
import os
import uuid

sys.path.append('/app')

class InteractiveTest:
    def __init__(self):
        self.wf = DialogueWorkflow()
        
        # 고정된 세션 정보 (테스트용) - UUID 형식으로 변경
        self.conversation_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())
        self.turn_count = 0
        
        # 메모리에서 대화 히스토리 유지 (DB 저장 실패 대비)
        self.conversation_history = []
        
        # 고정된 사진 컨텍스트 - photo_id도 UUID 형식으로 변경
        self.photo_context = {
            "photo_id": str(uuid.uuid4()),
            "description": "사진 속에는 어린 소년이 해변에서 모래성을 쌓고 있습니다. 햇살이 따사롭게 내리쬐며, 소년의 얼굴에는 밝은 미소가 가득합니다. 파도 소리가 배경에서 잔잔히 들리고, 바람에 흩날리는 모래와 소년의 모자, 주변에 놓인 삽과 양동이가 장면을 더욱 생생하게 만듭니다.",
            "tags": ["강아지", "잔디밭", "여름"],
            "location_name": "고향집 마당",
            "naming_objects": [
                {"item": "모래성", "location": "소년 앞 바닥에", "context": "놀이 중심 아이템"},
                {"item": "삽", "location": "손에 들고 있음", "context": "모래성을 쌓는 도구"},
                {"item": "양동이", "location": "모래성 옆", "context": "모래를 담는 도구"},
                {"item": "모자", "location": "머리에 쓰고 있음", "context": "햇볕을 막기 위한 소품"}
            ],
            "photo_year": 2000
        }
    
    def print_status(self):
        """현재 테스트 상태 출력"""
        print(f"\n{'='*50}")
        print(f"🎮 테스트 세션 정보:")
        print(f"   - 대화 ID: {self.conversation_id}")
        print(f"   - 사용자 ID: {self.user_id}")
        print(f"   - 현재 턴: {self.turn_count}")
        print(f"   - 사진 ID: {self.photo_context['photo_id']}")
        
        # CIST 결과 상태 (있다면)
        if hasattr(self.wf, 'cist_results') and self.wf.cist_results:
            print(f"   - CIST 결과: {len(self.wf.cist_results)}개")
            for i, result in enumerate(self.wf.cist_results, 1):
                print(f"     {i}. {result['cist_category']}: {result['expected_answer']}")
        
        print(f"{'='*50}\n")
    
    async def send_message(self, user_message):
        """메시지 전송 및 응답 받기"""
        self.turn_count += 1
        
        print(f"\n🚀 [{self.turn_count}턴] 메시지 전송 중...")
        print(f"📝 사용자: {user_message}")
        
        # 입력 데이터 구성
        input_data = {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "user_message": user_message,
            "photo_context": self.photo_context
        }
        
        try:
            # 메모리 히스토리를 WorkflowInput에 추가
            input_data["conversation_history"] = self.conversation_history
            
            # 워크플로우 실행 (인증된 클라이언트 전달)
            output = await self.wf.process_message(input_data, self.wf.supabase)
            ai_response = output["response_text"]
            
            print(f"🤖 AI: {ai_response}")
            
            # 메모리 히스토리에 대화 추가
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            self.conversation_history.append({
                "role": "assistant", 
                "content": ai_response
            })
            
            return ai_response
            
        except Exception as e:
            error_msg = f"❌ 오류 발생: {e}"
            print(error_msg)
            return error_msg
    
    async def run_interactive(self):
        """인터랙티브 테스트 실행"""
        print("🎮 LangGraph DialogueWorkflow 인터랙티브 테스트")
        print("=" * 60)
        print("💡 사용법:")
        print("  - 메시지 입력: 일반 텍스트")
        print("  - /status: 현재 상태 보기")
        print("  - /reset: 세션 재시작")
        print("  - /quit: 종료")
        print("  - Ctrl+C: 강제 종료")
        
        self.print_status()
        
        while True:
            try:
                # 사용자 입력 받기
                user_input = input(f"[{self.turn_count + 1}턴] 입력 > ").strip()
                
                if not user_input:
                    continue
                
                # 명령어 처리
                if user_input.startswith('/'):
                    if user_input == '/quit':
                        print("👋 테스트를 종료합니다.")
                        break
                    elif user_input == '/status':
                        self.print_status()
                        continue
                    elif user_input == '/reset':
                        # 세션 재시작
                        self.conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
                        self.turn_count = 0
                        # CIST 결과 초기화
                        if hasattr(self.wf, 'cist_results'):
                            self.wf.cist_results = []
                        print(f"🔄 새 세션으로 재시작: {self.conversation_id}")
                        continue
                    else:
                        print(f"❓ 알 수 없는 명령어: {user_input}")
                        continue
                
                # 일반 메시지 처리
                await self.send_message(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 Ctrl+C로 테스트를 종료합니다.")
                break
            except EOFError:
                print("\n\n👋 입력 스트림이 종료되었습니다.")
                break
            except Exception as e:
                print(f"❌ 예상치 못한 오류: {e}")
                continue

async def test_workflow():
    """기존 테스트 함수 (한 번만 실행)"""
    wf = DialogueWorkflow()

    input_data = {
        "conversation_id": "conv_12345",
        "user_id": "user_001", 
        "user_message": "안녕하세요, 사진 속 강아지가 귀엽네요!",
        "photo_context": {
            "photo_id": "photo_001",
            "description": "사진 속에는 어린 소년이 해변에서 모래성을 쌓고 있습니다. 햇살이 따사롭게 내리쬐며, 소년의 얼굴에는 밝은 미소가 가득합니다. 파도 소리가 배경에서 잔잔히 들리고, 바람에 흩날리는 모래와 소년의 모자, 주변에 놓인 삽과 양동이가 장면을 더욱 생생하게 만듭니다.",
            "tags": ["강아지", "잔디밭", "여름"],
            "location_name": "고향집 마당",
            "naming_objects": [
                {"item": "모래성", "location": "소년 앞 바닥에", "context": "놀이 중심 아이템"},
                {"item": "삽", "location": "손에 들고 있음", "context": "모래성을 쌓는 도구"},
                {"item": "양동이", "location": "모래성 옆", "context": "모래를 담는 도구"},
                {"item": "모자", "location": "머리에 쓰고 있음", "context": "햇볕을 막기 위한 소품"}
            ],
            "photo_year": 2000
        }
    }

    output = await wf.process_message(input_data)
    print("💬 최종 응답:", output["response_text"])

async def main():
    """메인 함수 - 모드 선택"""
    print("🚀 DialogueWorkflow 테스트")
    print("1. 단일 테스트 (기존 방식)")
    print("2. 인터랙티브 테스트 (실시간 대화)")
    
    while True:
        try:
            choice = input("선택 (1 또는 2, 또는 q로 종료): ").strip()
            
            if choice == 'q':
                print("👋 종료합니다.")
                return
            elif choice == '1':
                print("\n📋 단일 테스트 실행...")
                await test_workflow()
                break
            elif choice == '2':
                print("\n🎮 인터랙티브 테스트 시작...")
                test_runner = InteractiveTest()
                await test_runner.run_interactive()
                break
            else:
                print("❌ 1 또는 2를 입력하세요.")
                
        except KeyboardInterrupt:
            print("\n👋 종료합니다.")
            break

# 실행
if __name__ == "__main__":
    asyncio.run(main())