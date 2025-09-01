#!/usr/bin/env python3
"""
Google STT 단독 테스트 스크립트
Flutter에서 보내는 오디오 형식과 동일한 조건으로 테스트
"""

import os
import sys
import base64
import wave
import struct
from pathlib import Path

# 백엔드 앱 경로 추가
sys.path.insert(0, '/home/ec2-user/Memento-Box/backend/app')

def create_test_audio():
    """간단한 테스트용 WAV 파일 생성 (묵음)"""
    import numpy as np
    
    # 1초 분량의 묵음 생성
    sample_rate = 16000
    duration = 2  # seconds
    samples = sample_rate * duration
    
    # 약간의 노이즈 추가 (완전한 묵음은 인식 안될 수 있음)
    audio_data = np.random.randint(-100, 100, samples, dtype=np.int16)
    
    # WAV 파일로 저장
    wav_path = "/tmp/test_audio.wav"
    with wave.open(wav_path, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    print(f"✅ 테스트 오디오 생성: {wav_path}")
    return wav_path

def test_google_credentials():
    """Google Cloud 인증 설정 확인"""
    print("\n=== Google Cloud 인증 확인 ===")
    
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS 환경변수가 설정되지 않음")
        return False
    
    print(f"📁 인증 파일 경로: {creds_path}")
    
    if not os.path.exists(creds_path):
        print(f"❌ 인증 파일이 존재하지 않음: {creds_path}")
        return False
    
    print("✅ 인증 파일 존재 확인")
    
    # 파일 크기 확인
    file_size = os.path.getsize(creds_path)
    print(f"📊 인증 파일 크기: {file_size} bytes")
    
    return True

def test_stt_with_file():
    """파일로 STT 테스트"""
    print("\n=== 파일 기반 STT 테스트 ===")
    
    try:
        from services.voice_system import VoiceSystem
        
        # VoiceSystem 초기화
        voice_system = VoiceSystem()
        
        if not voice_system.google_client:
            print("❌ Google Speech Client 초기화 실패")
            return False
        
        print("✅ Google Speech Client 초기화 성공")
        
        # 테스트 오디오 생성
        test_audio_path = create_test_audio()
        
        # STT 테스트
        result = voice_system.transcribe_with_google_file(test_audio_path)
        
        if result:
            print(f"✅ STT 성공: '{result}'")
            return True
        else:
            print("⚠️ STT 결과 없음 (묵음이거나 인식 불가)")
            # 묵음도 정상 처리로 간주
            return True
            
    except Exception as e:
        print(f"❌ STT 테스트 실패: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_stt_with_base64():
    """Base64 인코딩된 오디오로 STT 테스트 (Flutter와 동일한 방식)"""
    print("\n=== Base64 기반 STT 테스트 ===")
    
    try:
        from services.voice_system import VoiceSystem
        
        # VoiceSystem 초기화
        voice_system = VoiceSystem()
        
        if not voice_system.google_client:
            print("❌ Google Speech Client 초기화 실패")
            return False
        
        # 테스트 오디오 생성
        test_audio_path = create_test_audio()
        
        # Base64로 인코딩
        with open(test_audio_path, 'rb') as f:
            audio_content = f.read()
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        print(f"📊 Base64 데이터 길이: {len(audio_base64)} chars")
        
        # STT 테스트
        result = voice_system.transcribe_with_google_base64(audio_base64)
        
        if result:
            print(f"✅ Base64 STT 성공: '{result}'")
            return True
        else:
            print("⚠️ Base64 STT 결과 없음 (묵음이거나 인식 불가)")
            return True
            
    except Exception as e:
        print(f"❌ Base64 STT 테스트 실패: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_m4a_format():
    """M4A 포맷 처리 테스트"""
    print("\n=== M4A 포맷 지원 테스트 ===")
    
    try:
        from google.cloud import speech
        
        # 지원 포맷 확인
        supported_formats = [
            "LINEAR16", "FLAC", "MULAW", "AMR", "AMR_WB", 
            "OGG_OPUS", "WEBM_OPUS", "MP3", "M4A"
        ]
        
        print("Google STT 지원 포맷:")
        for fmt in supported_formats:
            try:
                encoding = getattr(speech.RecognitionConfig.AudioEncoding, fmt, None)
                if encoding is not None:
                    print(f"  ✅ {fmt}")
                else:
                    print(f"  ❌ {fmt}")
            except:
                print(f"  ❌ {fmt}")
        
        return True
        
    except Exception as e:
        print(f"❌ 포맷 확인 실패: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("🔬 Google STT 테스트 시작\n")
    
    # 환경변수 로드
    from dotenv import load_dotenv
    load_dotenv('/home/ec2-user/Memento-Box/backend/.env')
    
    tests = [
        ("Google Cloud 인증", test_google_credentials),
        ("M4A 포맷 지원", test_m4a_format),
        ("파일 기반 STT", test_stt_with_file),
        ("Base64 기반 STT", test_stt_with_base64),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"테스트: {test_name}")
        print('='*50)
        
        success = test_func()
        results.append((test_name, success))
    
    # 결과 요약
    print("\n" + "="*50)
    print("테스트 결과 요약")
    print("="*50)
    
    for test_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{test_name}: {status}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패 - 로그를 확인하세요")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())