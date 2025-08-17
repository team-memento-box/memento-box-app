"""
CIST 통합 대화를 위한 LangGraph 워크플로우
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from schemas.conversation_state import ConversationState, ConversationPhase, NodeDecision
from models.cist_items import cist_registry, CognitiveDomain
from evaluators.scoring import CISTScorer
from agents.conversation_agent import ConversationAgent
from agents.cist_integration_agent import CISTIntegrationAgent
from agents.evaluation_agent import EvaluationAgent


class CISTConversationGraph:
    """CIST 통합 대화 그래프"""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(temperature=0.7, model="gpt-4.1-nano")
        self.scorer = CISTScorer(self.llm)
        
        # 에이전트 초기화
        self.conversation_agent = ConversationAgent(self.llm)
        self.cist_agent = CISTIntegrationAgent(self.llm)
        self.evaluation_agent = EvaluationAgent(self.llm, self.scorer)
        
        # 그래프 생성
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """대화 그래프 생성"""
        
        workflow = StateGraph(ConversationState)
        
        # 노드 추가
        workflow.add_node("initialize", self._initialize_conversation)
        workflow.add_node("analyze_photo", self._analyze_photo)
        workflow.add_node("natural_conversation", self._conduct_natural_conversation)
        workflow.add_node("assess_integration_opportunity", self._assess_integration_opportunity)
        workflow.add_node("integrate_cist_item", self._integrate_cist_item)
        workflow.add_node("evaluate_response", self._evaluate_response)
        workflow.add_node("update_conversation_state", self._update_conversation_state)
        workflow.add_node("check_completion", self._check_completion)
        workflow.add_node("finalize_evaluation", self._finalize_evaluation)
        
        # 시작점
        workflow.set_entry_point("initialize")
        
        # 조건부 엣지
        workflow.add_conditional_edges(
            "initialize",
            self._decide_after_initialization,
            {
                "analyze_photo": "analyze_photo",
                "natural_conversation": "natural_conversation"
            }
        )
        
        workflow.add_conditional_edges(
            "analyze_photo", 
            self._decide_after_photo_analysis,
            {
                "natural_conversation": "natural_conversation"
            }
        )
        
        workflow.add_conditional_edges(
            "natural_conversation",
            self._decide_after_natural_conversation,
            {
                "assess_integration_opportunity": "assess_integration_opportunity",
                "check_completion": "check_completion"
            }
        )
        
        workflow.add_conditional_edges(
            "assess_integration_opportunity",
            self._decide_integration_strategy,
            {
                "integrate_cist_item": "integrate_cist_item",
                "natural_conversation": "natural_conversation",
                "check_completion": "check_completion"
            }
        )
        
        workflow.add_conditional_edges(
            "integrate_cist_item",
            self._decide_after_integration,
            {
                "evaluate_response": "evaluate_response",
                "natural_conversation": "natural_conversation"
            }
        )
        
        workflow.add_conditional_edges(
            "evaluate_response",
            self._decide_after_evaluation,
            {
                "update_conversation_state": "update_conversation_state",
                "natural_conversation": "natural_conversation"
            }
        )
        
        workflow.add_conditional_edges(
            "update_conversation_state",
            self._decide_after_state_update,
            {
                "natural_conversation": "natural_conversation",
                "check_completion": "check_completion"
            }
        )
        
        workflow.add_conditional_edges(
            "check_completion",
            self._decide_completion,
            {
                "finalize_evaluation": "finalize_evaluation",
                "natural_conversation": "natural_conversation",
                "assess_integration_opportunity": "assess_integration_opportunity"
            }
        )
        
        workflow.add_edge("finalize_evaluation", END)
        
        return workflow.compile()
    
    # 노드 함수들
    async def _initialize_conversation(self, state: ConversationState) -> ConversationState:
        """대화 초기화"""
        
        # CIST 문항 목록 초기화
        all_items = list(cist_registry.items.keys())
        state.pending_cist_items = all_items.copy()
        
        # 대화 시작 메시지
        welcome_message = "안녕하세요! 사진을 보면서 즐겁게 대화해보시죠."
        state.conversation_history.append({
            "role": "assistant", 
            "content": welcome_message
        })
        
        state.current_phase = ConversationPhase.INITIALIZATION
        return state
    
    async def _analyze_photo(self, state: ConversationState) -> ConversationState:
        """사진 분석"""
        
        # 기존 시스템의 사진 분석 결과 활용
        # 실제 구현에서는 기존 image_analyzer 서비스와 연동
        if not state.photo_analysis:
            state.photo_analysis = {
                "caption": "가족이 함께 있는 따뜻한 모습",
                "mood": "따뜻함, 행복",
                "objects": ["사람", "테이블", "음식"],
                "people_count": 3
            }
        
        state.current_phase = ConversationPhase.PHOTO_DISCUSSION
        return state
    
    async def _conduct_natural_conversation(self, state: ConversationState) -> ConversationState:
        """자연스러운 대화 진행"""
        
        if not state.conversation_history:
            return state
        
        # 마지막 사용자 메시지 가져오기
        last_user_message = None
        for msg in reversed(state.conversation_history):
            if msg["role"] == "user":
                last_user_message = msg["content"]
                break
        
        if last_user_message:
            # 대화 에이전트를 통해 자연스러운 응답 생성 (임시로 모킹)
            response = f"네, {last_user_message[:20]}... 말씀 잘 들었습니다. 정말 소중한 추억이시겠어요."
            print(f"🤖 Mocked conversation response: {response}")
            
            state.conversation_history.append({
                "role": "assistant",
                "content": response
            })
        
        return state
    
    async def _assess_integration_opportunity(self, state: ConversationState) -> ConversationState:
        """CIST 문항 통합 기회 평가"""
        
        print(f"🎯 _assess_integration_opportunity: pending_items={len(state.pending_cist_items)}, attempts={state.integration_attempt_count}")
        
        # 통합 시도 횟수 증가
        state.integration_attempt_count += 1
        
        if not state.pending_cist_items:
            print("📝 No pending items, returning state")
            return state
        
        # 현재 대화 맥락에서 자연스럽게 통합할 수 있는 CIST 문항 찾기
        # 임시로 모킹하여 무한 루프 방지
        try:
            # 실제 에이전트 호출 대신 간단한 로직으로 대체
            if state.pending_cist_items and state.integration_attempt_count <= 1:
                # 첫 번째 시도에서만 추천 항목 제공
                first_item = state.pending_cist_items[0]
                opportunity = {
                    "recommended_item": first_item,
                    "strategy": "natural_transition",
                    "evaluation_context": {}
                }
                print(f"🧠 Mocked integration opportunity: {first_item}")
            else:
                opportunity = {}
                print("📝 No integration opportunity (mocked)")
            
            state.integration_opportunities = opportunity
        except Exception as e:
            print(f"❌ Error assessing integration opportunity: {e}")
            state.integration_opportunities = {}
            
        return state
    
    async def _integrate_cist_item(self, state: ConversationState) -> ConversationState:
        """CIST 문항 자연스러운 통합"""
        
        if not state.integration_opportunities.get("recommended_item"):
            return state
        
        item_id = state.integration_opportunities["recommended_item"]
        integration_strategy = state.integration_opportunities.get("strategy", "natural_transition")
        
        # CIST 문항을 자연스럽게 통합한 질문 생성 (임시로 모킹)
        integrated_question = f"그런데 말씀드린 것 중에서... (CIST 문항 {item_id} 통합된 질문)"
        print(f"🧠 Mocked integrated question for {item_id}: {integrated_question}")
        
        state.conversation_history.append({
            "role": "assistant",
            "content": integrated_question
        })
        
        state.current_cist_item = item_id
        state.current_phase = ConversationPhase.CIST_INTEGRATION
        
        return state
    
    async def _evaluate_response(self, state: ConversationState) -> ConversationState:
        """사용자 응답 평가"""
        
        if not state.current_cist_item:
            return state
        
        # 마지막 사용자 응답 가져오기
        last_user_response = None
        for msg in reversed(state.conversation_history):
            if msg["role"] == "user":
                last_user_response = msg["content"]
                break
        
        if last_user_response:
            # 평가 컨텍스트 준비
            evaluation_context = state.integration_opportunities.get("evaluation_context", {})
            
            # 응답 평가
            item_response = self.scorer.evaluate_response(
                item_id=state.current_cist_item,
                user_response=last_user_response,
                context=evaluation_context
            )
            
            # 평가 결과 저장
            state.cist_evaluation.item_responses[state.current_cist_item] = item_response
            
            # 상태 업데이트
            state.completed_cist_items.append(state.current_cist_item)
            if state.current_cist_item in state.pending_cist_items:
                state.pending_cist_items.remove(state.current_cist_item)
            
            state.current_cist_item = None
            state.current_phase = ConversationPhase.EVALUATION
        
        return state
    
    async def _update_conversation_state(self, state: ConversationState) -> ConversationState:
        """대화 상태 업데이트"""
        
        # 영역별 점수 계산  
        state.cist_evaluation.domain_scores = self.scorer.calculate_domain_scores(state.cist_evaluation)
        
        # 전체 점수 계산
        total_score, percentage = self.scorer.calculate_total_score(state.cist_evaluation)
        state.cist_evaluation.total_score = total_score
        state.cist_evaluation.total_percentage = percentage
        
        # 대화 품질 업데이트
        await self._update_conversation_quality(state)
        
        state.last_updated = datetime.now()
        return state
    
    async def _check_completion(self, state: ConversationState) -> ConversationState:
        """완료 조건 확인"""
        
        # 완료 조건 체크
        completed_items_count = len(state.completed_cist_items)
        conversation_turns = len([msg for msg in state.conversation_history if msg["role"] == "user"])
        
        should_complete = (
            completed_items_count >= state.min_cist_items_to_complete or
            conversation_turns >= state.max_conversation_turns or
            not state.pending_cist_items
        )
        
        if should_complete:
            state.current_phase = ConversationPhase.COMPLETION
        
        return state
    
    async def _finalize_evaluation(self, state: ConversationState) -> ConversationState:
        """최종 평가 완료"""
        
        # 최종 점수 계산
        state.cist_evaluation.domain_scores = self.scorer.calculate_domain_scores(state.cist_evaluation)
        total_score, percentage = self.scorer.calculate_total_score(state.cist_evaluation)
        
        state.cist_evaluation.total_score = total_score
        state.cist_evaluation.total_percentage = percentage
        state.cist_evaluation.completed_at = datetime.now()
        state.cist_evaluation.evaluation_status = "completed"
        
        # 마무리 메시지
        closing_message = f"오늘 대화 정말 즐거웠습니다. 어르신과 함께한 소중한 시간이었어요."
        state.conversation_history.append({
            "role": "assistant",
            "content": closing_message
        })
        
        return state
    
    # 조건부 엣지 결정 함수들
    def _decide_after_initialization(self, state: ConversationState) -> str:
        """초기화 후 결정"""
        print(f"🚀 _decide_after_initialization: photo_analysis exists = {bool(state.photo_analysis)}")
        if state.photo_analysis:
            print("📸 Photo analysis exists, going to natural_conversation")
            return "natural_conversation"
        else:
            print("📷 No photo analysis, going to analyze_photo")
            return "analyze_photo"
    
    def _decide_after_photo_analysis(self, state: ConversationState) -> str:
        """사진 분석 후 결정"""
        return "natural_conversation"
    
    def _decide_after_natural_conversation(self, state: ConversationState) -> str:
        """자연 대화 후 결정"""
        conversation_turns = len([msg for msg in state.conversation_history if msg["role"] == "user"])
        
        print(f"🔄 _decide_after_natural_conversation: executions={state.graph_execution_count}, integrations={state.integration_attempt_count}, turns={conversation_turns}")
        
        # 루프 방지: 최대 실행 횟수 체크
        if state.graph_execution_count >= state.max_graph_executions:
            print("⚠️  Max executions reached, going to completion")
            return "check_completion"
        
        # 루프 방지: 최대 통합 시도 횟수 체크
        if state.integration_attempt_count >= state.max_integration_attempts:
            print("⚠️  Max integration attempts reached, going to completion")
            return "check_completion"
        
        # 적절한 타이밍에 CIST 문항 통합 시도
        if (conversation_turns >= 2 and 
            state.pending_cist_items and 
            conversation_turns % 3 == 0):  # 3턴마다 CIST 통합 시도
            state.integration_attempt_count += 1
            print(f"🧠 Going to assess_integration_opportunity (attempt #{state.integration_attempt_count})")
            return "assess_integration_opportunity"
        else:
            print("📝 Going to check_completion")
            return "check_completion"
    
    def _decide_integration_strategy(self, state: ConversationState) -> str:
        """통합 전략 결정"""
        print(f"🎯 _decide_integration_strategy: has_recommended_item={bool(state.integration_opportunities.get('recommended_item'))}")
        
        # 통합 시도 횟수 체크
        if state.integration_attempt_count >= state.max_integration_attempts:
            print("⚠️  Max integration attempts reached in strategy decision")
            return "check_completion"
            
        if state.integration_opportunities.get("recommended_item"):
            print("🧠 Has recommended item, going to integrate_cist_item")
            return "integrate_cist_item"
        else:
            print("📝 No recommended item, going to check_completion")
            return "check_completion"
    
    def _decide_after_integration(self, state: ConversationState) -> str:
        """통합 후 결정"""
        # 사용자 응답 대기
        return "evaluate_response"
        
    def _decide_after_evaluation(self, state: ConversationState) -> str:
        """평가 후 결정"""
        return "update_conversation_state"
    
    def _decide_after_state_update(self, state: ConversationState) -> str:
        """상태 업데이트 후 결정"""  
        return "check_completion"
    
    def _decide_completion(self, state: ConversationState) -> str:
        """완료 결정"""
        print(f"🏁 _decide_completion: phase={state.current_phase.value}, executions={state.graph_execution_count}, completed_items={len(state.completed_cist_items)}, pending_items={len(state.pending_cist_items)}, attempts={state.integration_attempt_count}")
        
        # 루프 방지: 최대 실행 횟수에 도달하면 강제 종료
        if state.graph_execution_count >= state.max_graph_executions:
            print("⚠️  Max executions reached, finalizing evaluation")
            return "finalize_evaluation"
            
        # 루프 방지: 최대 통합 시도 횟수에 도달하면 강제 종료
        if state.integration_attempt_count >= state.max_integration_attempts:
            print("⚠️  Max integration attempts reached, finalizing evaluation")
            return "finalize_evaluation"
        
        if state.current_phase == ConversationPhase.COMPLETION:
            print("✅ Phase is COMPLETION, finalizing evaluation")
            return "finalize_evaluation"
        elif state.pending_cist_items and len(state.completed_cist_items) < state.min_cist_items_to_complete:
            # CIST 통합 시도 횟수를 여기서 증가시키지 말고, 실제로 assess_integration_opportunity를 실행할 때만 증가
            print(f"🧠 Need more CIST items, going to assess_integration_opportunity")
            return "assess_integration_opportunity"
        else:
            print("🔄 Going back to natural_conversation")
            return "natural_conversation"
    
    async def _update_conversation_quality(self, state: ConversationState):
        """대화 품질 업데이트"""
        # 간단한 휴리스틱으로 대화 품질 평가
        # 실제로는 더 정교한 평가 로직 필요
        
        user_messages = [msg["content"] for msg in state.conversation_history if msg["role"] == "user"]
        
        if user_messages:
            avg_length = sum(len(msg.split()) for msg in user_messages) / len(user_messages)
            state.conversation_quality["engagement_level"] = min(10, int(avg_length / 2))
            state.conversation_quality["response_coherence"] = 8  # 기본값
            state.conversation_quality["topic_maintenance"] = 7  # 기본값
    
    async def run_conversation_step(self, state: ConversationState, user_input: Optional[str] = None) -> ConversationState:
        """대화 한 스텝 실행"""
        
        print(f"🔄 run_conversation_step called: execution_count={state.graph_execution_count}, user_input={user_input is not None}")
        
        if user_input:
            state.conversation_history.append({
                "role": "user", 
                "content": user_input
            })
        
        # 그래프 실행 횟수 증가
        state.graph_execution_count += 1
        
        # 최대 실행 횟수 체크
        if state.graph_execution_count >= state.max_graph_executions:
            print(f"⚠️  Maximum executions ({state.max_graph_executions}) reached, forcing completion")
            # 강제 종료
            state.current_phase = ConversationPhase.COMPLETION
            return state
        
        print(f"📊 Starting graph execution #{state.graph_execution_count}")
        # 그래프 실행 (recursion_limit 설정)
        try:
            result = await self.graph.ainvoke(
                state, 
                config={
                    "recursion_limit": 50
                }
            )
            print(f"✅ Graph execution #{state.graph_execution_count} completed")
            return result
        except Exception as e:
            print(f"❌ Graph execution failed: {e}")
            state.current_phase = ConversationPhase.COMPLETION
            return state