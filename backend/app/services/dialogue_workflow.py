import os
import uuid
import random
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from supabase import create_client, Client

import sys
sys.path.append('/app')
from core.config import settings
from services.dialogue_prompt import TIME_ORIENTATION_PROMPT, NAMING_PROMPT, ROUTER_PROMPT, STANDARD_PROMPT, AFTER_NAMING_PROMPT, LIGHT_STANDARD_PROMPT

class WorkflowInput(TypedDict):
    """그래프 실행을 위해 외부에서 주입되는 초기 데이터"""
    conversation_id: str
    user_id: str
    user_message: str
    photo_context: Dict[str, Any]
    # conversation_history: Optional[List[Dict[str, str]]]  # 메모리 히스토리 지원

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

class DialogueWorkflow:
    """LangGraph 기반 대화 워크플로우 시스템"""
    
    ### 임시 테스트용 사진 정보 상수 ### 
    TEMP_PHOTO_INFO = {
        "id": str(uuid.uuid4()),
        "filename": "test_beach_photo.jpg",
        "description": "사진 속에는 어린 소년이 해변에서 모래성을 쌓고 있습니다. 맑은 파란 바다가 배경에 펼쳐져 있고, 하얀 모래사장 위에는 작은 조개껍질들이 흩어져 있습니다. 소년은 빨간 티셔츠를 입고 있으며, 집중해서 모래성을 만들고 있는 모습입니다.",
        "tags": ["해변", "모래성", "어린이", "바다", "여름휴가"],
        "location_name": "부산 해운대 해수욕장",
        "naming_objects": [
            {"item": "모래성", "location": "소년 앞 바닥에", "context": "놀이 중심 아이템"},
            {"item": "삽", "location": "손에 들고 있음", "context": "모래성을 쌓는 도구"},
            {"item": "바다", "location": "배경", "context": "푸른 바다 풍경"},
            {"item": "조개껍질", "location": "모래사장 곳곳", "context": "자연물"},
            {"item": "빨간 티셔츠", "location": "소년이 입고 있음", "context": "의류"}
        ],
        "photo_year": 2000
    }
    ### 임시 테스트용 사진 정보 상수 ###
    
    def __init__(self):
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
        workflow.add_node("orientation_naming", self.orientation_naming_node)
        workflow.add_node("router", self.router_node)
        workflow.add_node("standard_response", self.standard_response_node)
        workflow.add_node("bridge", self.bridge_generation_node)
        workflow.add_node("cache_retrieve", self.cache_retrieve_and_evaluate_node)
        workflow.add_node("fallback", self.fallback_node)
        
        # 진입점 설정
        workflow.set_entry_point("init_state")
        
        # 엣지 정의
        workflow.add_conditional_edges(
            "init_state",
            self._should_orientation_naming,
            {
                "orientation_naming": "orientation_naming",
                "router": "router"
            }
        )
        workflow.add_edge("orientation_naming", END)
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
                "use_cache": "bridge", 
                "use_fallback": "fallback"
            }
        )
        workflow.add_edge("bridge", END)
        workflow.add_edge("fallback", END)
        
        return workflow.compile()
    
    
    def init_state_node(self, state: GraphState) -> GraphState:
        """상태 초기화 노드: DB에서 대화 기록 및 사진 정보 조회"""
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
                        "id, filename, file_path, description, tags, location_name"
                    ).eq("id", photo_context["photo_id"]).single().execute()
                    
                    if photo_response.data:
                        photo_info = photo_response.data
                        ###  DB에서 로드된 사진에도 naming_objects 추가 (임시) ###
                        if not photo_info.get("naming_objects"):
                            photo_info["naming_objects"] = self.TEMP_PHOTO_INFO["naming_objects"]
                            photo_info["photo_year"] = self.TEMP_PHOTO_INFO["photo_year"]
                        ###  DB에서 로드된 사진에도 naming_objects 추가 (임시) ###

                        print(f"📷 사진 정보 로드됨: {photo_info}")
                except Exception as photo_error:
                    print(f"❌ 사진 정보 로드 실패: {photo_error}")
            

            ### 임시 테스트용 사진 정보 (실제 DB에서 조회 실패시 사용) ###
            if not photo_info:
                photo_info = self.TEMP_PHOTO_INFO.copy()  # 복사본 생성
                photo_info["id"] = str(uuid.uuid4())  # 새 ID 생성
                print(f"📷 임시 사진 정보 사용: {photo_info['filename']}")
            ### 임시 테스트용 사진 정보 ###


            # conversation_id를 session_id로 사용 (main.py에서 이미 세션 생성됨)
            session_id = conversation_id
            print(f"✅ 세션 ID 설정: {session_id}")
            
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
            
            # 현재 사용자 메시지를 히스토리에 추가
            current_user_message = state["input_data"]["user_message"]
            message_history.append({"role": "user", "content": current_user_message})
            
            state["message_history"] = message_history
            state["intermediate"] = {"cache_score": None, "routing_decision": ""}
            state["output"] = {"response_text": "", "response_audio_url": None}
            
            # photo_info와 session_id를 상태에 저장
            if photo_info:
                state["photo_info"] = photo_info
            state["session_id"] = session_id
            
        except Exception as e:
            print(f"Database operation failed: {e}")
            # 에러시 기본 상태 설정
            system_content = "당신은 치매 진단을 위한 따뜻한 대화 시스템입니다."
            state["message_history"] = [{"role": "system", "content": system_content}]
            state["intermediate"] = {"cache_score": None, "routing_decision": ""}
            state["output"] = {"response_text": "", "response_audio_url": None}
            state["session_id"] = conversation_id
        
        return state

    def orientation_naming_node(self, state: GraphState) -> GraphState:
        """시간지남력(1턴) 또는 이름대기(2턴) 평가 노드"""
        
        message_history = state.get("message_history", [])
        user_turns = sum(1 for msg in message_history if msg.get("role") == "user")
        photo_info = state.get("photo_info", {})
        
        print(f"🎯 orientation_naming_node: user_turns={user_turns}")
        
        # CIST 결과 리스트로 관리
        if not hasattr(self, 'cist_results'):
            self.cist_results = []
        
        try:
            if user_turns == 1:  # 1턴: 시간 지남력 (Rule-based)
                print("🕐 1턴 - 시간지남력 질문 생성 시작")
                current_date = datetime.now()
                current_year = current_date.year
                current_month = current_date.month
                current_day = current_date.day
                
                # TIME_ORIENTATION_PROMPT 사용하여 질문 생성
                time_question = TIME_ORIENTATION_PROMPT.format(
                    current_year=current_year,
                    current_month=current_month
                )
                state["output"]["response_text"] = time_question
                print(f"✅ 시간지남력 질문 생성 완료: {time_question}")
                
                # CIST 결과를 리스트에 추가
                cist_item = {
                    "cist_category": "time_orientation",
                    "assessment_question": time_question,  # Rule-based 생성 질문
                    "user_answer": "",  # 다음 턴에서 채워질 예정
                    "expected_answer": f"{current_day}"  # 오늘 날짜 (예: "15")
                }
                self.cist_results.append(cist_item)
                
            elif user_turns == 2:  # 2턴: 이름대기
                print("🎯 2턴 - 이름대기 질문 생성 시작")

                ### photo_info가 없거나 naming_objects가 없으면 임시 데이터 사용 ### 
                if not photo_info or not photo_info.get("naming_objects"):
                    print("⚠️ photo_info 또는 naming_objects 없음, 임시 데이터 사용")
                    photo_info = self.TEMP_PHOTO_INFO.copy()
                    photo_info["id"] = str(uuid.uuid4())
                ### photo_info가 없거나 naming_objects가 없으면 임시 데이터 사용 ### 
                
                # 사진에서 랜덤 객체 선택
                naming_objects = photo_info.get("naming_objects", [])
                print(f"🔍 naming_objects 개수: {len(naming_objects)}")
                
                if not naming_objects:
                    raise ValueError("naming_objects가 비어있습니다. TEMP_PHOTO_INFO 확인 필요")
                
                selected_object = random.choice(naming_objects)
                print(f"🎲 선택된 객체: {selected_object}")
                
                # 연도 계산
                current_year = datetime.now().year
                photo_year = int(photo_info.get("photo_year", current_year))
                years_diff = current_year - photo_year
                print(f"📅 사진 연도: {photo_year}, 현재: {current_year}, 차이: {years_diff}년")
                
                prompt_template = ChatPromptTemplate.from_template(NAMING_PROMPT)
                chain = prompt_template | self.llm_mini
                
                response = chain.invoke({
                    "photo_description": photo_info.get("description", ""),
                    "naming_objects": naming_objects,
                    "selected_object": selected_object,
                    "years_diff": years_diff
                })
                
                state["output"]["response_text"] = response.content.strip()
                print(f"✅ 이름대기 질문 생성 완료: {response.content.strip()}")
                
                # CIST 결과를 리스트에 추가
                cist_item = {
                    "cist_category": "naming",
                    "assessment_question": state["output"]["response_text"],  # AI가 생성한 질문
                    "user_answer": "",  # 다음 턴에서 채워질 예정
                    "expected_answer": selected_object["item"]  # 사물 이름
                }
                self.cist_results.append(cist_item)
                
            else:
                # 예외 상황: 3턴 이상에서는 orientation_naming에 들어오면 안됨
                print(f"⚠️ 예외 상황: {user_turns}턴에서 orientation_naming_node 호출됨")
                state["output"]["response_text"] = "죄송합니다. 처리 중 오류가 발생했습니다."
                
            # CIST 결과 리스트 확인
            print(f"🧠 누적된 CIST 결과: {len(self.cist_results)}개")
            for i, result in enumerate(self.cist_results, 1):
                print(f"   {i}. {result['cist_category']}: {result['expected_answer']}")
                
        except Exception as e:
            print(f"❌ orientation_naming_node 오류: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"❌ 상세 오류:\n{traceback.format_exc()}")
            state["output"]["response_text"] = "죄송합니다. 처리 중 오류가 발생했습니다. 다시 말씀해 주시겠어요?"
        
        return state
    
    def router_node(self, state: GraphState) -> GraphState:
        """라우터 노드: 인지기능 평가 질문 삽입 여부 결정"""
        user_message = state["input_data"]["user_message"]
        message_history = state["message_history"]
        
        # 현재 턴수 계산
        user_turns = sum(1 for msg in message_history if msg.get("role") == "user")
        
        print(f"🎯 router_node: 현재 턴수 {user_turns}턴")
        
        # 3턴의 경우 특수 규칙: 무조건 standard_chat
        if user_turns == 3:  
            print(f"   📌 3턴 특수 규칙: 무조건 standard_chat 선택")
            state["intermediate"]["routing_decision"] = "standard_chat"
            return state
        
        # 4턴 이후부터는 ROUTER_PROMPT 사용하여 일반적인 라우팅
        try:
            response = self.llm_mini.invoke([
                SystemMessage(content=ROUTER_PROMPT),
                HumanMessage(content=user_message)
            ])
            
            routing_decision = response.content.strip().lower()
            if routing_decision not in ["standard_chat", "assessment_chat"]:
                routing_decision = "standard_chat"  # 기본값
                
            print(f"   🛤️ LLM 라우팅 결정: {routing_decision}")
            state["intermediate"]["routing_decision"] = routing_decision
            
        except Exception as e:
            print(f"❌ Router decision failed: {e}")
            state["intermediate"]["routing_decision"] = "standard_chat"
        
        return state
    
    def standard_response_node(self, state: GraphState) -> GraphState:
        """일반 응답 생성 노드: 턴수에 따라 다른 프롬프트 사용"""
        user_message = state["input_data"]["user_message"]
        photo_context = state["input_data"]["photo_context"]
        photo_info = state.get("photo_info", {})
        message_history = state["message_history"]
        
        # 현재 턴수 계산
        user_turns = sum(1 for msg in message_history if msg.get("role") == "user")
        
        print(f"💬 standard_response_node: 현재 턴수 {user_turns}턴")
        
        # 3턴인 경우 AFTER_NAMING_PROMPT 사용
        if user_turns == 3:  
            print(f"   📝 3턴 전용 AFTER_NAMING_PROMPT 사용")
            
            try:
                # photo_info에서 메타데이터 구성
                photo_metadata = {
                    "description": photo_info.get("description", ""),
                    "naming_objects": photo_info.get("naming_objects", [])
                }
                
                prompt_template = ChatPromptTemplate.from_template(AFTER_NAMING_PROMPT)
                chain = prompt_template | self.llm_mini
                
                response = chain.invoke({
                    "user_message": user_message,
                    "photo_metadata": photo_metadata,
                    "message_history": message_history
                })
                
                state["output"]["response_text"] = response.content.strip()
                
            except Exception as e:
                print(f"❌ AFTER_NAMING_PROMPT 처리 실패: {e}")
                state["output"]["response_text"] = "정말 좋네요! 이 사진에 대해 더 이야기해볼까요?"
        
        # 4턴 이후는 STANDARD_PROMPT 사용
        else:
            print(f"📝 일상 대화용 STANDARD_PROMPT 사용")
            
            try:
                # 사진 정보 포함한 컨텍스트 구성
                photo_description = ""
                if photo_info:
                    photo_description = f"사진 정보: {photo_info.get('description', '')}, 위치: {photo_info.get('location_name', '')}, 태그: {', '.join(photo_info.get('tags', []))}"
                
                prompt_template = ChatPromptTemplate.from_template(STANDARD_PROMPT)
                chain = prompt_template | self.llm_mini
                
                response = chain.invoke({
                    "user_message": user_message,
                    "photo_description": photo_description,
                    "message_history": message_history
                })
                
                state["output"]["response_text"] = response.content.strip()
                
            except Exception as e:
                print(f"❌ STANDARD_PROMPT 처리 실패: {e}")
                state["output"]["response_text"] = "그렇군요. 더 자세히 이야기해 주실 수 있나요?"
        
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
    
    
    def bridge_generation_node(self, state: GraphState) -> GraphState:
        pass


    def fallback_node(self, state: GraphState) -> GraphState:
        """대체 응답 처리 노드: 경량 LLM으로 응답 생성"""
        user_message = state["input_data"]["user_message"]
        conversation_id = state["input_data"]["conversation_id"]
        photo_context = state["input_data"]["photo_context"]
        
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
            
            # 백그라운드에서 고품질 질문 생성 요청
            self._schedule_background_task(user_message, conversation_id, photo_context)
            
        except Exception as e:
            print(f"Fallback response failed: {e}")
            state["output"]["response_text"] = "네, 알겠습니다."
        
        return state
    
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
        return state["intermediate"]["routing_decision"]
    

    def _should_orientation_naming(self, state: GraphState) -> str:
        """대화 1~2턴 반드시 orientation_naming 진입"""
        message_history = state.get("message_history", [])
        
        # user 메시지 개수로 턴수 계산 (현재 메시지 포함)
        user_turns = sum(1 for msg in message_history if msg.get("role") == "user")
        
        print(f"🔍 현재 턴수: {user_turns}턴")
        
        # 1-2턴에서만 orientation_naming으로 진입 (현재 메시지 포함하여 계산)
        if user_turns <= 2:
            print(f"   ➡️ orientation_naming 노드로 진입")
            return "orientation_naming"
        else:
            print(f"   ➡️ router 노드로 진입")
            return "router"
    
    
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
            
            # 대화 레코드 생성 (실제 DB 스키마에 맞게)
            conversation_data = {
                "session_id": session_id,
                "user_id": user_id,
                "photo_id": photo_context.get("photo_id"),
                "conversation_order": next_order,
                "ai_output": ai_response,
                "question_type": "open_ended",  # 기본값
                "user_input": user_message,
                "is_cist_item": False  # 기본값
            }
            
            print(f"📝 대화 데이터: {conversation_data}")
            
            insert_response = client.table("conversations").insert(conversation_data).execute()
            if insert_response.data:
                print(f"✅ 대화 저장 성공: {insert_response.data[0]['id']}")
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
            "_authenticated_client": authenticated_client
        }
        
        try:
            print(f"🚀 워크플로우 시작: conversation_id={input_data['conversation_id']}")
            
            final_state = await self.app.ainvoke(initial_state)
            print(f"✅ 워크플로우 완료: conversation_id={input_data['conversation_id']}")
            
            # 대화 내용을 DB에 저장
            if final_state["output"]["response_text"]:
                try:
                    await self._save_conversation_to_db(final_state, authenticated_client)
                    print("✅ 대화 DB 저장 완료")
                except Exception as db_error:
                    print(f"❌ 대화 DB 저장 실패: {db_error}")
                    # 대화 저장 실패해도 응답은 전송
            
            return final_state["output"]
        except Exception as e:
            import traceback
            print(f"❌ 워크플로우 실행 실패: conversation_id={input_data['conversation_id']}, error={e}")
            print(f"📋 상세 오류: {traceback.format_exc()}")
            return {
                "response_text": "죄송합니다. 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                "response_audio_url": None
            }
        