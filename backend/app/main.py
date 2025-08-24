from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
# from routers import chat, conversation  # AI 전용 라우터들

load_dotenv()
app = FastAPI(title="Memento Box AI API", description="AI 전용 API - 채팅, 이미지 분석, 음성 합성")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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