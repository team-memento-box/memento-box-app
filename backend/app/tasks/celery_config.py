import os
from supabase import create_client, Client

# 환경변수에서 직접 가져오기 (Pydantic Settings 우회)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Supabase 클라이언트 초기화
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")