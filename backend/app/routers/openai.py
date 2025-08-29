from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from services.openai_story import OpenAIService, ChatRequest, ChatResponse, ChatMessage, openai_service
from datetime import datetime
from core.config import supabase_admin
import httpx
import asyncio

router = APIRouter()


class SimpleChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = None


class SimpleChatResponse(BaseModel):
    response: str
    timestamp: datetime


class StoryGenerationRequest(BaseModel):
    conversation_data: List[Dict[str, str]]
    

class StoryGenerationResponse(BaseModel):
    story: str
    timestamp: datetime


class GrandparentStoryRequest(BaseModel):
    session_id: str
    

class GrandparentStoryResponse(BaseModel):
    story: str
    session_id: str
    timestamp: datetime


class TTSRequest(BaseModel):
    story_id: str
    fish_speech_endpoint: str  # GPU 인스턴스의 Fish Speech API 엔드포인트


class TTSResponse(BaseModel):
    story_id: str
    tts_audio_path: str
    tts_status: str
    timestamp: datetime


class BackgroundJobRequest(BaseModel):
    session_id: str
    fish_speech_endpoint: Optional[str] = None  # 선택적으로 만들어서 기본값 사용 가능


class BackgroundJobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    timestamp: datetime


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    step: str
    message: str
    result: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=SimpleChatResponse)
async def simple_chat(
    request: SimpleChatRequest,
    service: OpenAIService = Depends(lambda: openai_service)
):
    """간단한 채팅 엔드포인트"""
    try:
        response = await service.simple_chat(
            message=request.message,
            system_prompt=request.system_prompt
        )
        
        return SimpleChatResponse(
            response=response,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/completion", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    service: OpenAIService = Depends(lambda: openai_service)
):
    """OpenAI Chat Completion API 직접 호출"""
    try:
        response = await service.chat_completion(request)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/story/generate", response_model=StoryGenerationResponse)
async def generate_story(
    request: StoryGenerationRequest,
    service: OpenAIService = Depends(lambda: openai_service)
):
    """대화 데이터를 기반으로 스토리 생성"""
    try:
        story = await service.generate_story(request.conversation_data)
        
        return StoryGenerationResponse(
            story=story,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/story/grandparent", response_model=GrandparentStoryResponse)
async def generate_grandparent_story(
    request: GrandparentStoryRequest,
    service: OpenAIService = Depends(lambda: openai_service)
):
    """세션 ID로 Supabase에서 대화 기록을 가져와서 할머니/할아버지 스타일 이야기로 변환하고 DB에 저장"""
    try:
        # 1. 세션 정보 가져오기 (user_id, selected_photos)
        print(f"Debug - Getting session info for session_id: {request.session_id}")
        session_response = supabase_admin.table("sessions").select(
            "user_id, selected_photos"
        ).eq("id", request.session_id).single().execute()
        
        if not session_response.data:
            raise HTTPException(status_code=404, detail="해당 세션을 찾을 수 없습니다.")
        
        user_id = session_response.data["user_id"]
        selected_photos = session_response.data["selected_photos"]
        print(f"Debug - Session info: user_id={user_id}, photos={selected_photos}")
        
        # user_id에서 family_id 가져오기
        user_response = supabase_admin.table("family_members").select(
            "family_id"
        ).eq("user_id", user_id).single().execute()
        
        family_id = user_response.data["family_id"] if user_response.data else None
        if not family_id:
            raise HTTPException(status_code=404, detail="사용자의 family_id를 찾을 수 없습니다.")
        
        print(f"Debug - Family ID: {family_id}")
        
        # 2. 대화 기록 가져오기
        print(f"Debug - Getting conversations for session_id: {request.session_id}")
        conversations_response = supabase_admin.table("conversations").select(
            "id, conversation_order, question_text, user_response_text"
        ).eq("session_id", request.session_id).order("conversation_order").execute()
        
        print(f"Debug - Number of conversations found: {len(conversations_response.data) if conversations_response.data else 0}")
        
        if not conversations_response.data:
            raise HTTPException(status_code=404, detail="해당 세션의 대화 기록을 찾을 수 없습니다.")
        
        # 3. 할머니/할아버지 스타일 이야기 생성
        story = await service.generate_grandparent_story(conversations_response.data)
        print(f"Debug - Generated story length: {len(story)}")
        
        # 4. photo_stories 테이블에 저장
        conversation_ids = [conv["id"] for conv in conversations_response.data]
        
        # selected_photos 배열의 첫 번째 photo_id 사용 (여러 사진이 있을 수 있으므로)
        photo_id = selected_photos[0] if selected_photos and len(selected_photos) > 0 else None
        
        if not photo_id:
            raise HTTPException(status_code=400, detail="세션에 연결된 사진이 없습니다.")
        
        story_data = {
            "user_id": user_id,
            "family_id": family_id,
            "photo_id": photo_id,
            "title": f"할머니의 이야기 - {datetime.now().strftime('%Y년 %m월 %d일')}",
            "story_text": story,
            "language": "ko",
            "status": "generated",
            "source_session_ids": [request.session_id],
            "source_conversation_ids": conversation_ids,
            "tts_audio_path": None,
            "tts_status": None,
            "tts_params": None
        }
        
        print(f"Debug - Saving story to photo_stories table")
        # upsert with on_conflict parameter to handle unique constraint
        story_response = supabase_admin.table("photo_stories").upsert(
            story_data, 
            on_conflict="user_id,photo_id"
        ).execute()
        
        print(f"Debug - Story saved successfully with ID: {story_response.data[0]['id'] if story_response.data else 'Unknown'}")
        
        return GrandparentStoryResponse(
            story=story,
            session_id=request.session_id,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error - Exception occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/story/tts", response_model=TTSResponse)
async def generate_tts_from_story(
    request: TTSRequest
):
    """Story ID로 Supabase에서 스토리와 참조 오디오를 가져와 Fish Speech TTS 생성"""
    try:
        # 1. photo_stories에서 story_text와 source_conversation_ids 가져오기
        print(f"Debug - Getting story data for story_id: {request.story_id}")
        story_response = supabase_admin.table("photo_stories").select(
            "story_text, source_conversation_ids, user_id, photo_id, family_id"
        ).eq("id", request.story_id).execute()
        
        if not story_response.data or len(story_response.data) == 0:
            raise HTTPException(status_code=404, detail="해당 스토리를 찾을 수 없습니다.")
        
        story_data = story_response.data[0]
        story_text = story_data["story_text"]
        source_conversation_ids = story_data["source_conversation_ids"]
        user_id = story_data["user_id"]
        photo_id = story_data["photo_id"]
        family_id = story_data["family_id"]
        
        print(f"Debug - Story text length: {len(story_text)}")
        print(f"Debug - Source conversation IDs: {source_conversation_ids}")
        print(f"Debug - Family ID: {family_id}")
        
        # 3. 첫 번째 conversation_id의 user_response_audio_url 가져오기
        if not source_conversation_ids or len(source_conversation_ids) == 0:
            raise HTTPException(status_code=400, detail="참조할 대화 기록이 없습니다.")
        
        first_conversation_id = source_conversation_ids[0]
        print(f"Debug - Getting audio from conversation_id: {first_conversation_id}")
        
        conversation_response = supabase_admin.table("conversations").select(
            "user_response_audio_url"
        ).eq("id", first_conversation_id).execute()
        
        print(f"Debug - Conversation response: {conversation_response.data}")
        
        if not conversation_response.data or len(conversation_response.data) == 0:
            raise HTTPException(status_code=404, detail="참조할 오디오 파일을 찾을 수 없습니다.")
        
        reference_audio_url = conversation_response.data[0]["user_response_audio_url"]
        print(f"Debug - Raw audio URL from DB: '{reference_audio_url}'")
        
        if not reference_audio_url:
            raise HTTPException(status_code=400, detail="참조 오디오 파일이 존재하지 않습니다.")
        
        print(f"Debug - Reference audio URL: {reference_audio_url}")
        
        # TTS 작업 시작을 위해 상태를 running으로 업데이트
        supabase_admin.table("photo_stories").update({
            "tts_status": "running",
            "updated_at": datetime.now().isoformat()
        }).eq("id", request.story_id).execute()
        
        # 완전한 Supabase Storage URL 생성 (signed URL for private bucket)
        if not reference_audio_url.startswith('http'):
            full_audio_url = None
            max_attempts = 3
            
            for attempt in range(max_attempts):
                try:
                    print(f"Debug - Attempting to create signed URL (attempt {attempt + 1}/{max_attempts})")
                    
                    # Create signed URL with longer expiration time
                    signed_url_response = supabase_admin.storage.from_("voice").create_signed_url(
                        path=reference_audio_url,
                        expires_in=7200  # 2 hours
                    )
                    
                    if signed_url_response and 'signedURL' in signed_url_response:
                        full_audio_url = signed_url_response['signedURL']
                        print(f"Debug - Signed URL created successfully on attempt {attempt + 1}")
                        break
                        
                except Exception as e:
                    print(f"Debug - Signed URL attempt {attempt + 1} failed: {e}")
                    if attempt < max_attempts - 1:  # 마지막 시도가 아니면 잠깐 대기
                        print(f"Debug - Waiting 3 seconds before retry...")
                        await asyncio.sleep(3)
            
            # 모든 시도가 실패한 경우
            if not full_audio_url:
                print("Error - All signed URL attempts failed")
                raise HTTPException(
                    status_code=500, 
                    detail="참조 오디오 파일에 접근할 수 없습니다. Supabase 연결 문제가 있습니다."
                )
        else:
            full_audio_url = reference_audio_url
            
        print(f"Debug - Full audio URL: {full_audio_url}")
        
        # URL 접근 테스트
        try:
            import httpx
            async with httpx.AsyncClient() as test_client:
                test_response = await test_client.head(full_audio_url)
                print(f"Debug - URL test response: {test_response.status_code}")
        except Exception as url_test_error:
            print(f"Debug - URL test failed: {url_test_error}")
        
        # 3. Fish Speech API 호출
        fish_speech_payload = {
            "text": story_text,
            "reference_audio": full_audio_url,
            "reference_text": "",
            "output_format": "base64"
        }
        
        print(f"Debug - Calling Fish Speech API at: {request.fish_speech_endpoint}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5분 타임아웃
            fish_response = await client.post(
                request.fish_speech_endpoint,
                json=fish_speech_payload
            )
            
            if fish_response.status_code != 200:
                print(f"Error - Fish Speech API error: {fish_response.status_code} - {fish_response.text}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Fish Speech API 오류: {fish_response.status_code}"
                )
            
            fish_result = fish_response.json()
            print(f"Debug - Fish Speech response received")
        
        # 4. TTS 결과를 Supabase Storage에 저장 (base64 디코딩 후)
        import base64
        import uuid
        
        # base64 오디오 데이터 디코딩
        audio_base64 = fish_result.get("audio_base64", "")  # GPU 서버 응답 구조에 맞춤
        if not audio_base64:
            raise HTTPException(status_code=500, detail="Fish Speech에서 오디오 데이터를 받지 못했습니다.")
        
        # GPU 서버 응답 정보 로깅
        sample_rate = fish_result.get("sample_rate", 22050)
        duration = fish_result.get("duration", 0.0)
        print(f"Debug - Audio info: sample_rate={sample_rate}, duration={duration}s")
        
        audio_data = base64.b64decode(audio_base64)
        
        # 파일명 생성 (photo_id + timestamp)
        audio_filename = f"{photo_id}_{int(datetime.now().timestamp())}.wav"
        audio_path = f"{family_id}/{user_id}/{audio_filename}"
        
        # Supabase Storage에 업로드
        print(f"Debug - Uploading audio to Supabase Storage: {audio_path}")
        storage_response = supabase_admin.storage.from_("fishspeech").upload(
            audio_path, 
            audio_data,
            file_options={"content-type": "audio/wav"}
        )
        
        if hasattr(storage_response, 'error') and storage_response.error:
            print(f"Error - Storage upload failed: {storage_response.error}")
            raise HTTPException(status_code=500, detail="오디오 파일 저장에 실패했습니다.")
        
        # 5. photo_stories 테이블의 TTS 관련 필드 업데이트
        tts_params = {
            "fish_speech_endpoint": request.fish_speech_endpoint,
            "reference_audio_url": reference_audio_url,
            "generated_at": datetime.now().isoformat()
        }
        
        update_response = supabase_admin.table("photo_stories").update({
            "tts_audio_path": audio_path,
            "tts_status": "succeeded",
            "tts_params": tts_params,
            "updated_at": datetime.now().isoformat()
        }).eq("id", request.story_id).execute()
        
        print(f"Debug - Updated photo_stories with TTS info")
        
        return TTSResponse(
            story_id=request.story_id,
            tts_audio_path=audio_path,
            tts_status="succeeded",
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error - Exception occurred: {str(e)}")
        
        # 실패 시 photo_stories의 tts_status를 failed로 업데이트
        try:
            supabase_admin.table("photo_stories").update({
                "tts_status": "failed",
                "updated_at": datetime.now().isoformat()
            }).eq("id", request.story_id).execute()
        except:
            pass
        
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/story/process-background", response_model=BackgroundJobResponse)
async def process_story_and_tts_background_endpoint(
    request: BackgroundJobRequest
):
    """세션 ID로 스토리 생성 + TTS를 백그라운드에서 처리"""
    try:
        # 세션 유효성 검사
        session_response = supabase_admin.table("sessions").select("id").eq("id", request.session_id).single().execute()
        if not session_response.data:
            raise HTTPException(status_code=404, detail="해당 세션을 찾을 수 없습니다.")
        
        # 동적으로 Celery 작업 import (startup 시 config 에러 방지)
        try:
            from tasks.story_tasks import process_story_and_tts_background
            from core.config import settings
            
            # Fish Speech 엔드포인트 설정 (요청에 없으면 기본값 사용)
            fish_endpoint = request.fish_speech_endpoint or settings.FISH_SPEECH_ENDPOINT
            
            # Celery 작업 시작
            task = process_story_and_tts_background.delay(
                session_id=request.session_id,
                fish_speech_endpoint=fish_endpoint
            )
            
            return BackgroundJobResponse(
                job_id=task.id,
                status="queued",
                message="스토리 및 TTS 생성 작업이 큐에 추가되었습니다.",
                timestamp=datetime.now()
            )
        except ImportError as import_error:
            raise HTTPException(
                status_code=503, 
                detail=f"백그라운드 작업 서비스를 사용할 수 없습니다: {str(import_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/story/job-status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """백그라운드 작업 상태 조회"""
    try:
        # 동적으로 Celery 앱 import
        from tasks.story_tasks import celery_app
        
        # Celery 작업 상태 조회
        task = celery_app.AsyncResult(job_id)
        
        if task.state == 'PENDING':
            response = {
                'job_id': job_id,
                'status': 'pending',
                'progress': 0,
                'step': 'waiting',
                'message': '작업 대기 중입니다.'
            }
        elif task.state == 'PROCESSING':
            response = {
                'job_id': job_id,
                'status': 'processing',
                'progress': task.info.get('progress', 0),
                'step': task.info.get('step', 'unknown'),
                'message': task.info.get('message', '처리 중입니다.')
            }
            # 중간 결과가 있으면 포함
            if 'story_id' in task.info:
                response['result'] = {'story_id': task.info['story_id']}
        elif task.state == 'SUCCESS':
            response = {
                'job_id': job_id,
                'status': 'completed',
                'progress': 100,
                'step': 'completed',
                'message': '모든 작업이 완료되었습니다.',
                'result': task.result
            }
        elif task.state == 'FAILURE':
            response = {
                'job_id': job_id,
                'status': 'failed',
                'progress': 0,
                'step': 'error',
                'message': f'작업 실패: {str(task.info)}'
            }
        else:
            response = {
                'job_id': job_id,
                'status': task.state.lower(),
                'progress': 0,
                'step': 'unknown',
                'message': f'알 수 없는 상태: {task.state}'
            }
        
        return JobStatusResponse(**response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """OpenAI 서비스 상태 확인"""
    try:
        # 간단한 테스트 요청으로 API 키 유효성 검증
        test_response = await openai_service.simple_chat("Hello")
        return {
            "status": "healthy",
            "message": "OpenAI service is working properly",
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"OpenAI service is not available: {str(e)}"
        )