import os
import openai
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = "gpt-3.5-turbo"
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7


class ChatResponse(BaseModel):
    response: str
    usage: Dict[str, Any]
    model: str
    created_at: datetime


class OpenAIService:
    """OpenAI API 서비스 클래스"""
    
    def __init__(self):
        # dotenv 파일을 먼저 로드
        from dotenv import load_dotenv
        load_dotenv()
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        print(f"Debug - API Key found: {self.api_key is not None}")
        print(f"Debug - API Key length: {len(self.api_key) if self.api_key else 0}")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # OpenAI 클라이언트 초기화
        self.client = openai.OpenAI(api_key=self.api_key)
    
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """OpenAI Chat Completion API 호출"""
        try:
            # messages를 dict 형태로 변환
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            
            response = self.client.chat.completions.create(
                model=request.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            return ChatResponse(
                response=response.choices[0].message.content,
                usage=response.usage.model_dump(),
                model=response.model,
                created_at=datetime.now()
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API 호출 실패: {str(e)}")
    
    
    
    async def simple_chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """간단한 채팅 응답 생성"""
        try:
            messages = []
            
            if system_prompt:
                messages.append(ChatMessage(role="system", content=system_prompt))
            
            messages.append(ChatMessage(role="user", content=message))
            
            request = ChatRequest(
                messages=messages,
                model="gpt-3.5-turbo",
                max_tokens=500,
                temperature=0.7
            )
            
            response = await self.chat_completion(request)
            return response.response
            
        except Exception as e:
            raise Exception(f"채팅 응답 생성 실패: {str(e)}")


# 전역 서비스 인스턴스
openai_service = OpenAIService()