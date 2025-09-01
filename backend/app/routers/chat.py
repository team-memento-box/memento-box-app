from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import json
import os

# Legacy chat router - most functionality moved to WebSocket endpoint in main.py
# Keeping minimal test endpoints for development
router = APIRouter(
    prefix="/chat",
    tags=["llm-legacy"]
)

@router.get("/deprecated")
async def deprecated_endpoint():
    """
    Legacy chat endpoints have been moved to WebSocket implementation.
    Use WebSocket endpoint: /ws/chat/{conversation_id}
    """
    return JSONResponse(content={
        "message": "This endpoint is deprecated. Use WebSocket endpoint: /ws/chat/{conversation_id}",
        "websocket_endpoint": "/ws/chat/{conversation_id}",
        "documentation": "See main.py for WebSocket implementation"
    })

@router.get("/health")
async def legacy_health_check():
    """Simple health check for legacy chat router"""
    return JSONResponse(content={
        "status": "deprecated",
        "message": "Legacy chat endpoints. Use WebSocket at /ws/chat/{conversation_id}",
        "active_endpoints": ["/deprecated", "/health"]
    })