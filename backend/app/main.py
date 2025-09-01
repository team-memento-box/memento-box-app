from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import uuid
from datetime import datetime
import base64
import tempfile
import io
from pydub import AudioSegment
from services.dialogue_workflow import DialogueWorkflow, WorkflowInput
from services.voice_system import VoiceSystem
from core.auth import get_supabase_user
from core.config import supabase_admin

from routers import chat, conversation, openai, audio_analysis, photos  # AI 전용 라우터들

app = FastAPI(title="Memento Box AI API", description="AI 전용 API - 채팅, 이미지 분석, 음성 합성")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI 전용 라우터 등록
app.include_router(chat.router, prefix="/api", tags=["chat-legacy"])
app.include_router(conversation.router, prefix="/api", tags=["conversation"])
app.include_router(openai.router, prefix="/api/openai", tags=["openai"])

app.include_router(audio_analysis.router, prefix="/api", tags=["audio-analysis"])

app.include_router(photos.router, prefix="/api", tags=["photos"])

# LangGraph 대화 워크플로우 초기화
workflow = DialogueWorkflow()

# 음성 시스템 초기화
voice_system = VoiceSystem()

async def create_session(user_id: str, conversation_id: str, photo_id: str = None) -> str:
    """새로운 대화 세션을 생성하고 세션 ID 반환"""
    try:
        # conversation_id를 session_id로 사용
        session_id = conversation_id
        
        print(f"🔍 세션 생성 시도: session_id={session_id}, user_id={user_id}, photo_id={photo_id}")
        
        # 기존 세션 확인
        existing_session = supabase_admin.table("sessions").select("*").eq("id", session_id).execute()
        
        if existing_session.data:
            print(f"✅ 기존 세션 발견: {session_id}")
            return session_id
        
        # sessions 테이블에 새 세션 생성
        session_data = {
            "id": session_id,
            "user_id": user_id,
            "session_type": "reminiscence",  # 추억 회상 대화
            "status": "active"
        }
        
        # photo_id가 있다면 selected_photos 배열에 추가 (스키마에 맞춤)
        if photo_id:
            session_data["selected_photos"] = [photo_id]
        
        print(f"📝 세션 데이터 생성: {session_data}")
        
        # Supabase 서비스 역할로 세션 생성
        result = supabase_admin.table("sessions").insert(session_data).execute()
        
        if not result.data:
            print(f"❌ 세션 생성 실패: 응답 데이터가 없음")
            raise Exception("세션 생성 실패 - 응답 데이터 없음")
        
        print(f"✅ 새 세션 생성 성공: {session_id} (사용자: {user_id}, 사진: {photo_id})")
        return session_id
        
    except Exception as e:
        print(f"❌ 세션 생성 오류: {type(e).__name__}: {str(e)}")
        # 디버깅을 위해 상세 오류 정보 출력
        import traceback
        print(f"📋 상세 오류: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"세션 생성에 실패했습니다: {str(e)}")

@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(websocket: WebSocket, conversation_id: str):
    """실시간 대화를 위한 WebSocket 엔드포인트"""
    client_host = websocket.client.host if websocket.client else "unknown"
    client_port = websocket.client.port if websocket.client else "unknown"
    print(f"🌐 WebSocket 연결 요청: conversation_id={conversation_id}, client={client_host}:{client_port}")
    
    await websocket.accept()
    print(f"✅ WebSocket 연결 수락 완료: conversation_id={conversation_id}")
    
    user_authenticated = False
    user_id = None
    session_created = False
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            print(f"📥 WebSocket 메시지 수신 대기 중... (conversation_id={conversation_id})")
            data = await websocket.receive_text()
            print(f"📨 WebSocket 메시지 수신: {data[:200]}..." if len(data) > 200 else f"📨 WebSocket 메시지 수신: {data}")
            
            try:
                message_data = json.loads(data)
                print(f"📋 메시지 파싱 성공: {message_data.keys()}")
            except json.JSONDecodeError as e:
                print(f"❌ 메시지 파싱 실패: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "잘못된 메시지 형식입니다.",
                    "conversation_id": conversation_id
                }))
                continue
            
            # 첫 번째 메시지에서 JWT 토큰 검증 및 세션 생성
            if not user_authenticated:
                jwt_token = message_data.get("jwt_token")
                if not jwt_token:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "인증 토큰이 필요합니다.",
                        "conversation_id": conversation_id
                    }))
                    continue
                
                try:
                    # Supabase JWT 토큰 검증
                    user_info = await get_supabase_user(jwt_token)
                    user_id = user_info["id"]
                    user_authenticated = True
                    print(f"사용자 인증 성공: {user_id}")
                    
                    # 세션 생성 (conversation_id를 session_id로 사용, photo_id가 있다면 함께)
                    photo_id = message_data.get("photo_context", {}).get("photo_id")
                    session_id = await create_session(user_id, conversation_id, photo_id)
                    session_created = True
                    
                    print(f"✅ 인증 및 세션 생성 완료: user_id={user_id}, session_id={session_id}")
                    
                    # 인증 및 세션 생성 성공 알림
                    await websocket.send_text(json.dumps({
                        "type": "auth_success",
                        "message": "인증 및 세션 생성이 완료되었습니다.",
                        "conversation_id": conversation_id,
                        "session_id": session_id,
                        "user_id": user_id
                    }))
                    
                except Exception as e:
                    print(f"인증 실패: {type(e).__name__}: {str(e)}")
                    import traceback
                    print(f"인증 실패 상세: {traceback.format_exc()}")
                    await websocket.send_text(json.dumps({
                        "type": "error", 
                        "message": f"인증에 실패했습니다: {str(e)}",
                        "conversation_id": conversation_id,
                        "error_detail": str(e)
                    }))
                    continue
            
            # 메시지 타입에 따른 처리
            message_type = message_data.get("type", "text")
            user_message = ""
            
            if message_type == "audio":
                # 오디오 메시지 처리 (Google STT)
                audio_base64 = message_data.get("audio_data", "")
                if not audio_base64:
                    await websocket.send_text(json.dumps({
                        "type": "error", 
                        "message": "오디오 데이터가 비어있습니다.",
                        "conversation_id": conversation_id
                    }))
                    continue
                
                print(f"🎤 오디오 메시지 수신: {len(audio_base64)} chars")
                
                # STT 처리 중 알림
                await websocket.send_text(json.dumps({
                    "type": "processing",
                    "message": "음성을 텍스트로 변환하고 있습니다...",
                    "conversation_id": conversation_id
                }))
                
                # Google STT로 텍스트 변환
                user_message = voice_system.transcribe_with_google_base64(audio_base64)
                if not user_message:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "음성을 인식할 수 없습니다. 다시 시도해주세요.",
                        "conversation_id": conversation_id
                    }))
                    continue
                
                print(f"🎯 STT 변환 완료: '{user_message}'")
                
                # STT 변환된 텍스트를 즉시 클라이언트에 전송
                await websocket.send_text(json.dumps({
                    "type": "transcribed_text",
                    "text": user_message,
                    "conversation_id": conversation_id
                }, ensure_ascii=False))
                
                # 음성 파일을 Supabase Storage에 저장
                audio_url = None
                try:
                    # family_id 조회 (family_members 테이블에서)
                    family_response = supabase_admin.table("family_members").select("family_id").eq("user_id", user_id).limit(1).execute()
                    family_id = family_response.data[0]["family_id"] if family_response.data else None
                    
                    if family_id:
                        # 오디오 데이터 디코딩
                        audio_bytes = base64.b64decode(audio_base64)
                        
                        # M4A를 WAV로 변환
                        try:
                            # M4A 데이터를 AudioSegment로 로드
                            audio_io = io.BytesIO(audio_bytes)
                            audio_segment = AudioSegment.from_file(audio_io, format="m4a")
                            
                            # WAV로 변환
                            wav_io = io.BytesIO()
                            audio_segment.export(wav_io, format="wav")
                            wav_bytes = wav_io.getvalue()
                            
                            print(f"✅ M4A를 WAV로 변환 완료 (크기: {len(audio_bytes)} -> {len(wav_bytes)})")
                        except Exception as convert_error:
                            print(f"⚠️ 오디오 변환 실패, 원본 사용: {convert_error}")
                            wav_bytes = audio_bytes  # 변환 실패 시 원본 사용
                        
                        # conversation_id 생성 (UUID)
                        audio_conversation_id = str(uuid.uuid4())
                        
                        # 파일 경로 생성
                        file_path = f"{family_id}/{user_id}/{conversation_id}/{audio_conversation_id}.wav"
                        
                        # Supabase Storage에 업로드
                        storage_response = supabase_admin.storage.from_("voice").upload(
                            file_path,
                            wav_bytes,
                            {"content-type": "audio/wav"}
                        )
                        
                        # 상대 경로로 저장 (전체 URL 대신)
                        audio_url = file_path
                        print(f"✅ 음성 파일 저장 완료: {audio_url}")
                    else:
                        print("⚠️ family_id를 찾을 수 없어 음성 파일을 저장하지 않습니다")
                        
                except Exception as e:
                    print(f"❌ 음성 파일 저장 실패: {e}")
                    # 저장 실패해도 대화는 계속 진행
                
            elif message_type == "text":
                # 텍스트 메시지 처리
                user_message = message_data.get("message", "").strip()
                if not user_message:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "메시지가 비어있습니다.",
                        "conversation_id": conversation_id
                    }))
                    continue
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"지원하지 않는 메시지 타입입니다: {message_type}",
                    "conversation_id": conversation_id
                }))
                continue
            
            print(f"Received message: {user_message} from user: {user_id}")
            
            # 입력 데이터 구성 (오디오 URL 포함)
            workflow_input = WorkflowInput(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=user_message,
                photo_context=message_data.get("photo_context", {})
            )
            
            # 오디오 URL이 있으면 workflow_input에 추가
            if message_type == "audio" and audio_url:
                workflow_input["audio_url"] = audio_url
            
            # 처리 시작 알림
            await websocket.send_text(json.dumps({
                "type": "processing",
                "message": "답변을 생성하고 있습니다...",
                "conversation_id": conversation_id
            }))
            
            # LangGraph 워크플로우 실행 (인증된 클라이언트 전달)
            response = await workflow.process_message(workflow_input, authenticated_client=supabase_admin)
            
            # 응답 전송
            await websocket.send_text(json.dumps({
                "type": "response",
                "data": response,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False))
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for conversation: {conversation_id}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error for conversation {conversation_id}: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "메시지 형식이 올바르지 않습니다.",
                "conversation_id": conversation_id
            }))
        except:
            pass
    except Exception as e:
        print(f"WebSocket error for conversation {conversation_id}: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                "conversation_id": conversation_id,
                "error_details": str(e) if app.debug else None
            }))
        except:
            pass

@app.get("/")
def read_root():
    return {"message": "Memento Box AI API with WebSocket & LangGraph"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "supabase_configured": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))
    }