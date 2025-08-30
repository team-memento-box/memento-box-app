#!/usr/bin/env python3
"""
Audio Analysis Router for Memento-Box
음성 분석 관련 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
import uuid
from pydantic import BaseModel, Field
import asyncio

# Supabase 클라이언트
from supabase import create_client, Client
import os

router = APIRouter(
    prefix="/audio-analysis",
    tags=["audio-analysis"],
    responses={404: {"description": "Not found"}},
)

# Supabase 클라이언트 설정
def get_supabase_client() -> Client:
    """Supabase 클라이언트를 반환합니다."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase 설정이 누락되었습니다."
        )
    
    return create_client(url, key)

# Request/Response 모델들
class SessionAudioRequest(BaseModel):
    """세션 오디오 요청 모델"""
    session_id: str = Field(..., description="세션 ID")

class AudioFileInfo(BaseModel):
    """오디오 파일 정보 모델"""
    conversation_id: str
    conversation_order: int
    question_text: str
    user_response_audio_url: Optional[str]
    user_response_text: Optional[str]
    question_type: str
    created_at: str

class SessionAudioResponse(BaseModel):
    """세션 오디오 응답 모델"""
    session_id: str
    total_conversations: int
    audio_files_count: int
    audio_files: List[AudioFileInfo]

@router.get("/session/{session_id}/audio-files", response_model=SessionAudioResponse)
async def get_session_audio_files(
    session_id: str,
    supabase: Client = Depends(get_supabase_client)
) -> SessionAudioResponse:
    """
    세션 ID로 해당 세션의 모든 사용자 응답 오디오 파일 URL을 가져옵니다.
    
    Args:
        session_id: 조회할 세션 ID
        
    Returns:
        SessionAudioResponse: 세션의 오디오 파일 정보들
    """
    try:
        # UUID 형식 검증
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 세션 ID 형식입니다: {session_id}"
        )
    
    try:
        # 세션의 모든 대화 조회 (conversation_order 순서대로)
        response = supabase.table("conversations").select(
            "id, conversation_order, question_text, user_response_text, "
            "user_response_audio_url, question_type, created_at"
        ).eq(
            "session_id", session_id
        ).order(
            "conversation_order", desc=False
        ).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"세션 ID {session_id}에 대한 대화를 찾을 수 없습니다."
            )
        
        conversations = response.data
        
        # 오디오 파일 정보 구성
        audio_files = []
        audio_count = 0
        
        for conv in conversations:
            audio_info = AudioFileInfo(
                conversation_id=str(conv["id"]),
                conversation_order=conv["conversation_order"],
                question_text=conv["question_text"],
                user_response_audio_url=conv["user_response_audio_url"],
                user_response_text=conv["user_response_text"],
                question_type=conv["question_type"],
                created_at=conv["created_at"]
            )
            
            audio_files.append(audio_info)
            
            # 오디오 URL이 있는 경우만 카운트
            if conv["user_response_audio_url"]:
                audio_count += 1
        
        return SessionAudioResponse(
            session_id=session_id,
            total_conversations=len(conversations),
            audio_files_count=audio_count,
            audio_files=audio_files
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/session/audio-files", response_model=SessionAudioResponse)
async def get_session_audio_files_post(
    request: SessionAudioRequest,
    supabase: Client = Depends(get_supabase_client)
) -> SessionAudioResponse:
    """
    POST 방식으로 세션 오디오 파일들을 조회합니다.
    (프론트엔드에서 body로 session_id를 전달하는 경우)
    
    Args:
        request: 세션 오디오 요청 데이터
        
    Returns:
        SessionAudioResponse: 세션의 오디오 파일 정보들
    """
    return await get_session_audio_files(request.session_id, supabase)

@router.get("/session/{session_id}/audio-urls-only")
async def get_session_audio_urls_only(
    session_id: str,
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    세션의 오디오 URL만 간단히 반환합니다. (음성 분석 모듈용)
    
    Args:
        session_id: 조회할 세션 ID
        
    Returns:
        Dict: 오디오 URL 리스트와 메타데이터
    """
    try:
        # UUID 형식 검증
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 세션 ID 형식입니다: {session_id}"
        )
    
    try:
        # user_response_audio_url이 NULL이 아닌 대화만 조회
        response = supabase.table("conversations").select(
            "id, conversation_order, user_response_audio_url"
        ).eq(
            "session_id", session_id
        ).not_.is_(
            "user_response_audio_url", "null"
        ).order(
            "conversation_order", desc=False
        ).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"세션 ID {session_id}에 오디오 파일이 있는 대화를 찾을 수 없습니다."
            )
        
        conversations = response.data
        
        # 오디오 URL만 추출
        audio_urls = [
            {
                "conversation_id": conv["id"],
                "conversation_order": conv["conversation_order"],
                "audio_url": conv["user_response_audio_url"]
            }
            for conv in conversations
        ]
        
        return {
            "session_id": session_id,
            "audio_files_count": len(audio_urls),
            "audio_urls": audio_urls
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """음성 분석 라우터 헬스 체크"""
    return {
        "status": "healthy",
        "service": "audio-analysis",
        "message": "Audio Analysis API is running"
    }