"""
Celery 비동기 작업 처리
고품질 질문 생성 및 캐시 저장을 백그라운드에서 처리
"""
from celery import Celery
import os
from supabase import create_client
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Celery 앱 초기화
rabbitmq_user = os.getenv('RABBITMQ_USER', 'admin')
rabbitmq_pass = os.getenv('RABBITMQ_PASS', 'password')
rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
redis_host = os.getenv('REDIS_HOST', 'localhost')

celery_app = Celery(
    'dialogue_tasks',
    broker=f"pyamqp://{rabbitmq_user}:{rabbitmq_pass}@{rabbitmq_host}:5672//",
    backend=f"redis://{redis_host}:6379/0"
)

# Supabase 클라이언트 초기화
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

# LLM 초기화 (고품질 모델) with LangSmith 지원
langsmith_tracing = os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
langsmith_metadata = {
    "service": "background_tasks",
    "version": "1.0", 
    "environment": os.getenv("ENVIRONMENT", "development")
}

llm_high_quality = ChatOpenAI(
    model="gpt-4",
    api_key=os.getenv("OPENAI_API_KEY"),
    metadata=langsmith_metadata if langsmith_tracing else None
)

@celery_app.task
def generate_high_quality_questions(conversation_context: dict):
    """
    백그라운드에서 고품질 인지기능 평가 질문 생성
    """
    try:
        user_message = conversation_context.get("user_message", "")
        photo_context = conversation_context.get("photo_context", {})
        conversation_id = conversation_context.get("conversation_id", "")
        
        prompt = f"""
        다음 대화 맥락을 바탕으로 치매 진단에 유용한 고품질 인지기능 평가 질문을 5개 생성하세요.
        
        사용자 메시지: {user_message}
        사진 정보: {photo_context}
        
        각 질문은 다음 카테고리 중 하나에 해당해야 합니다:
        - orientation_time: 시간 지남력
        - orientation_place: 장소 지남력  
        - memory_registration: 기억 등록
        - memory_recall: 기억 회상
        - attention: 주의력
        - executive_function: 실행기능
        - language_naming: 언어 명명
        
        JSON 형식으로 응답:
        [
            {{
                "category": "orientation_time",
                "question": "지금이 몇 시인지 알 수 있나요?",
                "difficulty": 2
            }},
            ...
        ]
        """
        
        response = llm_high_quality.invoke([
            SystemMessage(content="당신은 치매 진단 전문가입니다."),
            HumanMessage(content=prompt)
        ])
        
        # 생성된 질문들을 Supabase에 저장
        import json
        questions = json.loads(response.content)
        
        for question_data in questions:
            supabase.table("cist_question_templates").insert({
                "category": question_data["category"],
                "template_text": question_data["question"],
                "difficulty_level": question_data.get("difficulty", 1),
                "context_type": "photo_based"
            }).execute()
        
        return {
            "status": "success",
            "questions_generated": len(questions),
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        print(f"High quality question generation failed: {e}")
        return {
            "status": "error", 
            "error": str(e),
            "conversation_id": conversation_id
        }

@celery_app.task
def analyze_conversation_patterns(conversation_id: str):
    """
    대화 패턴 분석 및 인지기능 저하 징후 감지
    """
    try:
        # Supabase에서 대화 기록 조회
        response = supabase.table("conversations").select(
            "*, sessions(*)"
        ).eq("id", conversation_id).execute()
        
        if not response.data:
            return {"status": "error", "error": "Conversation not found"}
        
        conversation = response.data[0]
        
        # 대화 패턴 분석 로직 (추후 구현)
        analysis_result = {
            "conversation_id": conversation_id,
            "cognitive_indicators": [],
            "risk_level": "low",  # low, medium, high
            "recommendations": []
        }
        
        return analysis_result
        
    except Exception as e:
        print(f"Conversation analysis failed: {e}")
        return {"status": "error", "error": str(e)}

# Celery 설정
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
)