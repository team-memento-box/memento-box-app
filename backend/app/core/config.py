from pydantic_settings import BaseSettings
import secrets
from supabase import create_client, Client

class Settings(BaseSettings):
    # PostgreSQL 설정 (기존)
    # POSTGRES_USER: str = None
    # POSTGRES_PASSWORD: str = None
    # POSTGRES_DB: str = None
    
    # 데이터베이스 URL (기존)
    ASYNC_DATABASE_URL: str = None
    SYNC_DATABASE_URL: str = None
    
    # Supabase 설정
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_ISS: str
    
    # 서버 설정
    SERVER_HOST: str = "http://localhost:8000"  # 기본값, .env에서 덮어쓸 수 있음
    
    # JWT 설정
    SECRET_KEY: str
    
    # OpenAI API 설정
    OPENAI_API_KEY: str
    
    # # Azure Blob Storage 설정
    # AZURE_BLOBSTORAGE_ACCOUNT: str
    # AZURE_BLOBSTORAGE_KEY: str

    # # Azure OpenAI 설정
    # azure_openai_endpoint: str
    # azure_openai_api_version: str
    # azure_openai_max_tokens: str
    # azure_openai_deployment: str
    # azure_openai_key: str

    # # Azure Speech 설정
    # azure_speech_endpoint: str
    # azure_speech_key: str
    # azure_speech_region: str

    # JWT 인증 설정
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # # Azure Speech 서비스 설정
    # AZURE_SPEECH_KEY: str
    # AZURE_SPEECH_REGION: str

    class Config:
        env_file = ".env"  # 루트 디렉토리에 있는 .env 파일을 읽도록 지정

# 인스턴스를 만들어서 다른 곳에서 불러다 씀
settings = Settings()

# Supabase 클라이언트 초기화
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)