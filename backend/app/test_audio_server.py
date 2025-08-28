#!/usr/bin/env python3
"""
음성 치매 감지 기능만 테스트하는 간단한 서버
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os

app = FastAPI(title="Audio Dementia Detection Test Server")

@app.get("/")
def read_root():
    return {"message": "Audio Dementia Detection Test Server"}

@app.post("/test-audio-dementia")
async def test_audio_dementia(audio_file: UploadFile = File(...)):
    """
    오디오 파일을 받아서 치매 여부를 감지합니다 (테스트용)
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
            # 4. 치매 감지 서비스 직접 호출
            from services.audio_dementia_detector import DementiaDetector
            
            # 상대 경로로 모델 디렉토리 지정
            detector = DementiaDetector(model_dir="services/models")
            result = await detector.detect_dementia_from_audio(temp_file_path)
            
            return JSONResponse(content=result)
            
        finally:
            # 5. 임시 파일 정리
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        # 기타 예외는 500 에러로 변환
        raise HTTPException(
            status_code=500, 
            detail=f"치매 감지 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/detector-info")
async def get_detector_info():
    """치매 감지 모듈 정보를 반환합니다."""
    try:
        from services.audio_dementia_detector import DementiaDetector
        detector = DementiaDetector(model_dir="services/models")
        return detector.get_model_info()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"모듈 정보 조회 실패: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)