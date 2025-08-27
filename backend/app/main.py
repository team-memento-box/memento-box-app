from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import json
import os
from datetime import datetime
from services.dialogue_workflow import DialogueWorkflow, WorkflowInput
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

# LangGraph 대화 워크플로우 초기화
workflow = DialogueWorkflow()

@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(websocket: WebSocket, conversation_id: str):
    """실시간 대화를 위한 WebSocket 엔드포인트"""
    await websocket.accept()
    print(f"WebSocket connection established for conversation: {conversation_id}")
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 메시지 검증
            user_message = message_data.get("message", "").strip()
            if not user_message:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "메시지가 비어있습니다.",
                    "conversation_id": conversation_id
                }))
                continue
            
            print(f"Received message: {user_message} from user: {message_data.get('user_id', 'unknown')}")
            
            # 입력 데이터 구성
            workflow_input = WorkflowInput(
                conversation_id=conversation_id,
                user_id=message_data.get("user_id", "temp_user"),
                user_message=user_message,
                photo_context=message_data.get("photo_context", {})
            )
            
            # 처리 시작 알림
            await websocket.send_text(json.dumps({
                "type": "processing",
                "message": "답변을 생성하고 있습니다...",
                "conversation_id": conversation_id
            }))
            
            # LangGraph 워크플로우 실행
            response = await workflow.process_message(workflow_input)
            
            # 응답 전송
            await websocket.send_text(json.dumps({
                "type": "response",
                "data": response,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False))
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for conversation: {conversation_id}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error for conversation {conversation_id}: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "메시지 형식이 올바르지 않습니다.",
                "conversation_id": conversation_id
            }))
        except:
            pass
    except Exception as e:
        print(f"WebSocket error for conversation {conversation_id}: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                "conversation_id": conversation_id,
                "error_details": str(e) if app.debug else None
            }))
        except:
            pass

@app.get("/")
def read_root():
    return {"message": "Memento Box AI API with WebSocket & LangGraph"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "supabase_configured": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))
    }