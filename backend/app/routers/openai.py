from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from services.openai_story import OpenAIService, ChatRequest, ChatResponse, ChatMessage, openai_service
from datetime import datetime
from core.config import supabase_admin

router = APIRouter()


class SimpleChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = None


class SimpleChatResponse(BaseModel):
    response: str
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