from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.database import get_db
from db.models.user import User
from core.config import settings, supabase_admin

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
        # Supabase JWT 토큰 디코딩 (HS256 알고리즘과 JWT_SECRET 사용)
        payload = jwt.decode(
            token, 
            settings.SUPABASE_JWT_SECRET, 
            algorithms=["HS256"],
            audience="authenticated",
            issuer=settings.SUPABASE_ISS
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
            
        # Supabase에서 사용자 정보 조회
        user_response = supabase_admin.auth.admin.get_user_by_id(user_id)
        
        if not user_response or not user_response.user:
            raise credentials_exception
            
        return {
            "id": user_response.user.id,
            "email": user_response.user.email,
            "created_at": user_response.user.created_at,
            "user_metadata": user_response.user.user_metadata,
            "app_metadata": user_response.user.app_metadata
        }
        
    except JWTError as e:
        print(f"Supabase JWT 검증 실패: {e}")
        raise credentials_exception
    except Exception as e:
        print(f"Supabase 사용자 조회 실패: {e}")
        raise credentials_exception

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
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """현재 인증된 사용자 정보 조회 (기존 JWT 시스템)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # JWT 토큰 디코딩
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 사용자 정보 조회
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user 