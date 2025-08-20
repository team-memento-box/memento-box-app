from fastapi import APIRouter, Request, Body, Depends, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
import requests
from core.config import supabase, settings
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/kakao/login")
async def kakao_login():
    """카카오 OAuth 로그인 URL 생성"""
    try:
        response = supabase.auth.sign_in_with_oauth({
            "provider": "kakao",
            "options": {
                "redirect_to": f"{settings.SERVER_HOST}/auth/kakao/callback"
            }
        })
        return {"login_url": response.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth URL 생성 실패: {str(e)}")

@router.get("/kakao/callback")
async def kakao_callback(code: str = None, error: str = None):
    """카카오 OAuth 콜백 처리"""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth 에러: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="인증 코드가 없습니다")
    
    try:
        # Supabase에서 OAuth 세션 가져오기
        response = supabase.auth.exchange_code_for_session({
            "auth_code": code
        })
        
        if response.user:
            # users 테이블에서 사용자 정보 조회/생성
            profile_data = supabase.table("users").select("*").eq("id", response.user.id).execute()
            
            if len(profile_data.data) == 0:
                # 새 사용자 - users 테이블에 기본 정보 추가
                new_profile = {
                    "id": response.user.id,
                    "email": response.user.email,
                    "full_name": response.user.user_metadata.get("name", ""),
                    "profile_image_url": response.user.user_metadata.get("avatar_url", ""),
                    "onboarding_completed": False,
                    "privacy_consent": False,
                    "terms_accepted": False,
                    "notification_enabled": True
                }
                supabase.table("users").insert(new_profile).execute()
                
                return JSONResponse(content={
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "full_name": new_profile["full_name"],
                    "profile_image_url": new_profile["profile_image_url"],
                    "is_registered": False,
                    "access_token": response.session.access_token
                })
            else:
                # 기존 사용자
                profile = profile_data.data[0]
                return JSONResponse(content={
                    "user_id": profile["id"],
                    "email": profile["email"],
                    "full_name": profile["full_name"],
                    "birth_date": profile["birth_date"],
                    "gender": profile["gender"],
                    "phone": profile["phone"],
                    "profile_image_url": profile["profile_image_url"],
                    "onboarding_completed": profile["onboarding_completed"],
                    "is_registered": profile["onboarding_completed"],
                    "access_token": response.session.access_token
                })
        else:
            raise HTTPException(status_code=400, detail="사용자 정보를 가져올 수 없습니다")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"인증 처리 중 오류: {str(e)}")

@router.post("/login")
async def login(request: Request):
    """토큰을 사용한 로그인 검증"""
    data = await request.json()
    access_token = data.get("access_token")
    
    if not access_token:
        raise HTTPException(status_code=400, detail="액세스 토큰이 필요합니다")
    
    try:
        # Supabase에서 토큰 검증
        response = supabase.auth.get_user(access_token)
        
        if response.user:
            # users 테이블에서 사용자 정보 조회
            profile_data = supabase.table("users").select("*").eq("id", response.user.id).execute()
            
            if len(profile_data.data) > 0:
                profile = profile_data.data[0]
                return JSONResponse(content={
                    "user_id": profile["id"],
                    "email": profile["email"],
                    "full_name": profile["full_name"],
                    "birth_date": profile["birth_date"],
                    "gender": profile["gender"],
                    "phone": profile["phone"],
                    "profile_image_url": profile["profile_image_url"],
                    "onboarding_completed": profile["onboarding_completed"],
                    "is_registered": profile["onboarding_completed"]
                })
            else:
                raise HTTPException(status_code=404, detail="사용자 프로필을 찾을 수 없습니다")
        else:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"토큰 검증 중 오류: {str(e)}")

@router.post("/register_user")
async def register_user(user_data: dict = Body(...)):
    """사용자 프로필 정보 업데이트 (온보딩 완료)"""
    user_id = user_data.get("user_id")
    if not user_id:
        return JSONResponse({"error": "user_id가 필요합니다"}, status_code=400)
    
    try:
        # users 테이블에서 사용자 조회
        profile_data = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if len(profile_data.data) == 0:
            return JSONResponse({"error": "사용자를 찾을 수 없습니다"}, status_code=404)
        
        # 프로필 정보 업데이트
        update_data = {
            "full_name": user_data.get("full_name"),
            "birth_date": user_data.get("birth_date"),
            "gender": user_data.get("gender"),
            "phone": user_data.get("phone"),
            "profile_image_url": user_data.get("profile_image_url"),
            "onboarding_completed": True,
            "privacy_consent": user_data.get("privacy_consent", True),
            "terms_accepted": user_data.get("terms_accepted", True),
            "notification_enabled": user_data.get("notification_enabled", True),
            "updated_at": datetime.now().isoformat()
        }
        
        # None 값 제거
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        result = supabase.table("users").update(update_data).eq("id", user_id).execute()
        
        if len(result.data) > 0:
            return JSONResponse({"message": "사용자 정보가 저장되었습니다"})
        else:
            return JSONResponse({"error": "사용자 정보 업데이트에 실패했습니다"}, status_code=500)
            
    except Exception as e:
        return JSONResponse({"error": f"서버 오류: {str(e)}"}, status_code=500)

@router.delete("/delete_user/{user_id}")
async def delete_user(user_id: str):
    """사용자 계정 삭제"""
    try:
        # users 테이블에서 사용자 삭제
        result = supabase.table("users").delete().eq("id", user_id).execute()
        
        if len(result.data) > 0:
            # Supabase Auth에서도 사용자 삭제 (관리자 권한 필요)
            # 실제로는 사용자가 직접 계정 삭제하는 것이 권장됨
            return {"message": f"사용자 {user_id}가 삭제되었습니다."}
        else:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 중 오류: {str(e)}")

@router.post("/logout")
async def logout(request: Request):
    """로그아웃"""
    data = await request.json()
    access_token = data.get("access_token")
    
    if not access_token:
        raise HTTPException(status_code=400, detail="액세스 토큰이 필요합니다")
    
    try:
        # Supabase에서 세션 종료
        supabase.auth.sign_out()
        return {"message": "로그아웃되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그아웃 중 오류: {str(e)}") 
    

