from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import os
from supabase import create_client, Client
import uuid
from datetime import datetime

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
    photo_info: Optional[Dict[str, Any]]  # 사진 정보 저장
    session_id: Optional[str]  # 세션 ID 저장
    _authenticated_client: Optional[Client]  # 인증된 Supabase 클라이언트

class DialogueWorkflow:
    """LangGraph 기반 대화 워크플로우 시스템"""
    
    def __init__(self):
        # 필수 환경 변수 검증
        openai_key = os.getenv("OPENAI_API_KEY")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not openai_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not supabase_url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not supabase_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is required")
        
        try:
            self.llm_mini = ChatOpenAI(
                model="gpt-5-mini",  # 실제 존재하는 모델로 변경
                api_key=openai_key
            )
            self.llm_nano = ChatOpenAI(
                model="gpt-5-nano",  # 경량 모델로 gpt-3.5-turbo 사용
                max_tokens=256,
                api_key=openai_key
            )
            print("OpenAI LLM clients initialized successfully")
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
                        print(f"📷 사진 정보 로드됨: {photo_info}")
                except Exception as photo_error:
                    print(f"❌ 사진 정보 로드 실패: {photo_error}")
            
            # conversation_id를 session_id로 사용 (main.py에서 이미 세션 생성됨)
            session_id = conversation_id
            print(f"✅ 세션 ID 설정: {session_id}")
            
            # 해당 세션의 기존 대화 내역 조회
            conversations_response = client.table("conversations").select(
                "id, question_text, user_response_text, conversation_order"
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
                    if conv.get("question_text"):
                        message_history.append({
                            "role": "assistant", 
                            "content": conv["question_text"]
                        })
                    if conv.get("user_response_text"):
                        message_history.append({
                            "role": "user", 
                            "content": conv["user_response_text"]
                        })
            
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
    
    def router_node(self, state: GraphState) -> GraphState:
        """라우터 노드: 인지기능 평가 질문 삽입 여부 결정"""
        user_message = state["input_data"]["user_message"]
        message_history = state["message_history"]
        
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
                routing_decision = "standard_chat"  # 기본값
                
            state["intermediate"]["routing_decision"] = routing_decision
            
        except Exception as e:
            print(f"Router decision failed: {e}")
            state["intermediate"]["routing_decision"] = "standard_chat"
        
        return state
    
    def standard_response_node(self, state: GraphState) -> GraphState:
        """일반 응답 생성 노드: 자연스러운 일상 대화"""
        user_message = state["input_data"]["user_message"]
        photo_context = state["input_data"]["photo_context"]
        photo_info = state.get("photo_info", {})
        
        # 사진 정보 포함한 컨텍스트 구성
        photo_description = ""
        if photo_info:
            photo_description = f"사진 정보: {photo_info.get('description', '')}, 위치: {photo_info.get('location_name', '')}, 태그: {', '.join(photo_info.get('tags', []))}"
        
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
            
        except Exception as e:
            print(f"Standard response generation failed: {e}")
            state["output"]["response_text"] = "죄송합니다. 다시 말씀해 주시겠어요?"
        
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
            
            # 대화 레코드 생성
            conversation_data = {
                "session_id": session_id,
                "user_id": user_id,
                "photo_id": photo_context.get("photo_id"),
                "conversation_order": next_order,
                "question_text": ai_response,
                "question_type": "open_ended",  # 기본값
                "user_response_text": user_message,
                "is_cist_item": False
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