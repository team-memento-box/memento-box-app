from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from core.config import settings, supabase, supabase_admin
import logging
from datetime import datetime

# OAuth2 토큰 URL 설정 (호환성을 위해 유지)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# 로깅 설정
logger = logging.getLogger(__name__)

def log_auth_debug(message: str, **kwargs):
    """인증 관련 디버깅 로그 출력"""
    timestamp = datetime.now().isoformat()
    log_message = f"🔐 [AUTH_DEBUG] {timestamp} | {message}"
    if kwargs:
        log_message += f" | {kwargs}"
    print(log_message)
    logger.info(log_message)

async def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """Supabase 클라이언트를 사용하여 JWT 토큰 검증 및 사용자 정보 반환"""
    log_auth_debug("JWT 토큰 검증 시작", token_length=len(token) if token else 0, token_prefix=token[:10] if token and len(token) > 10 else token)
    
    try:
        # Supabase 클라이언트의 get_user 메서드로 토큰 검증
        log_auth_debug("Supabase get_user API 호출 시작")
        response = supabase.auth.get_user(token)
        log_auth_debug("Supabase get_user API 응답 받음", user_exists=response.user is not None)
        
        if not response.user:
            log_auth_debug("JWT 토큰 검증 실패 - 사용자 정보 없음")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 인증 토큰입니다",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = response.user
        user_info = {
            "id": user.id,
            "email": user.email or "",
            "created_at": user.created_at,
            "user_metadata": user.user_metadata or {},
            "app_metadata": user.app_metadata or {}
        }
        log_auth_debug("JWT 토큰 검증 성공", user_id=user.id, email=user.email)
        return user_info
        
    except HTTPException:
        # FastAPI HTTPException은 그대로 전파
        log_auth_debug("HTTPException 발생으로 인증 실패")
        raise
    except Exception as e:
        log_auth_debug("예외 발생으로 인증 실패", error_type=type(e).__name__, error_message=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"인증 토큰 검증에 실패했습니다: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_supabase_user(token: str) -> Dict[str, Any]:
    """토큰에서 Bearer 접두사를 제거하여 Supabase 사용자 정보 반환"""
    log_auth_debug("get_supabase_user 호출", has_token=token is not None, token_length=len(token) if token else 0)
    
    if not token:
        log_auth_debug("토큰이 없어서 인증 실패")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 없습니다"
        )
    
    # Bearer 토큰에서 실제 토큰 부분만 추출
    original_token = token
    if token.startswith("Bearer "):
        token = token[7:]
        log_auth_debug("Bearer 접두사 제거", original_length=len(original_token), new_length=len(token))
    else:
        log_auth_debug("Bearer 접두사 없음", token_prefix=token[:10] if len(token) > 10 else token)
    
    return await verify_supabase_jwt(token)

async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> Dict[str, Any]:
    """현재 인증된 사용자 정보 조회 (Supabase Python 클라이언트 사용)"""
    log_auth_debug("get_current_user 의존성 주입 호출", dependency_type="oauth2_scheme")
    return await get_supabase_user(token)

async def get_current_user_from_header(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Authorization 헤더에서 JWT를 추출하여 Supabase 사용자 정보 조회"""
    log_auth_debug("get_current_user_from_header 의존성 주입 호출", 
                   dependency_type="Header",
                   has_authorization=authorization is not None,
                   auth_header_length=len(authorization) if authorization else 0)
    
    if not authorization:
        log_auth_debug("Authorization 헤더가 없어서 인증 실패")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization 헤더가 없습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Bearer 토큰 형식 확인
    if not authorization.startswith("Bearer "):
        log_auth_debug("잘못된 Authorization 헤더 형식", 
                       header_prefix=authorization[:20] if len(authorization) > 20 else authorization)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 Authorization 헤더 형식입니다. 'Bearer <token>' 형식이어야 합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization[7:]  # "Bearer " 제거
    log_auth_debug("Authorization 헤더에서 토큰 추출 완료", 
                   original_length=len(authorization), 
                   token_length=len(token))
    return await get_supabase_user(token) 