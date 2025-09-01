from dotenv import load_dotenv
import os
import base64
import json

from core.config import settings
from langchain_openai import ChatOpenAI

class ImageAnalyzer:
    """GPT-4o를 사용한 이미지 분석"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        # LangSmith 설정
        self._setup_langsmith()
        
        # LangSmith 메타데이터 설정
        langsmith_tracing = settings.LANGSMITH_TRACING and settings.LANGSMITH_TRACING.lower() == "true"
        langsmith_metadata = {
            "service": "image_analyzer",
            "version": "1.0",
            "environment": os.getenv("ENVIRONMENT", "development")
        }

        self.client = ChatOpenAI(
            model="gpt-4o",
            api_key=self.api_key,
            temperature=0.3,
            max_tokens=1000,
            metadata=langsmith_metadata if langsmith_tracing else None
        )
    
    def _setup_langsmith(self):
        """LangSmith 추적 설정"""
        # LangSmith 환경변수 설정 (LangChain이 자동으로 읽도록)
        if settings.LANGSMITH_TRACING:
            os.environ["LANGSMITH_TRACING"] = settings.LANGSMITH_TRACING
        if settings.LANGSMITH_API_KEY:
            os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
        if settings.LANGSMITH_PROJECT:
            os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
        if settings.LANGSMITH_ENDPOINT:
            os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    
    def analyze_image(self, image_path):
        """이미지 분석"""
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception:
            return None
        
        try:
            from langchain_core.messages import HumanMessage
            
            messages = [
                HumanMessage(content=[
                    {
                        "type": "text",
                        "text": """이미지를 분석해서 JSON으로 답해주세요:
{
    "caption": "전체 설명",
    "dense_captions": ["세부 설명1", "세부 설명2"],
    "mood": "분위기",
    "time_period": "시대",
    "key_objects": ["객체1", "객체2"],
    "people_description": "인물 설명",
    "people_count": 숫자,
    "time_of_day": "시간대"
}"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ])
            ]
            
            response = self.client.invoke(messages)
            response_text = response.content
            
            # JSON 추출
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "{" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                response_text = response_text[json_start:json_end]
            
            return json.loads(response_text)
            
        except Exception:
            return None