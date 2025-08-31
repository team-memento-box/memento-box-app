#!/usr/bin/env python3
"""
수동 세션 및 대화 저장 테스트
환경변수 없이 직접 Supabase 클라이언트 생성하여 테스트
"""

import sys
import os
import uuid
from supabase import create_client, Client

def test_with_credentials():
    """환경변수를 수동으로 입력받아 테스트"""
    print("🔧 Supabase 테스트를 위한 정보 입력")
    print("(이 정보는 저장되지 않고 테스트에만 사용됩니다)\n")
    
    supabase_url = input("SUPABASE_URL: ").strip()
    service_role_key = input("SUPABASE_SERVICE_ROLE_KEY: ").strip()
    
    if not supabase_url or not service_role_key:
        print("❌ URL과 서비스 역할 키가 모두 필요합니다.")
        return False
    
    try:
        # Supabase 서비스 역할 클라이언트 생성
        supabase_admin: Client = create_client(supabase_url, service_role_key)
        print("✅ Supabase 클라이언트 생성 성공!")
        
        # 간단한 연결 테스트
        result = supabase_admin.table("sessions").select("*").limit(1).execute()
        print(f"✅ Supabase 연결 성공! (기존 세션 수: {len(result.data)})")
        
        # 테스트 세션 생성
        test_session_id = str(uuid.uuid4())
        test_user_id = str(uuid.uuid4())  # 실제 사용자 ID를 시뮬레이션
        
        print(f"\n📝 테스트 세션 생성...")
        session_data = {
            "id": test_session_id,
            "user_id": test_user_id,
            "session_type": "reminiscence",
            "status": "active"
        }
        
        session_result = supabase_admin.table("sessions").insert(session_data).execute()
        
        if session_result.data:
            print(f"✅ 세션 생성 성공: {test_session_id}")
            
            # 테스트 대화 생성
            print(f"💬 테스트 대화 생성...")
            conversation_data = {
                "session_id": test_session_id,
                "user_id": test_user_id,
                "conversation_order": 1,
                "ai_output": "안녕하세요! 이 사진에 대해 이야기해볼까요?",
                "question_type": "open_ended",
                "user_input": "네, 좋습니다!",
                "is_cist_item": False
            }
            
            conv_result = supabase_admin.table("conversations").insert(conversation_data).execute()
            
            if conv_result.data:
                print(f"✅ 대화 생성 성공: {conv_result.data[0]['id']}")
                
                # 생성된 데이터 조회 확인
                query_sessions = supabase_admin.table("sessions").select("*").eq("id", test_session_id).execute()
                query_conversations = supabase_admin.table("conversations").select("*").eq("session_id", test_session_id).execute()
                
                print(f"\n📊 생성된 데이터 확인:")
                print(f"  세션: {len(query_sessions.data)}개")
                print(f"  대화: {len(query_conversations.data)}개")
                
                # 테스트 데이터 정리
                print(f"\n🗑️  테스트 데이터 정리...")
                supabase_admin.table("conversations").delete().eq("session_id", test_session_id).execute()
                supabase_admin.table("sessions").delete().eq("id", test_session_id).execute()
                print(f"✅ 정리 완료")
                
                return True
            else:
                print(f"❌ 대화 생성 실패")
                # 세션만 정리
                supabase_admin.table("sessions").delete().eq("id", test_session_id).execute()
                return False
        else:
            print(f"❌ 세션 생성 실패")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(f"📋 상세 오류:\n{traceback.format_exc()}")
        return False

def show_implementation_summary():
    """구현 내용 요약 출력"""
    print("=" * 60)
    print("🎯 구현 완료된 기능들")
    print("=" * 60)
    print()
    
    print("✅ 1. JWT 인증 통합")
    print("   - main.py에서 Supabase JWT 토큰 검증")
    print("   - 인증된 사용자 정보로 세션 생성")
    print()
    
    print("✅ 2. 통합된 세션 생성")
    print("   - WebSocket 첫 연결 시 세션 생성")
    print("   - conversation_id = session_id 매핑")
    print("   - 중복 세션 생성 로직 제거")
    print()
    
    print("✅ 3. 서비스 역할 클라이언트 사용")
    print("   - main.py에서 서비스 역할 키로 DB 접근")
    print("   - dialogue_workflow.py에 인증된 클라이언트 전달")
    print("   - RLS 정책 우회하여 안전한 DB 조작")
    print()
    
    print("✅ 4. 대화 저장 로직 개선")
    print("   - 인증된 클라이언트로 conversations 테이블 저장")
    print("   - 적절한 외래 키 관계 보장")
    print("   - conversation_order 자동 계산")
    print()
    
    print("✅ 5. 상세한 로깅 및 에러 처리")
    print("   - 각 단계별 디버깅 정보 출력")
    print("   - 구체적인 오류 메시지")
    print("   - 예외 상황 처리")
    print()
    
    print("🎯 다음 테스트 단계:")
    print("1. FastAPI 서버 실행: uvicorn app.main:app --reload")
    print("2. Flutter 앱에서 '대화하기' 버튼 테스트")
    print("3. WebSocket 로그 확인")
    print("4. Supabase 대시보드에서 데이터 확인")

if __name__ == "__main__":
    print("🚀 Memento Box - 세션 및 대화 저장 테스트\n")
    
    # 구현 내용 요약 표시
    show_implementation_summary()
    print("\n" + "=" * 60)
    
    print("\n🧪 실제 Supabase 연결을 테스트하시겠습니까? (y/n): ", end="")
    choice = input().lower().strip()
    
    if choice == 'y':
        print()
        success = test_with_credentials()
        if success:
            print(f"\n🎉 테스트 성공! 이제 실제 앱에서 테스트해보세요.")
        else:
            print(f"\n❌ 테스트 실패. 환경 설정을 확인해주세요.")
    else:
        print(f"\n📋 테스트를 건너뜁니다. 구현은 완료되었습니다!")
    
    print(f"\n💡 문제가 발생하면 다음을 확인해주세요:")
    print(f"   1. .env 파일의 SUPABASE_SERVICE_ROLE_KEY 설정")
    print(f"   2. Supabase 프로젝트의 RLS 정책")
    print(f"   3. FastAPI 서버 로그 확인")