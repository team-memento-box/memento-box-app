from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from uuid import UUID
from core.config import supabase_admin
from datetime import datetime

router = APIRouter()

@router.get("/api/photos/{photo_id}/latest_conversation")
async def get_latest_conversation(photo_id: UUID):
    """Supabase를 사용해 특정 사진의 가장 최근 대화를 조회"""
    try:
        # Supabase에서 sessions 테이블 조회 (selected_photos 배열에 photo_id가 포함된 것 중 가장 최근)
        response = supabase_admin.table("sessions").select(
            "id, user_id, session_type, status, selected_photos, created_at"
        ).contains("selected_photos", [str(photo_id)]).order("created_at", desc=True).limit(1).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="No conversation found for this photo")
        
        session = response.data[0]
        
        # 해당 세션의 대화 내역도 함께 조회
        conversations = supabase_admin.table("conversations").select(
            "id, question_text, user_response_text, conversation_order"
        ).eq("session_id", session["id"]).order("conversation_order").execute()
        
        return JSONResponse(content={
            "session_id": session["id"],
            "photo_id": str(photo_id),
            "session_type": session["session_type"],
            "status": session["status"],
            "created_at": session["created_at"],
            "conversations": conversations.data or []
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversation: {str(e)}") 

@router.get("/api/photos/{photo_id}/{session_id}")
async def get_conversation_for_photo(photo_id: UUID, session_id: UUID):
    """특정 사진과 세션 ID에 해당하는 대화 조회"""
    try:
        # 세션 정보 조회
        session_response = supabase_admin.table("sessions").select(
            "id, user_id, session_type, status, selected_photos, created_at"
        ).eq("id", str(session_id)).single().execute()
        
        if not session_response.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_response.data
        
        # selected_photos에 해당 photo_id가 포함되어 있는지 확인
        if str(photo_id) not in session.get("selected_photos", []):
            raise HTTPException(status_code=404, detail="Photo not associated with this session")
        
        # 대화 내역 조회
        conversations = supabase_admin.table("conversations").select(
            "id, question_text, user_response_text, conversation_order, created_at"
        ).eq("session_id", str(session_id)).order("conversation_order").execute()
        
        return JSONResponse(content={
            "session_id": str(session_id),
            "photo_id": str(photo_id),
            "session_info": session,
            "conversations": conversations.data or []
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversation: {str(e)}")

@router.get("/api/sessions/{session_id}/summary_text")
async def get_session_summary_text(session_id: UUID):
    """세션의 요약 텍스트 조회 (session_reports 테이블에서)"""
    try:
        response = supabase_admin.table("session_reports").select(
            "id, summary_text, created_at"
        ).eq("session_id", str(session_id)).single().execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Session summary not found")
        
        return JSONResponse(content={
            "session_id": str(session_id),
            "summary_text": response.data["summary_text"],
            "created_at": response.data["created_at"]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary: {str(e)}")

@router.get("/api/sessions/{session_id}/conversations/history")
async def get_session_conversation_history(session_id: UUID):
    """세션의 모든 대화 내역을 시간순으로 조회"""
    try:
        response = supabase_admin.table("conversations").select(
            "id, question_text, user_response_text, conversation_order, question_type, is_cist_item, created_at"
        ).eq("session_id", str(session_id)).order("conversation_order").execute()
        
        return JSONResponse(content={
            "session_id": str(session_id),
            "conversation_history": response.data or [],
            "total_conversations": len(response.data) if response.data else 0
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversation history: {str(e)}")

@router.get("/health")
async def conversation_health_check():
    """Conversation router health check"""
    return JSONResponse(content={
        "status": "healthy",
        "message": "Conversation router updated to use Supabase",
        "endpoints": [
            "/api/photos/{photo_id}/latest_conversation",
            "/api/photos/{photo_id}/{session_id}",
            "/api/sessions/{session_id}/summary_text",
            "/api/sessions/{session_id}/conversations/history"
        ]
    })