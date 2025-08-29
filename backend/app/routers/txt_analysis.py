from fastapi import APIRouter, HTTPException
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from core.config import supabase
from services.txt_analyzer import complete_speech_analysis

router = APIRouter(
    tags=["Text Analysis"]
)

class AllResponseData(BaseModel):
    user_id: UUID
    session_id: UUID
    all_response_text: str

class AnalysisOut(BaseModel):
    user_id: UUID
    session_id: UUID
    lexical_diversity: float
    mlu: float
    demonstrative_ratio: float
    speech_rate: float
    
class AnalysisResult(BaseModel):
    id: UUID
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    lexical_diversity: float
    mlu: float
    demonstrative_ratio: float
    speech_rate: float
    created_at: str

@router.get("/user/{user_id}/session/{session_id}", response_model=List[AllResponseData])
async def get_all_user_response_texts(user_id:UUID, session_id: UUID):
    """
    특정 사용자의 특정 대화에 대한 사용자 답변 조회
    """
    try:
        response = supabase.table("conversations")\
            .select("user_id, session_id, user_response_text")\
            .eq("user_id", str(user_id))\
            .eq("session_id", str(session_id))\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # 모든 user_response_text를 하나로 합치기
        total_response_texts = ""
        for item in response.data:
            if item.get('user_response_text'):
                total_response_texts += item['user_response_text'] + " "

        # 통합된 데이터 반환
        unified_data = AllResponseData(
            user_id=user_id,
            session_id=session_id,
            all_response_text=total_response_texts.strip()
        )
        
        return [unified_data]
    
    except Exception as error:
            print(f"Error fetching all user response texts: {error}")
            return None


@router.post("/", response_model=AnalysisOut)
async def analyze_and_save_scoring(analysis_request: AllResponseData):
    """
    텍스트를 분석하고 결과를 Supabase에 저장
    """
    try:
        if not analysis_request:
            raise HTTPException(status_code=404, detail="No user response texts found")
    

        # 텍스트 분석 수행
        analysis_result = complete_speech_analysis(analysis_request.all_response_text)
        
        if "categorical_score" not in analysis_result or "ai_scoring" not in analysis_result["categorical_score"]:
            raise HTTPException(status_code=500, detail="Analysis failed: No AI scoring result")
            
        ai_scoring = analysis_result["categorical_score"]["ai_scoring"]
        raw_data = analysis_result["categorical_score"]["raw_data"]
        
        # Supabase에 결과 저장
        insert_data = {
            "user_id": str(analysis_request.user_id),
            "session_id": str(analysis_request.session_id),
            "lexical_diversity": ai_scoring["lexical_diversity"],
            "mlu": ai_scoring["mlu"], 
            "demonstrative_ratio": ai_scoring["demonstrative_ratio"],
            "speech_rate": ai_scoring["speech_rate"],
        }
        
        if analysis_request.session_id:
            insert_data["session_id"] = str(analysis_request.session_id)
        if analysis_request.user_id:
            insert_data["user_id"] = str(analysis_request.user_id)
            
        response = supabase.table("session_text_analysis").insert(insert_data).execute()
        
        if response.data:
            return AnalysisOut(**response.data[0])
        else:
            raise HTTPException(status_code=500, detail="Failed to save analysis to database")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/user/{user_id}", response_model=List[AnalysisResult])
async def get_analysis_by_user(user_id: UUID, session_id: Optional[UUID] = None):
    """
    user_id로 분석 결과 조회
    - session_id가 없으면: 해당 사용자의 모든 분석 결과 조회
    - session_id가 있으면: 특정 세션의 분석 결과만 조회
    """
    try:
        query = supabase.table("session_text_analysis")\
            .select("*")\
            .eq("user_id", str(user_id))
        
        # session_id가 제공된 경우 추가 필터링
        if session_id:
            query = query.eq("session_id", str(session_id))
        
        response = query.execute()
        
        if response.data:
            return [AnalysisResult(**item) for item in response.data]
        else:
            raise HTTPException(status_code=404, detail="Analysis not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
