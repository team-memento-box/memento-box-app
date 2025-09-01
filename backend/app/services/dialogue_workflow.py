from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import os
from supabase import create_client, Client
import uuid
from datetime import datetime
from core.config import settings

class WorkflowInput(TypedDict):
    """그래프 실행을 위해 외부에서 주입되는 초기 데이터"""
    conversation_id: str
    user_id: str
    user_message: str
    photo_context: Dict[str, Any]
    audio_url: Optional[str] = None  # 음성 파일 URL 추가

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
    photo_info: Optional[Dict[str, Any]]  # 사진 정보 저장
    session_id: Optional[str]  # 세션 ID 저장
    _authenticated_client: Optional[Client]  # 인증된 Supabase 클라이언트
    cist_progress: Optional[Dict[str, bool]]  # CIST 진행 상태
    current_cist_category: Optional[str]  # 현재 진행할 CIST 카테고리

class DialogueWorkflow:
    """LangGraph 기반 대화 워크플로우 시스템"""
    
    def __init__(self):
        # 세션별 CIST 진행 상태 메모리 캐시
        self._session_cist_cache = {}
        # 필수 환경 변수 검증 (settings 사용)
        openai_key = settings.OPENAI_API_KEY
        supabase_url = settings.SUPABASE_URL
        supabase_key = settings.SUPABASE_ANON_KEY
        
        # LangSmith 설정
        langsmith_tracing = settings.LANGSMITH_TRACING and settings.LANGSMITH_TRACING.lower() == "true"
        langsmith_project = settings.LANGSMITH_PROJECT or "memento-box-dialogue"
        
        # LangSmith 환경변수 설정 (LangChain이 자동으로 읽도록)
        if settings.LANGSMITH_TRACING:
            os.environ["LANGSMITH_TRACING"] = settings.LANGSMITH_TRACING
        if settings.LANGSMITH_API_KEY:
            os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
        if settings.LANGSMITH_PROJECT:
            os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
        if settings.LANGSMITH_ENDPOINT:
            os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        
        if not openai_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not supabase_url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not supabase_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is required")
        
        try:
            # LangSmith 메타데이터 설정
            langsmith_metadata = {
                "service": "dialogue_workflow",
                "version": "1.0",
                "environment": os.getenv("ENVIRONMENT", "development")
            }
            
            self.llm = ChatOpenAI(
                model="gpt-4o",
                api_key=openai_key,
                metadata=langsmith_metadata if langsmith_tracing else None
            )
            self.llm_mini = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=openai_key,
                metadata=langsmith_metadata if langsmith_tracing else None
            )
            self.llm_nano = ChatOpenAI(
                model="gpt-4o-mini",
                max_tokens=256,
                api_key=openai_key,
                metadata=langsmith_metadata if langsmith_tracing else None
            )
            print(f"OpenAI LLM clients initialized successfully (LangSmith tracing: {langsmith_tracing})")
        except Exception as e:
            print(f"Failed to initialize OpenAI clients: {e}")
            raise
        
        try:
            # Supabase 클라이언트
            self.supabase: Client = create_client(
                supabase_url=supabase_url,
                supabase_key=supabase_key
            )
            print("Supabase client initialized successfully")
        except Exception as e:
            print(f"Failed to initialize Supabase client: {e}")
            raise
        
        try:
            # 워크플로우 구성
            self.app = self._build_workflow()
            print("LangGraph workflow compiled successfully")
        except Exception as e:
            print(f"Failed to build LangGraph workflow: {e}")
            raise
    
    def _build_workflow(self):
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(GraphState)
        
        # 노드 추가
        workflow.add_node("init_state", self.init_state_node)
        workflow.add_node("router", self.router_node)
        workflow.add_node("standard_response", self.standard_response_node)
        workflow.add_node("time_orientation", self.time_orientation_node)
        workflow.add_node("registration", self.registration_node) 
        workflow.add_node("recall", self.recall_node)
        workflow.add_node("naming", self.naming_node)
        workflow.add_node("cache_retrieve", self.cache_retrieve_and_evaluate_node)
        workflow.add_node("fallback", self.fallback_node)
        
        # 진입점 설정
        workflow.set_entry_point("init_state")
        
        # 엣지 정의
        workflow.add_edge("init_state", "router")
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "standard": "standard_response",
                "time_orientation": "time_orientation",
                "registration": "registration", 
                "recall": "recall",
                "naming": "naming",
                "assessment_chat": "cache_retrieve"  # 기존 호환성
            }
        )
        
        # 모든 노드에서 END로 연결
        workflow.add_edge("standard_response", END)
        workflow.add_edge("time_orientation", END)
        workflow.add_edge("registration", END)
        workflow.add_edge("recall", END) 
        workflow.add_edge("naming", END)
        
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
    
    def _get_cached_cist_progress(self, session_id: str) -> Dict[str, bool]:
        """메모리 캐시에서 CIST 진행 상태 조회"""
        return self._session_cist_cache.get(session_id, {
            "time_orientation": False, 
            "registration": False, 
            "recall": False, 
            "naming": False
        })
    
    def _update_cached_cist_progress(self, session_id: str, category: str, completed: bool = True):
        """메모리 캐시의 CIST 진행 상태 업데이트"""
        if session_id not in self._session_cist_cache:
            self._session_cist_cache[session_id] = {
                "time_orientation": False, 
                "registration": False, 
                "recall": False, 
                "naming": False
            }
        
        self._session_cist_cache[session_id][category] = completed
        print(f"💾 캐시 업데이트: {session_id} - {category} = {completed}")
        print(f"📊 현재 캐시 상태: {self._session_cist_cache[session_id]}")
    
    async def _get_session_cist_progress(self, session_id: str) -> Dict[str, bool]:
        """세션의 CIST 진행 상태 조회"""
        try:
            # 해당 세션에서 완료된 CIST 카테고리들 조회
            response = self.supabase.table("conversations").select(
                "cist_category"
            ).eq("session_id", session_id).eq("is_cist_item", True).not_.is_("cist_category", "null").execute()
            
            completed_categories = set()
            for record in response.data:
                if record.get("cist_category"):
                    completed_categories.add(record["cist_category"])
            
            # 전체 CIST 카테고리와 완료 상태 반환
            cist_categories = ["time_orientation", "registration", "recall", "naming"]
            progress = {}
            for category in cist_categories:
                progress[category] = category in completed_categories
                
            print(f"📊 CIST 진행 상태 (세션 {session_id}): {progress}")
            return progress
            
        except Exception as e:
            print(f"❌ CIST 진행 상태 조회 실패: {e}")
            return {"time_orientation": False, "registration": False, "recall": False, "naming": False}
    
    def _get_next_cist_category(self, progress: Dict[str, bool]) -> str:
        """다음 진행할 CIST 카테고리 반환"""
        # 순서대로 미완료된 첫 번째 카테고리 반환
        categories_order = ["time_orientation", "registration", "recall", "naming"]
        
        print(f"📊 CIST 진행 현황 확인: {progress}")
        
        for category in categories_order:
            if not progress.get(category, False):
                print(f"🎯 다음 CIST 카테고리: {category}")
                return category
        
        print("✅ 모든 CIST 카테고리 완료, standard 대화로 진행")
        return "standard"

    async def init_state_node(self, state: GraphState) -> GraphState:
        """상태 초기화 노드: DB에서 대화 기록, 사진 정보 및 CIST 진행 상태 조회"""
        conversation_id = state["input_data"]["conversation_id"]
        user_id = state["input_data"]["user_id"]
        photo_context = state["input_data"]["photo_context"]
        
        # 상태에서 인증된 클라이언트 가져오기
        client = state.get("_authenticated_client", self.supabase)
        
        print(f"🔍 상태 초기화: conversation_id={conversation_id}, user_id={user_id}")
        
        try:
            # 사진 정보 조회 (photo_context에 photo_id가 있는 경우)
            photo_info = None
            if photo_context.get("photo_id"):
                try:
                    photo_response = client.table("photos").select(
                        "id, filename, file_path, description, tags, location_name, photo_analyze_result"
                    ).eq("id", photo_context["photo_id"]).single().execute()
                    
                    if photo_response.data:
                        photo_info = photo_response.data
                        print(f"📷 사진 정보 로드됨: {photo_info}")
                except Exception as photo_error:
                    print(f"❌ 사진 정보 로드 실패: {photo_error}")
            
            # conversation_id를 session_id로 사용 (main.py에서 이미 세션 생성됨)
            session_id = conversation_id
            print(f"✅ 세션 ID 설정: {session_id}")
            
            # CIST 진행 상태 조회 (메모리 캐시 + DB 병합)
            cached_progress = self._get_cached_cist_progress(session_id)
            db_progress = await self._get_session_cist_progress(session_id)
            
            # 메모리와 DB 상태를 병합 (완료된 것은 되돌리지 않음)
            cist_progress = {}
            for category in ["time_orientation", "registration", "recall", "naming"]:
                # 캐시 또는 DB 중 하나라도 완료되었으면 완료로 처리
                cist_progress[category] = cached_progress.get(category, False) or db_progress.get(category, False)
            
            # 병합된 상태를 캐시에 저장
            self._session_cist_cache[session_id] = cist_progress
            
            next_cist_category = self._get_next_cist_category(cist_progress)
            
            print(f"🎯 캐시 상태: {cached_progress}")
            print(f"🎯 DB 상태: {db_progress}")
            print(f"🎯 병합된 CIST 진행 상태: {cist_progress}")
            print(f"🎯 다음 카테고리: {next_cist_category}")
            
            # 해당 세션의 기존 대화 내역 조회
            conversations_response = client.table("conversations").select(
                "id, ai_output, user_input, conversation_order"
            ).eq("session_id", session_id).order("conversation_order").execute()
            
            print(f"💬 기존 대화 내역: {len(conversations_response.data) if conversations_response.data else 0}개")
            
            # 메시지 히스토리 구성
            system_content = "당신은 치매 진단을 위한 따뜻한 대화 시스템입니다."
            if photo_info:
                system_content += f" 현재 사진 정보: 파일명({photo_info.get('filename', 'N/A')}), 설명({photo_info.get('description', 'N/A')}), 위치({photo_info.get('location_name', 'N/A')}), 태그({', '.join(photo_info.get('tags', []))})"
            
            message_history = [{"role": "system", "content": system_content}]
            
            # 기존 대화 내용 추가
            if conversations_response.data:
                for conv in conversations_response.data:
                    if conv.get("ai_output"):
                        message_history.append({
                            "role": "assistant", 
                            "content": conv["ai_output"]
                        })
                    if conv.get("user_input"):
                        message_history.append({
                            "role": "user", 
                            "content": conv["user_input"]
                        })
            
            state["message_history"] = message_history
            state["intermediate"] = {"cache_score": None, "routing_decision": ""}
            state["output"] = {"response_text": "", "response_audio_url": None}
            
            # photo_info, session_id, CIST 정보를 상태에 저장
            if photo_info:
                state["photo_info"] = photo_info
            state["session_id"] = session_id
            state["cist_progress"] = cist_progress
            state["current_cist_category"] = next_cist_category
            
        except Exception as e:
            print(f"Database operation failed: {e}")
            # 에러시 기본 상태 설정
            system_content = "당신은 치매 진단을 위한 따뜻한 대화 시스템입니다."
            state["message_history"] = [{"role": "system", "content": system_content}]
            state["intermediate"] = {"cache_score": None, "routing_decision": ""}
            state["output"] = {"response_text": "", "response_audio_url": None}
            state["cist_progress"] = {"time_orientation": False, "registration": False, "recall": False, "naming": False}
            state["current_cist_category"] = "time_orientation"
            state["session_id"] = conversation_id
        
        return state
    
    def router_node(self, state: GraphState) -> GraphState:
        """라우터 노드: CIST 진행 상태에 따른 대화 분기 결정"""
        user_message = state["input_data"]["user_message"]
        current_cist_category = state.get("current_cist_category", "standard")
        cist_progress = state.get("cist_progress", {})
        session_id = state.get("session_id")
        
        print(f"🎯 라우터 결정 - 현재 CIST 카테고리: {current_cist_category}")
        print(f"🎯 현재 진행 상태: {cist_progress}")
        
        # 메모리 캐시를 우선 사용하여 동기화 문제 해결
        if session_id:
            try:
                # 메모리 캐시에서 완료 상태 조회
                cached_progress = self._get_cached_cist_progress(session_id)
                print(f"🔍 캐시에서 완료된 CIST 카테고리: {cached_progress}")
                
                # 메모리 캐시 상태를 현재 상태에 병합 (완료된 것은 되돌리지 않음)
                for category in ["time_orientation", "registration", "recall", "naming"]:
                    if cached_progress.get(category, False):
                        cist_progress[category] = True
                        print(f"🔄 {category} 캐시에서 동기화: 완료됨")
                
                # 동기화된 상태로 다음 카테고리 재계산
                current_cist_category = self._get_next_cist_category(cist_progress)
                state["current_cist_category"] = current_cist_category
                state["cist_progress"] = cist_progress
                
                # 캐시 업데이트
                self._session_cist_cache[session_id] = cist_progress
                
            except Exception as e:
                print(f"❌ CIST 상태 캐시 동기화 실패: {e}")
        
        # CIST 카테고리에 따른 분기 결정
        if current_cist_category in ["time_orientation", "registration", "recall", "naming"]:
            # 해당 카테고리가 이미 완료되었는지 확인
            if cist_progress.get(current_cist_category, False):
                print(f"⏭️  {current_cist_category} 이미 완료됨, standard로 진행")
                routing_decision = "standard"
            else:
                # 대화 횟수 제한 (너무 빠른 CIST 질문 방지)
                message_count = len(state.get("message_history", []))
                if message_count < 3:  # 처음 2번은 일반 대화
                    print(f"🔄 초기 대화 단계 ({message_count}회), standard로 변경")
                    routing_decision = "standard"
                else:
                    print(f"🎯 {current_cist_category} CIST 질문 진행")
                    routing_decision = current_cist_category
        else:
            print("💬 일반 대화 진행")
            routing_decision = "standard"
        
        # 모든 CIST 카테고리 완료 시 standard로 강제 설정
        all_completed = all(cist_progress.get(cat, False) for cat in ["time_orientation", "registration", "recall", "naming"])
        if all_completed and routing_decision != "standard":
            print("✅ 모든 CIST 카테고리 완료, standard 대화로 전환")
            routing_decision = "standard"
        
        state["intermediate"]["routing_decision"] = routing_decision
        print(f"✅ 라우팅 결정: {routing_decision}")
        
        return state
    
    def standard_response_node(self, state: GraphState) -> GraphState:
        """일반 응답 생성 노드: 자연스러운 일상 대화"""
        print("💬 Standard 응답 노드 시작")
        user_message = state["input_data"]["user_message"]
        photo_context = state["input_data"]["photo_context"]
        photo_info = state.get("photo_info", {})
        
        # 사진 정보 포함한 컨텍스트 구성
        photo_description = ""
        if photo_info:
            # 기본 사진 정보
            basic_info = f"사진 정보: {photo_info.get('description', '')}, 위치: {photo_info.get('location_name', '')}, 태그: {', '.join(photo_info.get('tags', []))}"
            
            # 분석 결과 추가
            analyze_result = photo_info.get('photo_analyze_result')
            if analyze_result:
                analysis_info = []
                if analyze_result.get('caption'):
                    analysis_info.append(f"분석 설명: {analyze_result['caption']}")
                if analyze_result.get('mood'):
                    analysis_info.append(f"분위기: {analyze_result['mood']}")
                if analyze_result.get('key_objects'):
                    analysis_info.append(f"주요 객체: {', '.join(analyze_result['key_objects'])}")
                if analyze_result.get('people_description'):
                    analysis_info.append(f"인물: {analyze_result['people_description']}")
                if analyze_result.get('time_of_day'):
                    analysis_info.append(f"시간대: {analyze_result['time_of_day']}")
                
                if analysis_info:
                    photo_description = f"{basic_info}\n분석 결과: {', '.join(analysis_info)}"
                else:
                    photo_description = basic_info
            else:
                photo_description = basic_info
        
        conversation_prompt = f"""
        사용자와 자연스럽고 따뜻한 대화를 나누세요.
        
        사용자 메시지: {user_message}
        {photo_description}
        
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
            print(f"✅ Standard 응답 생성 완료: {response.content.strip()[:50]}...")
            
        except Exception as e:
            print(f"❌ Standard response generation failed: {e}")
            state["output"]["response_text"] = "죄송합니다. 다시 말씀해 주시겠어요?"
        
        print("💬 Standard 응답 노드 완료")
        return state
    
    def cache_retrieve_and_evaluate_node(self, state: GraphState) -> GraphState:
        """캐시 검색 및 평가 노드: 인지기능 평가 질문 검색"""
        user_message = state["input_data"]["user_message"]
        
        try:
            # Supabase에서 CIST 질문 템플릿 검색
            response = self.supabase.table("cist_question_templates").select(
                "*"
            ).limit(5).execute()
            
            if response.data:
                # 간단한 유사도 평가 (실제로는 벡터 DB 사용 권장)
                best_question = response.data[0]
                cache_score = 0.9  # 임시 점수
                
                state["intermediate"]["cache_score"] = cache_score
                state["output"]["response_text"] = best_question["template_text"]
            else:
                state["intermediate"]["cache_score"] = 0.3  # 낮은 점수
                
        except Exception as e:
            print(f"Cache retrieval failed: {e}")
            state["intermediate"]["cache_score"] = 0.3
        
        return state
    
    def fallback_node(self, state: GraphState) -> GraphState:
        """대체 응답 처리 노드: 경량 LLM으로 응답 생성"""
        user_message = state["input_data"]["user_message"]
        conversation_id = state["input_data"]["conversation_id"]
        photo_context = state["input_data"]["photo_context"]
        photo_info = state.get("photo_info", {})
        
        # 사진 분석 결과 요약 (fallback용 간단 버전)
        photo_context_text = ""
        if photo_info:
            analyze_result = photo_info.get('photo_analyze_result')
            if analyze_result:
                context_parts = []
                if analyze_result.get('caption'):
                    context_parts.append(f"사진: {analyze_result['caption'][:50]}...")
                if analyze_result.get('mood'):
                    context_parts.append(f"분위기: {analyze_result['mood']}")
                
                if context_parts:
                    photo_context_text = f"\n참고: {', '.join(context_parts)}"
        
        fallback_prompt = f"""
        간단하고 따뜻한 응답을 생성하세요.
        
        사용자 메시지: {user_message}{photo_context_text}
        
        30자 이내로 공감하며 답변해주세요.
        """
        
        try:
            response = self.llm_nano.invoke([
                SystemMessage(content=fallback_prompt),
                HumanMessage(content=user_message)
            ])
            
            state["output"]["response_text"] = response.content.strip()
            
            # 백그라운드에서 고품질 질문 생성 요청
            self._schedule_background_task(user_message, conversation_id, photo_context)
            
        except Exception as e:
            print(f"Fallback response failed: {e}")
            state["output"]["response_text"] = "네, 알겠습니다."
        
        return state
    
    def time_orientation_node(self, state: GraphState) -> GraphState:
        """시간지남력 평가 노드"""
        return self._generate_cist_response(state, "time_orientation", 
            "현재 시간, 날짜, 계절 등의 시간적 지향력을 평가하는 질문")
    
    def registration_node(self, state: GraphState) -> GraphState:
        """기억 등록 평가 노드"""
        return self._generate_cist_response(state, "registration",
            "새로운 정보를 기억하고 저장하는 능력을 평가하는 질문")
    
    def recall_node(self, state: GraphState) -> GraphState:
        """회상 평가 노드"""
        return self._generate_cist_response(state, "recall",
            "이전에 학습한 정보를 기억해내는 능력을 평가하는 질문")
    
    def naming_node(self, state: GraphState) -> GraphState:
        """명명 평가 노드"""
        return self._generate_cist_response(state, "naming",
            "사물의 이름을 정확히 기억하고 표현하는 능력을 평가하는 질문")
    
    def _generate_cist_response(self, state: GraphState, category: str, description: str) -> GraphState:
        """CIST 카테고리별 질문 생성"""
        user_message = state["input_data"]["user_message"]
        photo_info = state.get("photo_info", {})
        
        # 사진 정보 포함한 컨텍스트 구성
        photo_context = ""
        if photo_info:
            photo_context = f"사진 정보: {photo_info.get('description', '')} "
            if photo_info.get('tags'):
                photo_context += f"태그: {photo_info['tags']} "
        
        # 카테고리별 질문 프롬프트
        category_prompts = {
            "time_orientation": f"""
            {photo_context}
            
            현재 대화의 맥락에서 시간지남력을 평가할 수 있는 자연스러운 질문을 1개 만들어주세요.
            
            예시:
            - "지금이 몇 시인지 알 수 있나요?"
            - "오늘이 며칠인지 기억하시나요?"
            - "지금이 무슨 계절인지 알려주세요."
            
            사진과 연관지어 자연스럽게 질문해주세요.
            """,
            
            "registration": f"""
            {photo_context}
            
            기억 등록 능력을 평가할 수 있는 자연스러운 질문을 1개 만들어주세요.
            
            예시:
            - "제가 지금 말씀드리는 3가지 단어를 기억해주세요: 사과, 자동차, 연필"
            - "이 사진에서 보이는 것들을 기억해두시고, 나중에 물어볼게요."
            
            사진 내용과 연관지어 기억할 수 있는 정보를 제시해주세요.
            """,
            
            "recall": f"""
            {photo_context}
            
            회상 능력을 평가할 수 있는 자연스러운 질문을 1개 만들어주세요.
            
            예시:
            - "아까 제가 말씀드린 3가지 단어가 무엇이었는지 기억나시나요?"
            - "이 사진을 찍었을 때 함께 있던 사람이 누구였는지 기억하시나요?"
            
            이전 대화나 사진과 관련된 정보의 회상을 요청해주세요.
            """,
            
            "naming": f"""
            {photo_context}
            
            명명 능력을 평가할 수 있는 자연스러운 질문을 1개 만들어주세요.
            
            예시:
            - "이 사진에 보이는 이것의 이름이 무엇인지 말씀해주세요."
            - "이 꽃의 이름을 아시나요?"
            - "이 동물의 이름이 무엇인지 알려주세요."
            
            사진 속 사물, 동물, 장소 등의 이름을 묻는 질문을 해주세요.
            """
        }
        
        try:
            prompt = category_prompts.get(category, "적절한 질문을 만들어주세요.")
            
            response = self.llm.invoke([
                SystemMessage(content="당신은 치매 진단을 위한 전문 상담사입니다. 자연스럽고 따뜻한 대화로 인지기능을 평가합니다."),
                HumanMessage(content=prompt)
            ])
            
            state["output"]["response_text"] = response.content.strip()
            print(f"✅ {category} 질문 생성 완료")
            
        except Exception as e:
            print(f"❌ {category} 질문 생성 실패: {e}")
            state["output"]["response_text"] = f"사진에 대해 더 자세히 이야기해주세요."
        
        return state
    
    def _evaluate_cist_response(self, user_message: str, category: str, expected_answer: str = None) -> int:
        """CIST 응답 평가 (0 또는 1 반환)"""
        try:
            # 카테고리별 평가 기준
            evaluation_prompts = {
                "time_orientation": f"""
                사용자의 답변을 분석하여 시간지남력이 정상인지 평가해주세요.
                
                사용자 답변: {user_message}
                
                다음 기준으로 평가:
                - 현재 시간, 날짜, 계절을 정확히 알고 있으면 → 1
                - 대략적으로라도 맞는 범위에서 답변하면 → 1  
                - 완전히 틀렸거나 모른다고 하면 → 0
                
                0 또는 1로만 답하세요.
                """,
                
                "registration": f"""
                사용자의 답변을 분석하여 새로운 정보 기억 등록 능력을 평가해주세요.
                
                사용자 답변: {user_message}
                
                다음 기준으로 평가:
                - 제시된 정보를 정확히 기억하겠다고 하면 → 1
                - 기억하려고 노력하는 모습을 보이면 → 1
                - 기억할 수 없다거나 거부하면 → 0
                
                0 또는 1로만 답하세요.
                """,
                
                "recall": f"""
                사용자의 답변을 분석하여 이전 정보 회상 능력을 평가해주세요.
                
                사용자 답변: {user_message}
                예상 답변: {expected_answer or "이전에 제시된 정보"}
                
                다음 기준으로 평가:
                - 이전 정보를 정확히 기억해내면 → 1
                - 부분적으로라도 기억해내면 → 1
                - 완전히 기억하지 못하면 → 0
                
                0 또는 1로만 답하세요.
                """,
                
                "naming": f"""
                사용자의 답변을 분석하여 사물 명명 능력을 평가해주세요.
                
                사용자 답변: {user_message}
                
                다음 기준으로 평가:
                - 사물의 이름을 정확히 말하면 → 1
                - 비슷한 표현이나 설명으로라도 의미를 전달하면 → 1
                - 완전히 모르거나 틀린 답변을 하면 → 0
                
                0 또는 1로만 답하세요.
                """
            }
            
            prompt = evaluation_prompts.get(category, "답변의 적절성을 0 또는 1로 평가해주세요.")
            
            response = self.llm_mini.invoke([
                SystemMessage(content="당신은 치매 진단 전문가입니다. 답변을 객관적으로 평가합니다."),
                HumanMessage(content=prompt)
            ])
            
            # 응답에서 숫자만 추출
            score_text = response.content.strip()
            if "1" in score_text:
                score = 1
            elif "0" in score_text:
                score = 0
            else:
                score = 0  # 기본값
            
            print(f"🔍 {category} 평가 결과: {score} (답변: {user_message[:50]}...)")
            return score
            
        except Exception as e:
            print(f"❌ CIST 평가 실패: {e}")
            return 0  # 에러시 기본값
    
    def _schedule_background_task(self, user_message: str, conversation_id: str, photo_context: dict):
        """Celery를 통한 백그라운드 작업 스케줄링"""
        try:
            from tasks import generate_high_quality_questions
            
            context = {
                "user_message": user_message,
                "conversation_id": conversation_id, 
                "photo_context": photo_context
            }
            
            # 비동기 작업 발행
            generate_high_quality_questions.delay(context)
            print(f"Background task scheduled for conversation: {conversation_id}")
            
        except Exception as e:
            print(f"Failed to schedule background task: {e}")
    
    def _route_decision(self, state: GraphState) -> str:
        """라우터 결정에 따른 경로 선택"""
        routing_decision = state["intermediate"]["routing_decision"]
        print(f"🔀 라우팅 결정 실행: {routing_decision}")
        return routing_decision
    
    def _cache_decision(self, state: GraphState) -> str:
        """캐시 점수에 따른 경로 선택"""
        cache_score = state["intermediate"]["cache_score"]
        if cache_score and cache_score >= 0.85:
            return "use_cache"
        return "use_fallback"
    
    async def _save_conversation_to_db(self, state: GraphState, authenticated_client: Client = None) -> None:
        """대화 내용을 DB에 저장"""
        try:
            # 인증된 클라이언트가 있으면 사용, 없으면 기본 클라이언트 사용
            client = authenticated_client if authenticated_client else self.supabase
            
            session_id = state.get("session_id")
            user_message = state["input_data"]["user_message"]
            ai_response = state["output"]["response_text"]
            photo_context = state["input_data"]["photo_context"]
            user_id = state["input_data"]["user_id"]
            
            print(f"💾 대화 저장 시도: session_id={session_id}, user_id={user_id}")
            
            if not session_id:
                print("❌ session_id 없음, 대화 저장 건너뜀")
                return
            
            # 다음 conversation_order 계산
            count_response = client.table("conversations").select(
                "conversation_order"
            ).eq("session_id", session_id).execute()
            
            next_order = len(count_response.data) + 1 if count_response.data else 1
            print(f"📊 대화 순서: {next_order}")
            
            # CIST 정보 확인
            current_cist_category = state.get("current_cist_category")
            routing_decision = state["intermediate"].get("routing_decision", "standard")
            is_cist_question = routing_decision in ["time_orientation", "registration", "recall", "naming"]
            
            # 대화 레코드 생성
            conversation_data = {
                "session_id": session_id,
                "user_id": user_id,
                "photo_id": photo_context.get("photo_id"),
                "conversation_order": next_order,
                "ai_output": ai_response,
                "question_type": "open_ended",  # 기본값
                "user_input": user_message,
                "is_cist_item": is_cist_question,
                "cist_category": routing_decision if is_cist_question else None,
                "cist_score": None  # 초기값, 사용자 응답 시 업데이트됨
            }
            
            # CIST 질문에 대한 사용자 응답인 경우 점수 평가
            if is_cist_question and user_message and user_message != "안녕하세요! 이 사진에 대해 이야기해보세요.":
                cist_score = self._evaluate_cist_response(user_message, routing_decision)
                conversation_data["cist_score"] = cist_score
                print(f"🔍 CIST 평가 완료: {routing_decision} = {cist_score}")
                
                # CIST 진행 상태 즉시 업데이트 (점수와 관계없이 해당 카테고리는 완료로 처리)
                if routing_decision in ["time_orientation", "registration", "recall", "naming"]:
                    # 메모리 상태 업데이트
                    state["cist_progress"][routing_decision] = True
                    print(f"🔄 메모리 상태 즉시 업데이트: {routing_decision} = 완료")
                    
                    # 메모리 캐시도 업데이트
                    if session_id:
                        self._update_cached_cist_progress(session_id, routing_decision, True)
                    
                    # 다음 CIST 카테고리 업데이트
                    next_cist_category = self._get_next_cist_category(state["cist_progress"])
                    state["current_cist_category"] = next_cist_category
                    print(f"✅ {routing_decision} 완료, 다음 카테고리: {next_cist_category}")
                    
                    # 모든 CIST 완료 확인
                    all_completed = all(state["cist_progress"].get(cat, False) for cat in ["time_orientation", "registration", "recall", "naming"])
                    if all_completed:
                        print("🎉 모든 CIST 카테고리 완료! 이후 일반 대화만 진행됩니다.")
            
            print(f"💾 CIST 정보: category={conversation_data['cist_category']}, score={conversation_data['cist_score']}, is_cist={conversation_data['is_cist_item']}")
            
            # 오디오 URL이 있으면 추가
            audio_url = state["input_data"].get("audio_url")
            if audio_url:
                conversation_data["user_response_audio_url"] = audio_url
                print(f"🎤 오디오 URL 추가: {audio_url}")
            
            print(f"📝 대화 데이터: {conversation_data}")
            
            insert_response = client.table("conversations").insert(conversation_data).execute()
            if insert_response.data:
                print(f"✅ 대화 저장 성공: {insert_response.data[0]['id']}")
                
                # CIST 완료 상태를 즉시 DB에 반영 (동기화 보장)
                if is_cist_question and routing_decision in ["time_orientation", "registration", "recall", "naming"]:
                    # DB 커밋 완료를 위한 짧은 대기
                    import asyncio
                    await asyncio.sleep(0.1)
                    print(f"🔄 CIST 완료 상태 DB 동기화 완료: {routing_decision}")
            else:
                print("❌ 대화 저장 실패: 응답 데이터 없음")
                
        except Exception as e:
            print(f"❌ 대화 저장 DB 오류: {type(e).__name__}: {str(e)}")
            # 디버깅을 위해 상세 오류 정보 출력
            import traceback
            print(f"📋 상세 오류: {traceback.format_exc()}")

    async def process_message(self, input_data: WorkflowInput, authenticated_client: Client = None) -> FinalOutput:
        """메시지 처리 진입점"""
        initial_state = {
            "input_data": input_data,
            "message_history": [],
            "intermediate": {"cache_score": None, "routing_decision": ""},
            "output": {"response_text": "", "response_audio_url": None},
            "photo_info": None,
            "session_id": None,
            "_authenticated_client": authenticated_client,
            "cist_progress": None,
            "current_cist_category": None
        }
        
        try:
            print(f"🚀 워크플로우 시작: conversation_id={input_data['conversation_id']}")
            print(f"📊 초기 상태: {initial_state.keys()}")
            
            final_state = await self.app.ainvoke(initial_state)
            print(f"✅ 워크플로우 완료: conversation_id={input_data['conversation_id']}")
            print(f"📊 최종 상태: response_text={bool(final_state['output']['response_text'])}")
            
            # 대화 내용을 DB에 저장
            if final_state["output"]["response_text"]:
                try:
                    await self._save_conversation_to_db(final_state, authenticated_client)
                    print("✅ 대화 DB 저장 완료")
                except Exception as db_error:
                    print(f"❌ 대화 DB 저장 실패: {db_error}")
                    # 대화 저장 실패해도 응답은 전송
            else:
                print("⚠️ 응답 텍스트가 비어있어 DB 저장 생략")
            
            return final_state["output"]
        except Exception as e:
            import traceback
            print(f"❌ 워크플로우 실행 실패: conversation_id={input_data['conversation_id']}, error={e}")
            print(f"📋 상세 오류: {traceback.format_exc()}")
            
            # CIST 완료 후 standard 라우팅 에러인지 확인
            error_str = str(e).lower()
            if "standard" in error_str or "routing" in error_str:
                print("🔧 Standard 라우팅 에러로 추정, fallback 응답 제공")
                fallback_response = "네, 알겠습니다. 다른 이야기를 해보시겠어요?"
            else:
                fallback_response = "죄송합니다. 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            
            return {
                "response_text": fallback_response,
                "response_audio_url": None
            }