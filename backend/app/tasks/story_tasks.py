from celery import Celery
from .celery_config import supabase_admin
import httpx
import asyncio
from datetime import datetime
import base64
import openai
import os

# Celery 앱 초기화 (docker-compose의 redis 사용)
celery_app = Celery(
    "memento_box",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# OpenAI 클라이언트 초기화
client = openai.AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

async def generate_grandparent_story_openai(conversations_data):
    """할머니/할아버지 스타일 이야기 생성 (OpenAI API 직접 호출)"""
    
    # 대화 데이터를 텍스트로 변환
    conversation_text = "\n".join([
        f"질문: {conv['question_text']}\n답변: {conv['user_response_text']}"
        for conv in conversations_data
    ])
    
    system_prompt = """당신은 따뜻한 할머니입니다. 손자/손녀와의 대화를 바탕으로 
    추억이 담긴 이야기를 만들어주세요. 
    - 할머니의 따뜻한 말투를 사용하세요
    - 가족의 사랑과 추억을 강조하세요
    - 한국어로 자연스럽게 작성하세요"""
    
    user_prompt = f"""다음은 손자/손녀와의 대화 내용입니다:

{conversation_text}

이 대화를 바탕으로 할머니가 들려주는 따뜻한 이야기로 만들어주세요."""

    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"OpenAI API 오류: {str(e)}")

@celery_app.task(bind=True)
def process_story_and_tts_background(self, session_id: str, fish_speech_endpoint: str):
    """스토리 생성 + TTS 처리를 백그라운드에서 실행"""
    
    job_id = self.request.id
    
    try:
        # 1단계: 스토리 생성
        self.update_state(state='PROCESSING', meta={
            'step': 'story_generation', 
            'progress': 20,
            'message': '스토리를 생성하고 있습니다...'
        })
        
        story_result = asyncio.run(generate_story_async(session_id))
        story_id = story_result['story_id']
        
        # 2단계: TTS 생성  
        self.update_state(state='PROCESSING', meta={
            'step': 'tts_generation', 
            'progress': 60,
            'message': 'TTS 오디오를 생성하고 있습니다...',
            'story_id': story_id
        })
        
        tts_result = asyncio.run(generate_tts_async(story_id, fish_speech_endpoint))
        
        # 완료
        return {
            'story_id': story_id,
            'tts_audio_path': tts_result['tts_audio_path'],
            'status': 'completed',
            'message': '스토리와 TTS 생성이 완료되었습니다.'
        }
        
    except Exception as e:
        # 실패 시 DB 상태 업데이트
        try:
            if 'story_id' in locals():
                supabase_admin.table("photo_stories").update({
                    "tts_status": "failed",
                    "updated_at": datetime.now().isoformat()
                }).eq("id", story_id).execute()
        except:
            pass
            
        raise e

async def generate_story_async(session_id: str):
    """스토리 생성 작업 (비동기)"""
    # 세션 정보 가져오기
    session_response = supabase_admin.table("sessions").select(
        "user_id, selected_photos"
    ).eq("id", session_id).single().execute()
    
    if not session_response.data:
        raise Exception("해당 세션을 찾을 수 없습니다.")
    
    user_id = session_response.data["user_id"]
    selected_photos = session_response.data["selected_photos"]
    
    # family_id 가져오기
    user_response = supabase_admin.table("family_members").select(
        "family_id"
    ).eq("user_id", user_id).single().execute()
    
    family_id = user_response.data["family_id"] if user_response.data else None
    if not family_id:
        raise Exception("사용자의 family_id를 찾을 수 없습니다.")
    
    # 대화 기록 가져오기
    conversations_response = supabase_admin.table("conversations").select(
        "id, conversation_order, question_text, user_response_text"
    ).eq("session_id", session_id).order("conversation_order").execute()
    
    if not conversations_response.data:
        raise Exception("해당 세션의 대화 기록을 찾을 수 없습니다.")
    
    # 스토리 생성
    story = await generate_grandparent_story_openai(conversations_response.data)
    
    # DB에 저장
    photo_id = selected_photos[0] if selected_photos and len(selected_photos) > 0 else None
    if not photo_id:
        raise Exception("세션에 연결된 사진이 없습니다.")
        
    conversation_ids = [conv["id"] for conv in conversations_response.data]
    
    story_data = {
        "user_id": user_id,
        "family_id": family_id,
        "photo_id": photo_id,
        "title": f"할머니의 이야기 - {datetime.now().strftime('%Y년 %m월 %d일')}",
        "story_text": story,
        "language": "ko",
        "status": "generated",
        "source_session_ids": [session_id],
        "source_conversation_ids": conversation_ids,
        "tts_status": "queued"
    }
    
    story_response = supabase_admin.table("photo_stories").upsert(
        story_data, 
        on_conflict="user_id,photo_id"
    ).execute()
    
    return {'story_id': story_response.data[0]['id']}

async def generate_tts_async(story_id: str, fish_speech_endpoint: str):
    """TTS 생성 작업 (비동기)"""
    # 스토리 데이터 가져오기
    story_response = supabase_admin.table("photo_stories").select(
        "story_text, source_conversation_ids, user_id, photo_id, family_id"
    ).eq("id", story_id).execute()
    
    if not story_response.data:
        raise Exception("해당 스토리를 찾을 수 없습니다.")
    
    story_data = story_response.data[0]
    story_text = story_data["story_text"]
    source_conversation_ids = story_data["source_conversation_ids"]
    user_id = story_data["user_id"]
    photo_id = story_data["photo_id"]
    family_id = story_data["family_id"]
    
    # TTS 상태를 running으로 업데이트
    supabase_admin.table("photo_stories").update({
        "tts_status": "running",
        "updated_at": datetime.now().isoformat()
    }).eq("id", story_id).execute()
    
    # 참조 오디오 URL 가져오기
    if not source_conversation_ids:
        raise Exception("참조할 대화 기록이 없습니다.")
    
    first_conversation_id = source_conversation_ids[0]
    conversation_response = supabase_admin.table("conversations").select(
        "user_response_audio_url"
    ).eq("id", first_conversation_id).execute()
    
    if not conversation_response.data:
        raise Exception("참조할 오디오 파일을 찾을 수 없습니다.")
    
    reference_audio_url = conversation_response.data[0]["user_response_audio_url"]
    if not reference_audio_url:
        raise Exception("참조 오디오 파일이 존재하지 않습니다.")
    
    # Signed URL 생성 (재시도 로직)
    full_audio_url = None
    for attempt in range(3):
        try:
            signed_url_response = supabase_admin.storage.from_("voice").create_signed_url(
                path=reference_audio_url,
                expires_in=7200
            )
            if signed_url_response and 'signedURL' in signed_url_response:
                full_audio_url = signed_url_response['signedURL']
                break
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(3)
    
    if not full_audio_url:
        raise Exception("참조 오디오 파일에 접근할 수 없습니다. Supabase 연결 문제가 있습니다.")
    
    # Fish Speech API 호출
    fish_speech_payload = {
        "text": story_text,
        "reference_audio": full_audio_url,
        "reference_text": "",
        "output_format": "base64"
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        fish_response = await client.post(
            fish_speech_endpoint,
            json=fish_speech_payload
        )
        
        if fish_response.status_code != 200:
            raise Exception(f"Fish Speech API 오류: {fish_response.status_code}")
        
        fish_result = fish_response.json()
    
    # 오디오 저장
    audio_base64 = fish_result.get("audio_base64", "")
    if not audio_base64:
        raise Exception("Fish Speech에서 오디오 데이터를 받지 못했습니다.")
    
    audio_data = base64.b64decode(audio_base64)
    
    audio_filename = f"{photo_id}_{int(datetime.now().timestamp())}.wav"
    audio_path = f"{family_id}/{user_id}/{audio_filename}"
    
    # Supabase Storage에 업로드
    storage_response = supabase_admin.storage.from_("fishspeech").upload(
        audio_path, 
        audio_data,
        file_options={"content-type": "audio/wav"}
    )
    
    if hasattr(storage_response, 'error') and storage_response.error:
        raise Exception("오디오 파일 저장에 실패했습니다.")
    
    # DB 업데이트
    tts_params = {
        "fish_speech_endpoint": fish_speech_endpoint,
        "reference_audio_url": reference_audio_url,
        "generated_at": datetime.now().isoformat()
    }
    
    supabase_admin.table("photo_stories").update({
        "tts_audio_path": audio_path,
        "tts_status": "succeeded",
        "tts_params": tts_params,
        "updated_at": datetime.now().isoformat()
    }).eq("id", story_id).execute()
    
    return {'tts_audio_path': audio_path}