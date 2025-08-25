from pydantic_settings import BaseSettings
import secrets
from supabase import create_client, Client
from typing import Optional

class Settings(BaseSettings):
    # PostgreSQL 설정 (기존)
    # POSTGRES_USER: str = None
    # POSTGRES_PASSWORD: str = None
    # POSTGRES_DB: str = None
    
    # 데이터베이스 URL (기존)
    ASYNC_DATABASE_URL: Optional[str] = None
    SYNC_DATABASE_URL: Optional[str] = None
    
    # Supabase 설정
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # 서버 설정
    SERVER_HOST: str = "http://localhost:8000"  # 기본값, .env에서 덮어쓸 수 있음
    
    # JWT 설정
    SECRET_KEY: str = secrets.token_urlsafe(32)  # 기본값 설정
    
    # OpenAI API 설정
    OPENAI_API_KEY: str

    # JWT 인증 설정
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # # Azure Speech 서비스 설정
    # AZURE_SPEECH_KEY: str
    # AZURE_SPEECH_REGION: str

    class Config:
        env_file = ".env"  # 루트 디렉토리에 있는 .env 파일을 읽도록 지정
        extra = "ignore"  # 추가 필드 무시

# 인스턴스를 만들어서 다른 곳에서 불러다 씀
settings = Settings()

# Supabase 클라이언트 초기화 (익명 키 사용)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Supabase 서비스 역할 클라이언트 초기화 (관리자 권한)
supabase_admin: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)