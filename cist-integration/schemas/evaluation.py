"""
CIST 평가 관련 Pydantic 스키마
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

from models.cist_items import CognitiveDomain


class EvaluationStatus(str, Enum):
    """평가 상태"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    SKIPPED = "skipped"


class ItemResponse(BaseModel):
    """개별 문항 응답"""
    item_id: str
    user_response: str
    raw_score: int = Field(ge=0)
    max_score: int = Field(gt=0)
    evaluation_details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    status: EvaluationStatus = EvaluationStatus.NOT_STARTED


class DomainScore(BaseModel):
    """인지 영역별 점수"""
    domain: CognitiveDomain
    total_score: int = Field(ge=0)
    max_score: int = Field(gt=0)
    percentage: float = Field(ge=0.0, le=100.0)
    items_completed: int = Field(ge=0)
    items_total: int = Field(gt=0)


class CISTEvaluation(BaseModel):
    """CIST 평가 전체 결과"""
    conversation_id: str
    user_id: Optional[str] = None
    
    # 개별 문항 응답들
    item_responses: Dict[str, ItemResponse] = Field(default_factory=dict)
    
    # 영역별 점수
    domain_scores: Dict[CognitiveDomain, DomainScore] = Field(default_factory=dict)
    
    # 전체 점수
    total_score: int = Field(ge=0, default=0)
    max_total_score: int = Field(gt=0, default=22)  # 음성 대화로 평가 가능한 최대 점수
    total_percentage: float = Field(ge=0.0, le=100.0, default=0.0)
    
    # 메타 정보
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    evaluation_status: EvaluationStatus = EvaluationStatus.NOT_STARTED
    
    # 자연스러운 통합 정보
    integration_log: List[Dict[str, Any]] = Field(default_factory=list)  # 언제 어떤 문항이 자연스럽게 통합되었는지 로그


class EvaluationUpdate(BaseModel):
    """평가 업데이트 요청"""
    item_id: str
    user_response: str
    conversation_context: Optional[Dict[str, Any]] = None


class EvaluationSummary(BaseModel):
    """평가 요약 결과"""
    conversation_id: str
    total_score: int
    max_score: int
    percentage: float
    
    # 영역별 요약
    orientation_score: int = 0
    memory_score: int = 0
    attention_score: int = 0
    executive_score: int = 0
    language_score: int = 0
    
    # 위험도 평가
    risk_level: str = Field(description="low, moderate, high")
    recommendations: List[str] = Field(default_factory=list)
    
    completed_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }