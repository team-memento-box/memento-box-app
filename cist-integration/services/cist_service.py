"""
CIST 통합 서비스 메인 클래스
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from langchain_openai import ChatOpenAI

from schemas.conversation_state import ConversationState, ConversationPhase
from schemas.evaluation import CISTEvaluation, EvaluationStatus
from graphs.conversation_graph import CISTConversationGraph
from evaluators.scoring import CISTScorer
from agents.evaluation_agent import EvaluationAgent


class CISTIntegrationService:
    """CIST 통합 서비스"""
    
    def __init__(self, openai_api_key: str, openai_model: str = "gpt-4.1-nano"):
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            temperature=0.7,
            model=openai_model
        )
        
        self.conversation_graph = CISTConversationGraph(self.llm)
        self.scorer = CISTScorer(self.llm)
        self.evaluation_agent = EvaluationAgent(self.llm, self.scorer)
        
        # 활성 대화 세션 저장소 (실제로는 데이터베이스에 저장)
        self.active_conversations: Dict[str, ConversationState] = {}
    
    async def start_conversation(self, 
                               conversation_id: str,
                               user_id: Optional[str] = None,
                               photo_id: Optional[str] = None,
                               photo_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """대화 세션 시작"""
        
        # CIST 평가 초기화
        cist_evaluation = CISTEvaluation(
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        # 대화 상태 초기화
        conversation_state = ConversationState(
            conversation_id=conversation_id,
            user_id=user_id,
            photo_id=photo_id,
            photo_analysis=photo_analysis or {},
            cist_evaluation=cist_evaluation
        )
        
        # 그래프 실행하여 초기화
        updated_state = await self.conversation_graph.run_conversation_step(conversation_state)
        
        # LangGraph 결과가 dict 형태로 반환되는 경우 처리
        if isinstance(updated_state, dict):
            # dict를 ConversationState 객체로 변환
            for key, value in updated_state.items():
                if hasattr(conversation_state, key):
                    setattr(conversation_state, key, value)
            updated_state = conversation_state
        
        # 세션 저장
        self.active_conversations[conversation_id] = updated_state
        
        # 첫 번째 메시지 반환
        first_message = ""
        if hasattr(updated_state, 'conversation_history') and updated_state.conversation_history:
            first_message = updated_state.conversation_history[-1]["content"]
        
        return {
            "conversation_id": conversation_id,
            "message": first_message,
            "phase": updated_state.current_phase.value,
            "status": "started"
        }
    
    async def process_user_input(self, 
                               conversation_id: str, 
                               user_input: str) -> Dict[str, Any]:
        """사용자 입력 처리"""
        
        if conversation_id not in self.active_conversations:
            return {
                "error": "Active conversation not found",
                "conversation_id": conversation_id
            }
        
        conversation_state = self.active_conversations[conversation_id]
        
        # 사용자 입력으로 대화 진행
        updated_state = await self.conversation_graph.run_conversation_step(
            conversation_state, 
            user_input
        )
        
        # LangGraph 결과가 dict 형태로 반환되는 경우 처리
        if isinstance(updated_state, dict):
            # dict를 ConversationState 객체로 변환
            for key, value in updated_state.items():
                if hasattr(conversation_state, key):
                    setattr(conversation_state, key, value)
            updated_state = conversation_state
        
        # 상태 업데이트
        self.active_conversations[conversation_id] = updated_state
        
        # 응답 생성
        assistant_message = ""
        if updated_state.conversation_history:
            last_message = updated_state.conversation_history[-1]
            if last_message["role"] == "assistant":
                assistant_message = last_message["content"]
        
        # 현재 진행 중인 CIST 문항 정보
        current_cist_info = None
        if updated_state.current_cist_item:
            from models.cist_items import cist_registry
            item = cist_registry.get_item(updated_state.current_cist_item)
            if item:
                current_cist_info = {
                    "item_id": updated_state.current_cist_item,
                    "item_name": item.name,
                    "domain": item.domain.value
                }
        
        return {
            "conversation_id": conversation_id,
            "message": assistant_message,
            "phase": updated_state.current_phase.value,
            "current_cist_item": current_cist_info,
            "completed_items": len(updated_state.completed_cist_items),
            "total_items": len(updated_state.pending_cist_items) + len(updated_state.completed_cist_items),
            "current_score": updated_state.cist_evaluation.total_score,
            "is_completed": updated_state.current_phase == ConversationPhase.COMPLETION
        }
    
    async def get_evaluation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """평가 요약 조회"""
        
        if conversation_id not in self.active_conversations:
            return {"error": "Conversation not found"}
        
        conversation_state = self.active_conversations[conversation_id]
        
        # 평가 요약 생성
        summary = await self.evaluation_agent.generate_evaluation_summary(
            conversation_state.cist_evaluation
        )
        
        return {
            "conversation_id": conversation_id,
            "total_score": summary.total_score,
            "max_score": summary.max_score,
            "percentage": summary.percentage,
            "risk_level": summary.risk_level,
            "domain_scores": {
                "orientation": summary.orientation_score,
                "memory": summary.memory_score,
                "attention": summary.attention_score,
                "executive": summary.executive_score,
                "language": summary.language_score
            },
            "recommendations": summary.recommendations,
            "completed_at": summary.completed_at.isoformat()
        }
    
    async def get_detailed_report(self, conversation_id: str) -> str:
        """상세 평가 보고서 생성"""
        
        if conversation_id not in self.active_conversations:
            return "대화를 찾을 수 없습니다."
        
        conversation_state = self.active_conversations[conversation_id]
        
        return await self.evaluation_agent.generate_detailed_report(
            conversation_state.cist_evaluation
        )
    
    async def end_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """대화 강제 종료"""
        
        if conversation_id not in self.active_conversations:
            return {"error": "Conversation not found"}
        
        conversation_state = self.active_conversations[conversation_id]
        conversation_state.current_phase = ConversationPhase.COMPLETION
        
        # 최종 평가 수행
        updated_state = await self.conversation_graph.run_conversation_step(conversation_state)
        self.active_conversations[conversation_id] = updated_state
        
        # 평가 요약 생성
        summary = await self.get_evaluation_summary(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "status": "completed",
            "final_message": "대화가 종료되었습니다. 함께해 주셔서 감사합니다.",
            "evaluation_summary": summary
        }
    
    def get_conversation_status(self, conversation_id: str) -> Dict[str, Any]:
        """대화 상태 조회"""
        
        if conversation_id not in self.active_conversations:
            return {"error": "Conversation not found"}
        
        state = self.active_conversations[conversation_id]
        
        return {
            "conversation_id": conversation_id,
            "phase": state.current_phase.value,
            "current_cist_item": state.current_cist_item,
            "completed_items": len(state.completed_cist_items),
            "pending_items": len(state.pending_cist_items),
            "total_score": state.cist_evaluation.total_score,
            "conversation_turns": len([msg for msg in state.conversation_history if msg["role"] == "user"]),
            "started_at": state.started_at.isoformat(),
            "last_updated": state.last_updated.isoformat()
        }
    
    def cleanup_conversation(self, conversation_id: str) -> bool:
        """대화 세션 정리"""
        
        if conversation_id in self.active_conversations:
            del self.active_conversations[conversation_id]
            return True
        return False
    
    def get_active_conversations(self) -> List[str]:
        """활성 대화 목록 조회"""
        return list(self.active_conversations.keys())