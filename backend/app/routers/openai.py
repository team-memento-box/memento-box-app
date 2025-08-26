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
    """세션 ID로 Supabase에서 대화 기록을 가져와서 할머니/할아버지 스타일 이야기로 변환"""
    try:
        # Supabase에서 해당 세션의 대화 기록 가져오기 (Service Role Key 사용)
        print(f"Debug - Searching for session_id: {request.session_id}")
        conversations_response = supabase_admin.table("conversations").select(
            "conversation_order, question_text, user_response_text"
        ).eq("session_id", request.session_id).order("conversation_order").execute()
        
        print(f"Debug - Query result: {conversations_response.data}")
        print(f"Debug - Number of conversations found: {len(conversations_response.data) if conversations_response.data else 0}")
        
        if not conversations_response.data:
            raise HTTPException(status_code=404, detail="해당 세션의 대화 기록을 찾을 수 없습니다.")
        
        # 할머니/할아버지 스타일 이야기 생성
        story = await service.generate_grandparent_story(conversations_response.data)
        
        return GrandparentStoryResponse(
            story=story,
            session_id=request.session_id,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
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