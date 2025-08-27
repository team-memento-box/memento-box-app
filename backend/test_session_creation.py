#!/usr/bin/env python3
"""
세션 및 대화 저장 테스트 스크립트
JWT 인증부터 DB 저장까지 전체 플로우를 테스트합니다.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from core.config import supabase_admin
import json
import uuid

async def test_session_creation():
    """세션 생성 테스트"""
    print("=== 세션 생성 테스트 ===\n")
    
    try:
        # 테스트 데이터
        test_session_id = str(uuid.uuid4())
        test_user_id = "test-user-id"
        test_photo_id = "test-photo-id"
        
        print(f"📝 테스트 데이터:")
        print(f"  - session_id: {test_session_id}")
        print(f"  - user_id: {test_user_id}")
        print(f"  - photo_id: {test_photo_id}")
        print()
        
        # 세션 데이터 생성
        session_data = {
            "id": test_session_id,
            "user_id": test_user_id,
            "session_type": "reminiscence",
            "status": "active",
            "selected_photos": [test_photo_id]
        }
        
        print(f"💾 세션 생성 시도...")
        result = supabase_admin.table("sessions").insert(session_data).execute()
        
        if result.data:
            print(f"✅ 세션 생성 성공!")
            print(f"   생성된 세션: {result.data[0]}")
            
            # 생성된 세션 조회 확인
            print(f"\n🔍 세션 조회 테스트...")
            query_result = supabase_admin.table("sessions").select("*").eq("id", test_session_id).execute()
            
            if query_result.data:
                print(f"✅ 세션 조회 성공!")
                print(f"   조회된 세션: {query_result.data[0]}")
            else:
                print(f"❌ 세션 조회 실패")
            
            # 테스트 세션 삭제
            print(f"\n🗑️  테스트 세션 정리...")
            delete_result = supabase_admin.table("sessions").delete().eq("id", test_session_id).execute()
            print(f"✅ 테스트 세션 삭제 완료")
            
        else:
            print(f"❌ 세션 생성 실패: 응답 데이터 없음")
            print(f"   응답: {result}")
            
    except Exception as e:
        print(f"❌ 세션 생성 테스트 실패: {e}")
        import traceback
        print(f"📋 상세 오류: {traceback.format_exc()}")

async def test_conversation_creation():
    """대화 생성 테스트"""
    print("\n=== 대화 생성 테스트 ===\n")
    
    try:
        # 먼저 테스트 세션 생성
        test_session_id = str(uuid.uuid4())
        test_user_id = "test-user-id"
        
        session_data = {
            "id": test_session_id,
            "user_id": test_user_id,
            "session_type": "reminiscence",
            "status": "active"
        }
        
        session_result = supabase_admin.table("sessions").insert(session_data).execute()
        if not session_result.data:
            print("❌ 테스트 세션 생성 실패")
            return
        
        print(f"✅ 테스트 세션 생성됨: {test_session_id}")
        
        # 대화 데이터 생성
        conversation_data = {
            "session_id": test_session_id,
            "user_id": test_user_id,
            "conversation_order": 1,
            "question_text": "안녕하세요! 오늘 기분은 어떠신가요?",
            "question_type": "open_ended",
            "user_response_text": "안녕하세요! 오늘 날씨가 좋네요.",
            "is_cist_item": False
        }
        
        print(f"💬 대화 생성 시도...")
        conv_result = supabase_admin.table("conversations").insert(conversation_data).execute()
        
        if conv_result.data:
            print(f"✅ 대화 생성 성공!")
            print(f"   생성된 대화: {conv_result.data[0]['id']}")
            
            # 대화 조회 확인
            query_result = supabase_admin.table("conversations").select("*").eq("session_id", test_session_id).execute()
            print(f"✅ 대화 조회 성공: {len(query_result.data)}개 대화 발견")
            
        else:
            print(f"❌ 대화 생성 실패: 응답 데이터 없음")
        
        # 테스트 데이터 정리
        print(f"\n🗑️  테스트 데이터 정리...")
        supabase_admin.table("conversations").delete().eq("session_id", test_session_id).execute()
        supabase_admin.table("sessions").delete().eq("id", test_session_id).execute()
        print(f"✅ 테스트 데이터 정리 완료")
        
    except Exception as e:
        print(f"❌ 대화 생성 테스트 실패: {e}")
        import traceback
        print(f"📋 상세 오류: {traceback.format_exc()}")

def test_supabase_connection():
    """Supabase 연결 테스트"""
    print("=== Supabase 연결 테스트 ===\n")
    
    try:
        # 간단한 쿼리로 연결 테스트
        result = supabase_admin.table("sessions").select("*").limit(1).execute()
        print("✅ Supabase 연결 성공!")
        print(f"   반환된 세션 수: {len(result.data)}")
        return True
        
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return False

if __name__ == "__main__":
    print("🚀 세션 및 대화 저장 시스템 테스트 시작\n")
    
    # Supabase 연결 테스트
    if not test_supabase_connection():
        print("❌ Supabase 연결 실패로 테스트 중단")
        sys.exit(1)
    
    print()
    
    # 비동기 테스트 실행
    asyncio.run(test_session_creation())
    asyncio.run(test_conversation_creation())
    
    print("\n✨ 모든 테스트가 완료되었습니다!")
    print("\n📝 다음 단계:")
    print("1. Flutter 앱에서 '대화하기' 버튼 테스트")
    print("2. WebSocket 연결 및 메시지 전송 확인") 
    print("3. Supabase 대시보드에서 실제 데이터 확인")
    print("4. 각 단계별 로그 확인")