from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import auth  # 현재 Supabase로 마이그레이션된 라우터만 import
# from routers import family, photo, speech, conversation, report, chat, fish  # 추후 마이그레이션 예정

#, photo
#from routers import turn,  photo,conversation

load_dotenv()
app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router) # 인증관리
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