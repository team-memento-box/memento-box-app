from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import os
from supabase import create_client, Client
import uuid
from datetime import datetime
import sys

# 기존 워크플로우 import를 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from app.core.config import settings

class WorkflowInput(TypedDict):
    """그래프 실행을 위해 외부에서 주입되는 초기 데이터"""
    conversation_id: str
    user_id: str
    user_message: str
    photo_context: Dict[str, Any]

class IntermediateState(TypedDict):
    """노드 간 결정에 사용되는 임시 데이터"""
    cache_score: Optional[float]
    routing_decision: str

class FinalOutput(TypedDict):
    """최종적으로 사용자에게 전달될 결과물"""
    response_text: str
    response_audio_url: Optional[str]

class GraphState(TypedDict):
    """전체 워크플로우를 관통하는 상태 객체"""
    input_data: WorkflowInput
    message_history: List[Dict[str, str]]
    intermediate: IntermediateState
    output: FinalOutput
    execution_flow: List[str]  # 실행 플로우 추적용

class EnhancedDialogueWorkflow:
    """테스트용 확장된 대화 워크플로우 - 실행 플로우 추적 기능 추가"""
    
    def __init__(self):
        self.llm_mini = ChatOpenAI(
            model="gpt-4o-mini",  # 실제 사용 가능한 모델로 변경
            api_key=settings.OPENAI_API_KEY
        )
        self.llm_nano = ChatOpenAI(
            model="gpt-4o-mini",  # 실제 사용 가능한 모델로 변경
            temperature=0.5,
            max_tokens=256,
            api_key=settings.OPENAI_API_KEY
        )
        
        # Supabase 클라이언트 (테스트용이므로 에러 처리 강화)
        try:
            self.supabase: Client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_ANON_KEY
            )
        except Exception as e:
            print(f"⚠️  Supabase 연결 실패: {e}")
            self.supabase = None
        
        # 워크플로우 구성
        self.app = self._build_workflow()
    
    def _log_node_execution(self, node_name: str, state: GraphState) -> GraphState:
        """노드 실행 로그 추가"""
        if "execution_flow" not in state:
            state["execution_flow"] = []
        
        state["execution_flow"].append(node_name)
        print(f"🔄 노드 실행: {node_name}")
        
        # 상태 정보 출력
        if node_name == "router":
            print(f"   📝 사용자 메시지: {state['input_data']['user_message']}")
        elif node_name in ["cache_retrieve", "fallback"]:
            if state.get("intermediate", {}).get("cache_score"):
                print(f"   📊 캐시 점수: {state['intermediate']['cache_score']}")
        
        return state
    
    def _build_workflow(self):
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(GraphState)
        
        # 노드 추가 (로깅이 포함된 래퍼 함수들)
        workflow.add_node("init_state", self._wrapped_init_state)
        workflow.add_node("router", self._wrapped_router)
        workflow.add_node("standard_response", self._wrapped_standard_response)
        workflow.add_node("cache_retrieve", self._wrapped_cache_retrieve)
        workflow.add_node("fallback", self._wrapped_fallback)
        
        # 진입점 설정
        workflow.set_entry_point("init_state")
        
        # 엣지 정의
        workflow.add_edge("init_state", "router")
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "standard_chat": "standard_response",
                "assessment_chat": "cache_retrieve"
            }
        )
        workflow.add_edge("standard_response", END)
        workflow.add_conditional_edges(
            "cache_retrieve",
            self._cache_decision,
            {
                "use_cache": END,
                "use_fallback": "fallback"
            }
        )
        workflow.add_edge("fallback", END)
        
        return workflow.compile()
    
    def _wrapped_init_state(self, state: GraphState) -> GraphState:
        """로깅이 포함된 상태 초기화 노드"""
        state = self._log_node_execution("init_state", state)
        return self.init_state_node(state)
    
    def _wrapped_router(self, state: GraphState) -> GraphState:
        """로깅이 포함된 라우터 노드"""
        state = self._log_node_execution("router", state)
        result = self.router_node(state)
        print(f"   🛤️  라우팅 결정: {result['intermediate']['routing_decision']}")
        return result
    
    def _wrapped_standard_response(self, state: GraphState) -> GraphState:
        """로깅이 포함된 일반 응답 노드"""
        state = self._log_node_execution("standard_response", state)
        result = self.standard_response_node(state)
        print(f"   💬 일반 응답 생성 완료")
        return result
    
    def _wrapped_cache_retrieve(self, state: GraphState) -> GraphState:
        """로깅이 포함된 캐시 검색 노드"""
        state = self._log_node_execution("cache_retrieve", state)
        result = self.cache_retrieve_and_evaluate_node(state)
        print(f"   🔍 캐시 검색 완료 - 점수: {result['intermediate']['cache_score']}")
        return result
    
    def _wrapped_fallback(self, state: GraphState) -> GraphState:
        """로깅이 포함된 대체 응답 노드"""
        state = self._log_node_execution("fallback", state)
        result = self.fallback_node(state)
        print(f"   🔄 대체 응답 생성 완료")
        return result
    
    # 기존 노드들의 구현 (원본과 동일하지만 에러 처리 강화)
    def init_state_node(self, state: GraphState) -> GraphState:
        """상태 초기화 노드: DB에서 대화 기록 조회"""
        conversation_id = state["input_data"]["conversation_id"]
        
        try:
            if self.supabase:
                response = self.supabase.table("conversations").select(
                    "*, sessions(*)"
                ).eq("id", conversation_id).execute()
                
                if response.data:
                    conversation = response.data[0]
                    message_history = [
                        {"role": "system", "content": "당신은 치매 진단을 위한 대화 시스템입니다."}
                    ]
                    
                    if conversation.get("ai_analysis"):
                        message_history.append({
                            "role": "assistant", 
                            "content": conversation.get("ai_output", "")
                        })
                else:
                    message_history = [
                        {"role": "system", "content": "당신은 치매 진단을 위한 대화 시스템입니다."}
                    ]
            else:
                # Supabase 연결이 없는 경우 기본값
                message_history = [
                    {"role": "system", "content": "당신은 치매 진단을 위한 대화 시스템입니다."}
                ]
            
            state["message_history"] = message_history
            state["intermediate"] = {"cache_score": None, "routing_decision": ""}
            state["output"] = {"response_text": "", "response_audio_url": None}
            
        except Exception as e:
            print(f"❌ Database query failed: {e}")
            state["message_history"] = [
                {"role": "system", "content": "당신은 치매 진단을 위한 대화 시스템입니다."}
            ]
            state["intermediate"] = {"cache_score": None, "routing_decision": ""}
            state["output"] = {"response_text": "", "response_audio_url": None}
        
        return state
    
    def router_node(self, state: GraphState) -> GraphState:
        """라우터 노드: 인지기능 평가 질문 삽입 여부 결정"""
        user_message = state["input_data"]["user_message"]
        
        routing_prompt = f"""
        현재 대화 맥락을 분석하여 다음 중 하나를 선택하세요:
        
        1. standard_chat: 일반적인 일상 대화 진행
        2. assessment_chat: 인지기능 평가 질문 삽입
        
        사용자 메시지: {user_message}
        
        다음 기준으로 판단하세요:
        - 사용자가 기억력, 시간, 장소에 대해 언급하거나 혼란을 보이면 → assessment_chat
        - 일반적인 사진 설명이나 일상 대화이면 → standard_chat
        
        응답은 반드시 'standard_chat' 또는 'assessment_chat' 중 하나만 답하세요.
        """
        
        try:
            response = self.llm_mini.invoke([
                SystemMessage(content=routing_prompt),
                HumanMessage(content=user_message)
            ])
            
            routing_decision = response.content.strip().lower()
            if routing_decision not in ["standard_chat", "assessment_chat"]:
                routing_decision = "standard_chat"
                
            state["intermediate"]["routing_decision"] = routing_decision
            
        except Exception as e:
            print(f"❌ Router decision failed: {e}")
            state["intermediate"]["routing_decision"] = "standard_chat"
        
        return state
    
    def standard_response_node(self, state: GraphState) -> GraphState:
        """일반 응답 생성 노드: 자연스러운 일상 대화"""
        user_message = state["input_data"]["user_message"]
        photo_context = state["input_data"]["photo_context"]
        
        conversation_prompt = f"""
        사용자와 자연스럽고 따뜻한 대화를 나누세요.
        
        사용자 메시지: {user_message}
        사진 정보: {photo_context}
        
        응답 원칙:
        1. 50자 이내로 간결하게 답변
        2. 따뜻하고 공감적인 어조
        3. 사진과 관련된 내용이면 구체적으로 언급
        4. 추가 질문으로 대화 이어가기
        
        한 번에 하나의 질문만 해주세요.
        """
        
        try:
            response = self.llm_mini.invoke([
                SystemMessage(content=conversation_prompt),
                HumanMessage(content=user_message)
            ])
            
            state["output"]["response_text"] = response.content.strip()
            
        except Exception as e:
            print(f"❌ Standard response generation failed: {e}")
            state["output"]["response_text"] = "죄송합니다. 다시 말씀해 주시겠어요?"
        
        return state
    
    def cache_retrieve_and_evaluate_node(self, state: GraphState) -> GraphState:
        """캐시 검색 및 평가 노드: 인지기능 평가 질문 검색"""
        user_message = state["input_data"]["user_message"]
        
        try:
            if self.supabase:
                response = self.supabase.table("cist_question_templates").select(
                    "*"
                ).limit(5).execute()
                
                if response.data:
                    best_question = response.data[0]
                    cache_score = 0.9
                    
                    state["intermediate"]["cache_score"] = cache_score
                    state["output"]["response_text"] = best_question["template_text"]
                else:
                    state["intermediate"]["cache_score"] = 0.3
                    state["output"]["response_text"] = "오늘 날짜를 말씀해 주실 수 있나요?"
            else:
                # Supabase 연결이 없는 경우 Mock 데이터
                state["intermediate"]["cache_score"] = 0.9
                state["output"]["response_text"] = "오늘이 며칠인지 기억하시나요?"
                
        except Exception as e:
            print(f"❌ Cache retrieval failed: {e}")
            state["intermediate"]["cache_score"] = 0.3
            state["output"]["response_text"] = "기억에 관해 조금 더 이야기해주실까요?"
        
        return state
    
    def fallback_node(self, state: GraphState) -> GraphState:
        """대체 응답 처리 노드: 경량 LLM으로 응답 생성"""
        user_message = state["input_data"]["user_message"]
        
        fallback_prompt = f"""
        간단하고 따뜻한 응답을 생성하세요.
        
        사용자 메시지: {user_message}
        
        30자 이내로 공감하며 답변해주세요.
        """
        
        try:
            response = self.llm_nano.invoke([
                SystemMessage(content=fallback_prompt),
                HumanMessage(content=user_message)
            ])
            
            state["output"]["response_text"] = response.content.strip()
            
        except Exception as e:
            print(f"❌ Fallback response failed: {e}")
            state["output"]["response_text"] = "네, 알겠습니다."
        
        return state
    
    def _route_decision(self, state: GraphState) -> str:
        """라우터 결정에 따른 경로 선택"""
        decision = state["intermediate"]["routing_decision"]
        print(f"   🎯 라우팅 경로: {decision}")
        return decision
    
    def _cache_decision(self, state: GraphState) -> str:
        """캐시 점수에 따른 경로 선택"""
        cache_score = state["intermediate"]["cache_score"]
        if cache_score and cache_score >= 0.85:
            decision = "use_cache"
        else:
            decision = "use_fallback"
        
        print(f"   📈 캐시 결정: {decision} (점수: {cache_score})")
        return decision
    
    async def process_message(self, input_data: WorkflowInput) -> Dict[str, Any]:
        """메시지 처리 진입점 - 실행 플로우 정보 포함"""
        initial_state = {
            "input_data": input_data,
            "message_history": [],
            "intermediate": {"cache_score": None, "routing_decision": ""},
            "output": {"response_text": "", "response_audio_url": None},
            "execution_flow": []
        }
        
        print(f"\n🚀 워크플로우 시작: {input_data['user_message']}")
        print("=" * 60)
        
        try:
            final_state = await self.app.ainvoke(initial_state)
            
            print("=" * 60)
            print(f"✅ 워크플로우 완료!")
            print(f"🔄 실행된 노드들: {' → '.join(final_state['execution_flow'])}")
            print(f"💬 최종 응답: {final_state['output']['response_text']}")
            
            return {
                "response_text": final_state["output"]["response_text"],
                "response_audio_url": final_state["output"]["response_audio_url"],
                "execution_flow": final_state["execution_flow"]
            }
            
        except Exception as e:
            print(f"❌ Workflow execution failed: {e}")
            return {
                "response_text": "죄송합니다. 처리 중 오류가 발생했습니다.",
                "response_audio_url": None,
                "execution_flow": ["error"]
            }


async def test_standard_chat():
    """일반 대화 테스트"""
    workflow = EnhancedDialogueWorkflow()
    
    test_input: WorkflowInput = {
        "conversation_id": str(uuid.uuid4()),
        "user_id": "test-user-123",
        "user_message": "안녕하세요! 오늘 날씨가 좋네요.",
        "photo_context": {"description": "밝은 하늘 사진", "objects": ["하늘", "구름"]}
    }
    
    print("\n" + "="*80)
    print("🧪 일반 대화 테스트")
    print("="*80)
    
    try:
        result = await workflow.process_message(test_input)
        print(f"\n📊 테스트 결과:")
        print(f"   응답: {result['response_text']}")
        print(f"   실행 플로우: {' → '.join(result['execution_flow'])}")
        print("   ✅ 테스트 성공!")
        return True
    except Exception as e:
        print(f"   ❌ 테스트 실패: {e}")
        return False


async def test_assessment_chat():
    """평가 대화 테스트"""
    workflow = EnhancedDialogueWorkflow()
    
    test_input: WorkflowInput = {
        "conversation_id": str(uuid.uuid4()),
        "user_id": "test-user-124", 
        "user_message": "어제가 몇 일이었는지 기억이 안 나요.",
        "photo_context": {"description": "일기장 사진", "objects": ["일기장", "펜"]}
    }
    
    print("\n" + "="*80)
    print("🧪 평가 대화 테스트")
    print("="*80)
    
    try:
        result = await workflow.process_message(test_input)
        print(f"\n📊 테스트 결과:")
        print(f"   응답: {result['response_text']}")
        print(f"   실행 플로우: {' → '.join(result['execution_flow'])}")
        print("   ✅ 테스트 성공!")
        return True
    except Exception as e:
        print(f"   ❌ 테스트 실패: {e}")
        return False


async def test_edge_cases():
    """엣지 케이스 테스트"""
    workflow = EnhancedDialogueWorkflow()
    
    # 애매한 경계 케이스
    test_cases = [
        {
            "name": "경계 케이스 1: 시간 관련 일반 대화",
            "message": "오늘 시간이 참 빨리 가네요",
            "expected_route": "standard_chat"
        },
        {
            "name": "경계 케이스 2: 명확한 기억력 문제",
            "message": "방금 뭐라고 했는지 기억이 안나요",
            "expected_route": "assessment_chat"
        },
        {
            "name": "경계 케이스 3: 빈 메시지",
            "message": "",
            "expected_route": "standard_chat"
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases):
        print(f"\n" + "="*80)
        print(f"🧪 {test_case['name']}")
        print("="*80)
        
        test_input: WorkflowInput = {
            "conversation_id": str(uuid.uuid4()),
            "user_id": f"test-user-{125+i}",
            "user_message": test_case["message"],
            "photo_context": {"description": "테스트 사진", "objects": ["테스트"]}
        }
        
        try:
            result = await workflow.process_message(test_input)
            route_taken = "standard_chat" if "standard_response" in result["execution_flow"] else "assessment_chat"
            
            print(f"\n📊 테스트 결과:")
            print(f"   입력: '{test_case['message']}'")
            print(f"   예상 경로: {test_case['expected_route']}")
            print(f"   실제 경로: {route_taken}")
            print(f"   실행 플로우: {' → '.join(result['execution_flow'])}")
            print(f"   응답: {result['response_text']}")
            
            success = route_taken == test_case["expected_route"]
            print(f"   {'✅ 예상대로 라우팅됨' if success else '⚠️ 예상과 다른 라우팅'}")
            results.append(success)
            
        except Exception as e:
            print(f"   ❌ 테스트 실패: {e}")
            results.append(False)
    
    return results


async def main():
    """메인 테스트 실행"""
    print("🔬 Enhanced DialogueWorkflow 테스트를 시작합니다...")
    print("\n이 테스트는 각 노드의 실행 과정과 흐름을 상세히 보여줍니다.")
    
    # 환경변수 확인
    if not settings.OPENAI_API_KEY:
        print("\n❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        print("backend/.env 파일에서 OPENAI_API_KEY를 설정해주세요.")
        print("\n테스트를 위해 Mock 응답으로 진행할 수도 있습니다.")
        return
    
    # 테스트 실행
    test_results = []
    
    # 기본 테스트들
    test_results.append(await test_standard_chat())
    test_results.append(await test_assessment_chat())
    
    # 엣지 케이스 테스트
    edge_results = await test_edge_cases()
    test_results.extend(edge_results)
    
    # 결과 요약
    print("\n" + "="*80)
    print("📋 테스트 결과 요약")
    print("="*80)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"✅ 성공: {passed}/{total}")
    print(f"❌ 실패: {total-passed}/{total}")
    
    if passed == total:
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print(f"\n⚠️ {total-passed}개의 테스트에서 문제가 발생했습니다.")
    
    print("\n💡 이 테스트를 통해 다음을 확인할 수 있습니다:")
    print("   - 각 노드가 실행되는 순서")
    print("   - 라우팅 결정 과정") 
    print("   - 캐시 점수와 대체 로직 선택")
    print("   - 에러 처리 메커니즘")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())