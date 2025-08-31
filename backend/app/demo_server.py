#!/usr/bin/env python3
"""
음성 분석 API 데모 서버
Docker 없이 로컬에서 실행 가능
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import os
from datetime import datetime

# 환경 변수 로드
load_dotenv()

app = FastAPI(
    title="Memento Box Audio Analysis API",
    description="음성 기반 치매 감지 API 데모",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 음성 분석 라우터만 포함 (LangChain 의존성 제외)
try:
    from routers import audio_analysis
    app.include_router(audio_analysis.router, prefix="/api", tags=["audio-analysis"])
    AUDIO_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Audio analysis router 로드 실패: {e}")
    AUDIO_AVAILABLE = False

@app.get("/", response_class=HTMLResponse)
def read_root():
    """API 데모 홈페이지"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Memento Box Audio Analysis API</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; text-align: center; }}
            .status {{ padding: 10px; border-radius: 5px; margin: 10px 0; }}
            .success {{ background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }}
            .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }}
            .endpoint {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #007bff; }}
            .method {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-weight: bold; color: white; }}
            .post {{ background-color: #28a745; }}
            .get {{ background-color: #17a2b8; }}
            code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
            .demo-data {{ background-color: #e9ecef; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎤 Memento Box Audio Analysis API</h1>
            <p><strong>서버 시작 시간:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="status {'success' if AUDIO_AVAILABLE else 'warning'}">
                <strong>{'✅ 음성 분석 API 사용 가능' if AUDIO_AVAILABLE else '⚠️ 음성 분석 API 로딩 실패'}</strong>
            </div>

            <h2>📋 사용 가능한 API 엔드포인트</h2>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/docs</strong> - Swagger UI (대화형 API 문서)
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/health</strong> - 서버 상태 확인
            </div>

            {''.join([f'''
            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/audio-analysis/session/{{session_id}}/full-analysis</strong><br>
                전체 음성 분석 파이프라인 (병합 → 특징추출 → 치매감지 → DB저장)
            </div>

            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/audio-analysis/audio-dementia-detector</strong><br>
                음성에서 치매 감지 (114개 세그먼트 분석)
            </div>

            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/audio-analysis/session/{{session_id}}/audio-urls-only</strong><br>
                세션의 오디오 URL 목록 조회
            </div>

            <div class="demo-data">
                <h3>🧪 테스트 데이터</h3>
                <p><strong>테스트 세션 ID:</strong> <code>ac259fb9-3fcf-4bf0-9e0e-41651f187d8c</code></p>
                <p>이 세션에는 735초 분량의 실제 음성 데이터가 있습니다.</p>
            </div>
            ''' if AUDIO_AVAILABLE else '''
            <div class="status warning">
                음성 분석 기능을 사용하려면 필요한 의존성을 설치하세요:<br>
                <code>pip install supabase librosa scikit-learn noisereduce</code>
            </div>
            '''])}

            <h2>🚀 빠른 시작</h2>
            <ol>
                <li><strong>API 문서:</strong> <a href="/docs" target="_blank">http://localhost:8000/docs</a></li>
                <li><strong>헬스 체크:</strong> <a href="/health" target="_blank">http://localhost:8000/health</a></li>
                {'<li><strong>테스트:</strong> /docs에서 full-analysis API 사용해보기</li>' if AUDIO_AVAILABLE else ''}
            </ol>
            
            <h2>📊 성능 개선 내역</h2>
            <ul>
                <li>세그먼트 수: 8개 → <strong>114개 (1,325% 증가)</strong></li>
                <li>동적 오디오 슬라이싱: 20초 단위, 1초 오버랩</li>
                <li>데이터 증강: 0.8x, 1.2x 속도 변형</li>
                <li>최소 1분 오디오 제한으로 진단 정확도 향상</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return html_content

@app.get("/health")
def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "audio_analysis_available": AUDIO_AVAILABLE,
        "supabase_configured": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Memento Box Audio Analysis API 서버 시작...")
    print("📖 API 문서: http://localhost:8000/docs")
    print("🏠 홈페이지: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)