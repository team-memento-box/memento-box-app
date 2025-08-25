from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
import jwt
from core.config import settings, supabase, supabase_admin

# 비밀번호 해싱을 위한 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 토큰 URL 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# JWT 설정
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """Supabase JWT 토큰 검증 및 사용자 정보 반환"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Supabase 인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        print(f"🔐 JWT 토큰 검증 시작: {token[:50]}...")
        
        # Supabase Admin 클라이언트로 토큰 검증
        # get_user() 메서드를 사용하여 JWT 토큰 검증
        user_response = supabase_admin.auth.get_user(token)
        
        if not user_response or not user_response.user:
            print(f"❌ 사용자 정보 없음: user_response={user_response}")
            raise credentials_exception
            
        user = user_response.user
        print(f"✅ JWT 검증 성공: user_id={user.id}, email={user.email}")
        
        return {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at,
            "user_metadata": user.user_metadata or {},
            "app_metadata": user.app_metadata or {}
        }
        
    except Exception as e:
        error_msg = f"Supabase JWT 검증 실패: {type(e).__name__}: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(f"📋 상세 오류: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_supabase_user(token: str) -> Dict[str, Any]:
    """헤더에서 토큰을 추출하여 Supabase 사용자 정보 반환"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 없습니다"
        )
    
    # Bearer 토큰에서 실제 토큰 부분만 추출
    if token.startswith("Bearer "):
        token = token[7:]
    
    return await verify_supabase_jwt(token)

async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> Dict[str, Any]:
    """현재 인증된 사용자 정보 조회 (Supabase JWT 시스템)"""
    return await get_supabase_user(token) 