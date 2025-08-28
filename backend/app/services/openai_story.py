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
    
    async def generate_story(self, conversation_data: List[Dict]) -> str:
        """대화 데이터를 기반으로 스토리 생성"""
        try:
            # 대화 데이터를 텍스트로 변환
            conversation_text = ""
            for turn in conversation_data:
                if "question" in turn and "answer" in turn:
                    conversation_text += f"질문: {turn['question']}\n답변: {turn['answer']}\n\n"
            
            # 스토리 생성 프롬프트
            prompt = f"""
다음 대화를 바탕으로 따뜻하고 감동적인 추억 이야기를 만들어주세요.

대화 내용:
{conversation_text}

요구사항:
1. 3-5개 문단으로 구성
2. 감정적이고 따뜻한 톤
3. 대화에서 나온 구체적인 내용들을 포함
4. 한국어로 작성
5. 1000자 이내

추억 이야기:
"""
            
            messages = [ChatMessage(role="user", content=prompt)]
            request = ChatRequest(
                messages=messages,
                model="gpt-3.5-turbo",
                max_tokens=1200,
                temperature=0.8
            )
            
            response = await self.chat_completion(request)
            return response.response
            
        except Exception as e:
            raise Exception(f"스토리 생성 실패: {str(e)}")
    
    async def generate_grandparent_story(self, conversations: List[Dict]) -> str:
        """대화 기록을 할머니/할아버지가 손자/손녀에게 들려주는 옛날 이야기 스타일로 요약"""
        try:
            # 대화 데이터를 시간순으로 정렬하고 텍스트로 변환
            sorted_conversations = sorted(conversations, key=lambda x: x.get('conversation_order', 0))
            
            conversation_text = ""
            for conv in sorted_conversations:
                question = conv.get('question_text', '')
                response = conv.get('user_response_text', '')
                if question and response:
                    conversation_text += f"질문: {question}\n답변: {response}\n\n"
            
            # 할머니/할아버지 스타일 프롬프트
            prompt = f"""
다음 대화 내용을 바탕으로 할머니나 할아버지가 손자, 손녀에게 옛날 이야기를 들려주는 것처럼 따뜻하고 정감 있는 이야기로 만들어주세요.

대화 내용:
{conversation_text}

요구사항:
1. "우리 ○○이가..." 또는 "예전에 말이야..." 같은 할머니/할아버지 말투 사용
2. 대화에서 나온 추억들을 하나의 연결된 이야기로 구성
3. 따뜻하고 사랑스러운 톤으로 작성
4. 3-4개 문단으로 구성 (너무 길지 않게)
5. 한국어로 자연스럽게 작성
6. 800자 이내
7. 실제 할머니/할아버지가 말하는 것처럼 구어체 사용

할머니/할아버지의 이야기:
"""
            
            messages = [ChatMessage(role="user", content=prompt)]
            request = ChatRequest(
                messages=messages,
                model="gpt-4",
                max_tokens=1000,
                temperature=0.8
            )
            
            response = await self.chat_completion(request)
            return response.response
            
        except Exception as e:
            raise Exception(f"할머니 이야기 생성 실패: {str(e)}")
    
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