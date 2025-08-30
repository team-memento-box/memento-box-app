#!/usr/bin/env python3
"""
Audio Fetch API 테스트 스크립트
DB에서 오디오 파일 가져오기 기능 테스트
"""

import requests
import json
from typing import Dict, Any

# API 기본 URL (개발 환경)
BASE_URL = "http://localhost:8000/api"

def test_audio_analysis_health():
    """Audio Analysis API 헬스 체크"""
    print("🔍 Audio Analysis API 헬스 체크...")
    
    try:
        response = requests.get(f"{BASE_URL}/audio-analysis/health")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API가 정상 작동 중입니다!")
            print(f"Response: {response.json()}")
        else:
            print("❌ API 응답 오류")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")

def test_get_session_audio_files(session_id: str):
    """세션 오디오 파일 조회 테스트"""
    print(f"\n🔍 세션 오디오 파일 조회 테스트: {session_id}")
    
    try:
        # GET 방식 테스트
        response = requests.get(f"{BASE_URL}/audio-analysis/session/{session_id}/audio-files")
        print(f"GET Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ GET 요청 성공!")
            print(f"Session ID: {data['session_id']}")
            print(f"전체 대화 수: {data['total_conversations']}")
            print(f"오디오 파일 수: {data['audio_files_count']}")
            
            # 오디오 파일이 있는 대화들만 출력
            audio_conversations = [af for af in data['audio_files'] if af['user_response_audio_url']]
            
            if audio_conversations:
                print("\n📁 오디오 파일이 있는 대화들:")
                for audio_file in audio_conversations:
                    print(f"  - 대화 #{audio_file['conversation_order']}: {audio_file['question_text'][:50]}...")
                    print(f"    오디오 URL: {audio_file['user_response_audio_url']}")
            else:
                print("⚠️ 이 세션에는 오디오 파일이 없습니다.")
                
        elif response.status_code == 404:
            print("❌ 세션을 찾을 수 없습니다.")
            print(f"Error: {response.json()}")
        else:
            print("❌ API 응답 오류")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ API 서버에 연결할 수 없습니다.")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")

def test_get_session_audio_urls_only(session_id: str):
    """세션 오디오 URL만 조회 테스트 (음성 분석 모듈용)"""
    print(f"\n🔍 세션 오디오 URL 간단 조회 테스트: {session_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/audio-analysis/session/{session_id}/audio-urls-only")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 음성 분석용 URL 조회 성공!")
            print(f"Session ID: {data['session_id']}")
            print(f"오디오 파일 수: {data['audio_files_count']}")
            
            print("\n🎵 오디오 URL 목록:")
            for audio in data['audio_urls']:
                print(f"  - 대화 #{audio['conversation_order']}: {audio['audio_url']}")
                
        elif response.status_code == 404:
            print("❌ 세션에 오디오 파일이 없습니다.")
            print(f"Error: {response.json()}")
        else:
            print("❌ API 응답 오류")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ API 서버에 연결할 수 없습니다.")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")

def test_post_session_audio_files(session_id: str):
    """POST 방식으로 세션 오디오 파일 조회 테스트"""
    print(f"\n🔍 POST 방식 세션 오디오 파일 조회 테스트: {session_id}")
    
    try:
        # POST 요청 데이터
        payload = {"session_id": session_id}
        
        response = requests.post(
            f"{BASE_URL}/audio-analysis/session/audio-files",
            json=payload
        )
        print(f"POST Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ POST 요청 성공!")
            print(f"Session ID: {data['session_id']}")
            print(f"전체 대화 수: {data['total_conversations']}")
            print(f"오디오 파일 수: {data['audio_files_count']}")
        else:
            print("❌ POST 요청 실패")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ API 서버에 연결할 수 없습니다.")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🎵 Audio Fetch API 테스트 시작")
    print("=" * 60)
    
    # 1. 헬스 체크
    test_audio_analysis_health()
    
    # 2. 테스트용 세션 ID (실제 데이터베이스에 있는 세션 ID로 교체 필요)
    test_session_id = "123e4567-e89b-12d3-a456-426614174000"  # 예시 UUID
    
    print(f"\n📝 테스트 세션 ID: {test_session_id}")
    print("⚠️ 실제 테스트를 위해서는 데이터베이스에 존재하는 세션 ID로 교체하세요.")
    
    # 3. 세션 오디오 파일 조회 테스트
    test_get_session_audio_files(test_session_id)
    
    # 4. 세션 오디오 URL만 조회 테스트  
    test_get_session_audio_urls_only(test_session_id)
    
    # 5. POST 방식 테스트
    test_post_session_audio_files(test_session_id)
    
    print("\n" + "=" * 60)
    print("🎵 테스트 완료!")
    print("=" * 60)
    
    print("\n📋 다음 단계:")
    print("1. FastAPI 서버를 실행하세요: cd backend/app && python main.py")
    print("2. 실제 세션 ID로 테스트하세요")
    print("3. Supabase에서 conversations 테이블의 실제 데이터 확인")
    print("4. 오디오 URL이 유효한지 확인")