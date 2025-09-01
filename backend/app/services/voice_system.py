import azure.cognitiveservices.speech as speechsdk
import requests
import os, time
import uuid
from pathlib import Path
from dotenv import load_dotenv
import pygame
from fastapi import UploadFile
import json
import base64
from google.cloud import speech
from google.oauth2 import service_account

from core.config import settings

AUDIO_DIR = "audio_files"

class VoiceSystem:
    """음성 입출력 시스템"""
    
    def __init__(self):
        # Azure Speech Service 설정
        self.speech_key    = os.getenv("AZURE_SPEECH_KEY")
        self.region = os.getenv("AZURE_SPEECH_REGION")
        
        # STT 설정
        if self.speech_key and self.region:
            self.speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.region)
            self.speech_config.speech_recognition_language = "ko-KR"
        
        # TTS 설정
        self.tts_voice = "ko-KR-SunHiNeural"
        
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
        
        # 오디오 폴더
        self.audio_dir = Path("audio_files")
        self.audio_dir.mkdir(exist_ok=True)
        
        # pygame 초기화
        try:
            pygame.mixer.init()
            self.audio_enabled = True
        except:
            self.audio_enabled = False
    
    def transcribe_speech(self) -> str:
        """STT: 음성을 텍스트로 변환"""
        try:
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, 
                audio_config=audio_config
            )
            
            print("🎙️ 말씀해 주세요...")
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                recognized_text = result.text.strip()
                print(f"👤 \"{recognized_text}\"")
                
                # 종료 명령어 감지
                exit_commands = ['종료', '그만', '끝', '나가기', 'exit', 'quit', 'stop']
                cleaned_text = recognized_text.lower().replace(' ', '').replace('.', '')
                
                for exit_cmd in exit_commands:
                    if exit_cmd.lower() in cleaned_text:
                        return "종료"
                
                return recognized_text
            else:
                print("❌ 음성을 인식할 수 없습니다. 다시 말씀해 주세요.")
                return ""
        except Exception:
            return ""
        
    def transcribe_speech_wav(self, audio_file) -> str:
        """STT: 음성을 텍스트로 변환"""
        try:
            input_path = self.audio_dir / f"{audio_file}"
            audio_config = speechsdk.audio.AudioConfig(filename=input_path)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, 
                audio_config=audio_config
            )
            
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                recognized_text = result.text.strip()
                print(f"👤 \"{recognized_text}\"")
                
                # 종료 명령어 감지
                exit_commands = ['종료', '그만', '끝', '나가기', 'exit', 'quit', 'stop']
                cleaned_text = recognized_text.lower().replace(' ', '').replace('.', '')
                
                for exit_cmd in exit_commands:
                    if exit_cmd.lower() in cleaned_text:
                        return "종료"
                
                return recognized_text
            else:
                print("❌ 음성을 인식할 수 없습니다. 다시 말씀해 주세요.")
                return ""
        except Exception:
            return ""
        
    def transcribe_speech_wav2(self, file: UploadFile) -> str:
        """STT: 업로드된 UploadFile 객체를 텍스트로 변환"""
        try:
            # 임시 파일 저장
            unique_name = f"{uuid.uuid4().hex}.wav"
            temp_path = self.audio_dir / unique_name
            with open(temp_path, "wb") as f:
                f.write(file.file.read())

            # Azure Speech SDK로 인식
            audio_config = speechsdk.audio.AudioConfig(filename=str(temp_path))
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            result = speech_recognizer.recognize_once()

            # 인식 결과 확인
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                recognized_text = result.text.strip()
                return recognized_text
            else:
                print("❌ 인식 실패:", result.reason)
                return ""

        except Exception as e:
            print("❌ 예외 발생:", e)
            return ""
        finally:
            # 임시 파일 삭제
            try:
                temp_path.unlink()
            except Exception:
                pass

    def transcribe_speech_from_file(self, audio_path: str) -> str:
        """STT: 파일에서 음성을 텍스트로 변환 (Azure Speech REST API 방식, 디버깅 로그 포함)"""
        print(f"[DEBUG][transcribe_speech_from_file] 호출됨 - audio_path: {audio_path}")
        try:
            # 파일 존재 여부 확인
            if not os.path.exists(audio_path):
                print(f"[ERROR][transcribe_speech_from_file] 파일이 존재하지 않음: {audio_path}")
                return ""
            file_size = os.path.getsize(audio_path)
            print(f"[DEBUG][transcribe_speech_from_file] 파일 크기: {file_size} bytes")
            if file_size == 0:
                print(f"[ERROR][transcribe_speech_from_file] 파일이 비어있음: {audio_path}")
                return ""
            ext = os.path.splitext(audio_path)[-1].lower()
            print(f"[DEBUG][transcribe_speech_from_file] 파일 확장자: {ext}")

            # 환경변수에서 키/리전/엔드포인트 불러오기
            speech_key = os.getenv("AZURE_SPEECH_KEY")
            region = os.getenv("AZURE_SPEECH_REGION")
            endpoint = os.getenv("AZURE_SPEECH_ENDPOINT")
            if not speech_key or not region or not endpoint:
                print(f"[ERROR][transcribe_speech_from_file] 환경변수 누락: key={speech_key}, region={region}, endpoint={endpoint}")
                return ""

            # 1. 인증 토큰 발급
            token_url = f"{endpoint.rstrip('/')}/sts/v1.0/issueToken"
            print(f"[DEBUG][transcribe_speech_from_file] 토큰 발급 URL: {token_url}")
            headers = {"Ocp-Apim-Subscription-Key": speech_key}
            token_resp = requests.post(token_url, headers=headers)
            if token_resp.status_code != 200:
                print(f"[ERROR][transcribe_speech_from_file] 토큰 발급 실패: {token_resp.status_code}, {token_resp.text}")
                return ""
            token = token_resp.text
            print(f"[DEBUG][transcribe_speech_from_file] 토큰 발급 성공")

            # 2. STT REST API 요청
            stt_url = f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
            params = {"language": "ko-KR"}
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000"
            }
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            print(f"[DEBUG][transcribe_speech_from_file] STT 요청 시작: {stt_url}")
            response = requests.post(stt_url, params=params, headers=headers, data=audio_data)
            print(f"[DEBUG][transcribe_speech_from_file] STT 응답 코드: {response.status_code}")
            print(f"[DEBUG][transcribe_speech_from_file] STT 응답 본문: {response.text}")
            if response.status_code == 200:
                result = response.json()
                recognized_text = result.get("DisplayText", "").strip()
                print(f"[DEBUG][transcribe_speech_from_file] 인식된 텍스트: {recognized_text}")
                # 종료 명령어 감지
                exit_commands = ['종료', '그만', '끝', '나가기', 'exit', 'quit', 'stop']
                cleaned_text = recognized_text.lower().replace(' ', '').replace('.', '')
                for exit_cmd in exit_commands:
                    if exit_cmd.lower() in cleaned_text:
                        print(f"[DEBUG][transcribe_speech_from_file] 종료 명령어 감지: {exit_cmd}")
                        return "종료"
                return recognized_text
            else:
                print(f"[ERROR][transcribe_speech_from_file] 음성을 인식할 수 없음. status={response.status_code}")
                return ""
        except Exception as e:
            print(f"[ERROR][transcribe_speech_from_file] 예외 발생: {e}")
            import traceback; traceback.print_exc()
            return ""
    
    def transcribe_with_google_base64(self, audio_base64: str) -> str:
        """Google STT: base64 인코딩된 오디오를 텍스트로 변환"""
        if not self.google_client:
            print("❌ Google Speech Client가 초기화되지 않음")
            return ""
        
        try:
            print(f"🎤 Google STT 처리 시작: 데이터 길이 {len(audio_base64)} chars")
            
            # base64 디코딩
            audio_content = base64.b64decode(audio_base64)
            
            # Google Speech API 요청 설정
            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,  # Flutter record 기본 포맷
                sample_rate_hertz=48000,  # 일반적인 WebM Opus 샘플레이트
                language_code="ko-KR",
                alternative_language_codes=["en-US"],  # 영어 대안
                enable_automatic_punctuation=True,
                use_enhanced=True,
                model="latest_long",
            )
            
            # STT 실행
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

    def get_access_token(self):
        """Azure Speech Service 액세스 토큰 요청"""
        url = f"https://{self.region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        headers = {"Ocp-Apim-Subscription-Key": self.speech_key}
        try:
            res = requests.post(url, headers=headers)
            res.raise_for_status()
            return res.text
        except Exception:
            return None
    
    def synthesize_speech(self, text: str) -> str:
        """TTS: 텍스트를 음성으로 변환하고 재생"""
        if not text.strip():
            return None
            
        try:
            token = self.get_access_token()
            if not token:
                return None
                
            tts_url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
                "User-Agent": "DementiaAnalysisSystem"
            }
            
            ssml = f"""
            <speak version='1.0' xml:lang='ko-KR'>
                <voice xml:lang='ko-KR' xml:gender='Female' name='{self.tts_voice}'>
                    {text}
                </voice>
            </speak>
            """
            
            res = requests.post(tts_url, headers=headers, data=ssml.encode("utf-8"))
            res.raise_for_status()
            
            # 음성 파일 저장
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = self.audio_dir / f"tts_{timestamp}.wav"
            
            with open(output_path, "wb") as f:
                f.write(res.content)
            
            # 음성 재생
            if self.audio_enabled:
                try:
                    pygame.mixer.music.load(str(output_path))
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                except Exception:
                    pass
            
            return str(output_path)
            
        except Exception:
            return None