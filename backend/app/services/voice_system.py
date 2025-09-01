import os
import base64
from google.cloud import speech
from google.oauth2 import service_account

from core.config import settings

AUDIO_DIR = "audio_files"

class VoiceSystem:
    """Google STT 음성 인식 시스템"""
    
    def __init__(self):
        # Google Cloud Speech 설정
        self.google_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.google_client = None
        
        if self.google_credentials_path and os.path.exists(self.google_credentials_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    self.google_credentials_path
                )
                self.google_client = speech.SpeechClient(credentials=credentials)
                print("✅ Google Speech Client 초기화 성공")
            except Exception as e:
                print(f"❌ Google Speech Client 초기화 실패: {e}")
        else:
            print("⚠️ Google Cloud 인증 설정이 없음 - 환경변수 GOOGLE_APPLICATION_CREDENTIALS 확인 필요")
    
    def transcribe_with_google_base64(self, audio_base64: str) -> str:
        """Google STT: base64 인코딩된 오디오를 텍스트로 변환"""
        if not self.google_client:
            print("❌ Google Speech Client가 초기화되지 않음")
            return ""
        
        try:
            print(f"🎤 Google STT 처리 시작: 데이터 길이 {len(audio_base64)} chars")
            
            # base64 디코딩
            audio_content = base64.b64decode(audio_base64)
            
            # Google Speech API 요청 설정 - 여러 포맷 시도
            audio = speech.RecognitionAudio(content=audio_content)
            
            # 첫 번째 시도: M4A 포맷 (Flutter가 실제로 생성하는 포맷)
            try:
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.M4A,  # M4A 포맷 (AAC 컨테이너)
                    sample_rate_hertz=16000,
                    language_code="ko-KR",
                    alternative_language_codes=["en-US"],
                    enable_automatic_punctuation=True,
                    use_enhanced=True,
                    model="latest_long",
                )
                print("🎤 M4A 포맷으로 STT 시도")
                response = self.google_client.recognize(config=config, audio=audio)
            except Exception as e:
                print(f"⚠️ AAC 포맷 실패, WEBM_OPUS로 재시도: {e}")
                # 두 번째 시도: WEBM_OPUS 포맷
                try:
                    config = speech.RecognitionConfig(
                        encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                        sample_rate_hertz=48000,
                        language_code="ko-KR",
                        alternative_language_codes=["en-US"],
                        enable_automatic_punctuation=True,
                        use_enhanced=True,
                        model="latest_long",
                    )
                    print("🎤 WEBM_OPUS 포맷으로 STT 재시도")
                    response = self.google_client.recognize(config=config, audio=audio)
                except Exception as e2:
                    print(f"⚠️ WEBM_OPUS 포맷도 실패, 포맷 자동 감지로 최종 시도: {e2}")
                    # 세 번째 시도: 포맷 자동 감지
                    config = speech.RecognitionConfig(
                        # encoding을 지정하지 않으면 자동 감지
                        language_code="ko-KR",
                        alternative_language_codes=["en-US"],
                        enable_automatic_punctuation=True,
                        use_enhanced=True,
                        model="latest_long",
                    )
                    print("🎤 포맷 자동 감지로 STT 최종 시도")
                    response = self.google_client.recognize(config=config, audio=audio)
            
            if response.results:
                # 가장 신뢰도 높은 결과 선택
                transcript = response.results[0].alternatives[0].transcript
                confidence = response.results[0].alternatives[0].confidence
                
                print(f"✅ Google STT 인식 성공: '{transcript}' (신뢰도: {confidence:.2f})")
                
                # 종료 명령어 감지
                exit_commands = ['종료', '그만', '끝', '나가기', 'exit', 'quit', 'stop']
                cleaned_text = transcript.lower().replace(' ', '').replace('.', '')
                
                for exit_cmd in exit_commands:
                    if exit_cmd.lower() in cleaned_text:
                        print(f"🚪 종료 명령어 감지: {exit_cmd}")
                        return "종료"
                
                return transcript.strip()
            else:
                print("❌ Google STT: 인식된 텍스트가 없음")
                return ""
                
        except Exception as e:
            print(f"❌ Google STT 처리 실패: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return ""
    
    def transcribe_with_google_file(self, audio_file_path: str) -> str:
        """Google STT: 파일에서 오디오를 텍스트로 변환"""
        if not self.google_client:
            print("❌ Google Speech Client가 초기화되지 않음")
            return ""
            
        try:
            print(f"🎤 Google STT 파일 처리: {audio_file_path}")
            
            # 파일 존재 확인
            if not os.path.exists(audio_file_path):
                print(f"❌ 파일이 존재하지 않음: {audio_file_path}")
                return ""
            
            # 오디오 파일 읽기
            with open(audio_file_path, "rb") as audio_file:
                audio_content = audio_file.read()
            
            # Google Speech API 요청 설정
            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,  # WAV 파일용
                sample_rate_hertz=16000,
                language_code="ko-KR",
                alternative_language_codes=["en-US"],
                enable_automatic_punctuation=True,
                use_enhanced=True,
                model="latest_long",
            )
            
            # STT 실행
            response = self.google_client.recognize(config=config, audio=audio)
            
            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                confidence = response.results[0].alternatives[0].confidence
                
                print(f"✅ Google STT 파일 인식 성공: '{transcript}' (신뢰도: {confidence:.2f})")
                
                # 종료 명령어 감지
                exit_commands = ['종료', '그만', '끝', '나가기', 'exit', 'quit', 'stop']
                cleaned_text = transcript.lower().replace(' ', '').replace('.', '')
                
                for exit_cmd in exit_commands:
                    if exit_cmd.lower() in cleaned_text:
                        return "종료"
                
                return transcript.strip()
            else:
                print("❌ Google STT 파일: 인식된 텍스트가 없음")
                return ""
                
        except Exception as e:
            print(f"❌ Google STT 파일 처리 실패: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return ""

