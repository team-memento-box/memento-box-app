from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import json
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
            
            # 입력 데이터 구성
            workflow_input = WorkflowInput(
                conversation_id=conversation_id,
                user_id=message_data.get("user_id", "temp_user"),
                user_message=message_data.get("message", ""),
                photo_context=message_data.get("photo_context", {})
            )
            
            # LangGraph 워크플로우 실행
            response = await workflow.process_message(workflow_input)
            
            # 응답 전송
            await websocket.send_text(json.dumps({
                "type": "response",
                "data": response,
                "conversation_id": conversation_id
            }))
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for conversation: {conversation_id}")
    except Exception as e:
        print(f"WebSocket error for conversation {conversation_id}: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "처리 중 오류가 발생했습니다.",
                "conversation_id": conversation_id
            }))
        except:
            pass

@app.get("/")
def read_root():
    return {"message": "Memento Box AI API with WebSocket & LangGraph"}