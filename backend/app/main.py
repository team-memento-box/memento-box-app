from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import tempfile
import os
# from routers import chat, conversation  # AI 전용 라우터들

load_dotenv()
app = FastAPI(title="Memento Box AI API", description="AI 전용 API - 채팅, 이미지 분석, 음성 합성, 치매 감지")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 치매 감지 서비스 초기화
from services.dementia_detector import get_dementia_detector_service

# AI 전용 라우터 등록 (추후 활성화)
# app.include_router(chat.router, prefix="/ai", tags=["chat"])
# app.include_router(conversation.router, prefix="/ai", tags=["conversation"])
# app.include_router(chat.router, prefix="/api", tags=["llm"])
# app.include_router(family.router) # 가족 관리
# app.include_router(photo.router)
# app.include_router(speech.router)
# app.include_router(report.router)
# app.include_router(conversation.router)
# app.include_router(fish.router)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI with Nginx and PostgreSQL!"}

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}

@app.post("/audio-dementia-detection")
async def detect_dementia_from_audio(audio_file: UploadFile = File(...)):
    """
    오디오 파일을 받아서 치매 여부를 감지합니다.
    
    Args:
        audio_file: 분석할 오디오 파일 (WAV, MP3, FLAC, M4A, OGG)
    
    Returns:
        치매 감지 결과
    """
    try:
        # 1. 파일 형식 검증
        allowed_extensions = ('.wav', '.mp3', '.flac', '.m4a', '.ogg')
        if not audio_file.filename.lower().endswith(allowed_extensions):
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 오디오 형식입니다. 지원 형식: {', '.join(allowed_extensions)}"
            )
        
        # 2. 파일 크기 검증 (100MB 제한)
        content = await audio_file.read()
        if len(content) > 100 * 1024 * 1024:  # 100MB
            raise HTTPException(
                status_code=400, 
                detail="파일 크기가 너무 큽니다. 100MB 이하의 파일만 업로드 가능합니다."
            )
        
        # 3. 임시 파일로 저장
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=os.path.splitext(audio_file.filename)[1]
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # 4. 치매 감지 수행
            dementia_service = get_dementia_detector_service()
            if dementia_service is None:
                raise HTTPException(
                    status_code=500,
                    detail="치매 감지 서비스가 초기화되지 않았습니다."
                )
            
            result = await dementia_service.detect_dementia_from_audio(temp_file_path)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=500,
                    detail=result["error"]
                )
            
            return JSONResponse(content=result)
            
        finally:
            # 5. 임시 파일 정리
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        # HTTPException은 그대로 재발생
        raise
    except Exception as e:
        # 기타 예외는 500 에러로 변환
        raise HTTPException(
            status_code=500, 
            detail=f"치매 감지 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/dementia-detector/info")
async def get_detector_info():
    """치매 감지 모듈 정보를 반환합니다."""
    dementia_service = get_dementia_detector_service()
    if dementia_service is None:
        raise HTTPException(
            status_code=500,
            detail="치매 감지 서비스가 초기화되지 않았습니다."
        )
    
    return dementia_service.get_model_info()

@app.get("/api-info")
async def get_api_info():
    """API 정보를 반환합니다."""
    return {
        "service_name": "Memento Box AI API",
        "description": "AI 전용 API - 채팅, 이미지 분석, 음성 합성, 치매 감지",
        "endpoints": {
            "root": "/",
            "health": "/health",
            "dementia_detection": "/audio-dementia-detection",
            "detector_info": "/dementia-detector/info",
            "api_info": "/api-info"
        },
        "supported_audio_formats": [".wav", ".mp3", ".flac", ".m4a", ".ogg"],
        "max_file_size": "100MB"
    }