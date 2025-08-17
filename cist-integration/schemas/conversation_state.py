"""
대화 상태 관리를 위한 스키마
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from models.cist_items import CognitiveDomain
from schemas.evaluation import CISTEvaluation, ItemResponse


class ConversationPhase(str, Enum):
    """대화 단계"""
    INITIALIZATION = "initialization"  # 초기화
    PHOTO_DISCUSSION = "photo_discussion"  # 사진 관련 대화
    CIST_INTEGRATION = "cist_integration"  # CIST 문항 통합
    EVALUATION = "evaluation"  # 평가 진행
    COMPLETION = "completion"  # 완료


class IntegrationStrategy(str, Enum):
    """CIST 문항 통합 전략"""
    NATURAL_TRANSITION = "natural_transition"  # 자연스러운 전환
    DIRECT_QUESTION = "direct_question"  # 직접적 질문
    GAME_LIKE = "game_like"  # 게임 형태
    STORYTELLING = "storytelling"  # 스토리텔링


class ConversationState(BaseModel):
    """대화 상태 정보"""
    # 기본 정보
    conversation_id: str
    user_id: Optional[str] = None
    photo_id: Optional[str] = None
    
    # 대화 단계
    current_phase: ConversationPhase = ConversationPhase.INITIALIZATION
    
    # 사진 분석 결과
    photo_analysis: Dict[str, Any] = Field(default_factory=dict)
    
    # 대화 기록
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    
    # CIST 평가 상태
    cist_evaluation: CISTEvaluation
    
    # CIST 문항 진행 상태
    pending_cist_items: List[str] = Field(default_factory=list)  # 아직 진행하지 않은 문항들
    current_cist_item: Optional[str] = None  # 현재 진행 중인 문항
    completed_cist_items: List[str] = Field(default_factory=list)  # 완료된 문항들
    
    # 자연스러운 통합을 위한 컨텍스트
    integration_opportunities: Dict[str, Any] = Field(default_factory=dict)
    
    # 대화 품질 관리
    conversation_quality: Dict[str, Any] = Field(
        default_factory=lambda: {
            "engagement_level": 0,  # 참여도 (0-10)
            "response_coherence": 0,  # 응답 일관성 (0-10)
            "topic_maintenance": 0,  # 주제 유지도 (0-10)
        }
    )
    
    # 메타 정보
    started_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    # 설정
    max_conversation_turns: int = 50
    min_cist_items_to_complete: int = 5  # 최소 완료해야 할 CIST 문항 수
    
    # 루프 방지
    graph_execution_count: int = 0  # 그래프 실행 횟수
    max_graph_executions: int = 3  # 최대 그래프 실행 횟수 (매우 낮게 설정)
    integration_attempt_count: int = 0  # CIST 통합 시도 횟수
    max_integration_attempts: int = 1  # 최대 통합 시도 횟수 (매우 낮게 설정)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationAction(BaseModel):
    """대화 액션 정보"""
    action_type: str  # "continue_conversation", "integrate_cist", "evaluate_response", "end_conversation"
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class NodeDecision(BaseModel):
    """그래프 노드에서의 결정 정보"""
    next_node: str
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    additional_data: Dict[str, Any] = Field(default_factory=dict)