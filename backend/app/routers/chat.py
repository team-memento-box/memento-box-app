from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Response
from fastapi.responses import FileResponse, JSONResponse
from uuid import UUID
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.blob_storage import BlobStorageService, get_blob_service_client
from db.database import get_db
from services.llm_system import OptimizedDementiaSystem, upload_audio_to_blob
from services.blob_storage import get_blob_service_client, download_file_from_url
from db.models.user import User
from db.models.turn import Turn
from db.models.conversation import Conversation
from db.models.anomaly_report import AnomalyReport
from db.models.photo import Photo
from schemas.turn import TurnRequest
from schemas.chat import ConversationCreate, TurnCreate, SummaryUpdateRequest

import uuid
import os
import tempfile
from fastapi import UploadFile
import json


router = APIRouter(
    prefix="/chat",
    tags=["llm"]
)
system = OptimizedDementiaSystem()

# 이미지 기반 대화 세션 시작 (질문 생성) 
@router.post("/start")
async def start_chat(image_id: str, db: Session = Depends(get_db)):
    TEMP_DIR = "./temp_images"
    print(f"[DEBUG][start_chat] 호출됨 - image_id: {image_id}")
    
    # [0] DB에서 photo 정보 조회
    try:
        print(f"[DEBUG][start_chat] image_id를 UUID로 변환 시도")
        # image_id를 UUID로 변환하여 DB에서 조회
        photo_uuid = UUID(image_id)
        print(f"[DEBUG][start_chat] 변환된 photo_uuid: {photo_uuid}")
        stmt = select(Photo).where(Photo.id == photo_uuid)
        print(f"[DEBUG][start_chat] Photo 조회 쿼리 실행: {stmt}")
        result = await db.execute(stmt)
        photo = result.scalar_one_or_none()
        print(f"[DEBUG][start_chat] 조회된 photo: {photo}")
        
        if not photo:
            print(f"[ERROR][start_chat] Photo not found with id: {image_id}")
            raise HTTPException(status_code=404, detail=f"Photo not found with id: {image_id}")
        
        # Azure Blob Storage에서 이미지 다운로드 (URL에서 직접)
        print(f"[DEBUG][start_chat] 이미지 다운로드 시작: {photo.url}")
        image_bytes = await download_file_from_url(photo.url)
        print(f"[DEBUG][start_chat] 이미지 바이트 크기: {len(image_bytes)}")
        
        # 임시 디렉토리 생성
        if not os.path.exists(TEMP_DIR):
            print(f"[DEBUG][start_chat] 임시 디렉토리 생성: {TEMP_DIR}")
            os.makedirs(TEMP_DIR)
        
        # 임시 파일로 저장
        file_extension = os.path.splitext(photo.url)[-1] or '.jpg'
        temp_filename = f"{image_id}{file_extension}"
        image_path = os.path.join(TEMP_DIR, temp_filename)
        print(f"[DEBUG][start_chat] 임시 이미지 파일 경로: {image_path}")
        
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
            print(f"[DEBUG][start_chat] 이미지 파일 저장 완료: {image_path}")
            
        print(f"✅ 이미지 다운로드 완료: {image_path}")
        
    except ValueError:
        print(f"[ERROR][start_chat] Invalid UUID format for image_id: {image_id}")
        raise HTTPException(status_code=400, detail="Invalid UUID format for image_id")
    except Exception as e:
        print(f"[ERROR][start_chat] 이미지 다운로드 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"이미지 다운로드 실패: {str(e)}")
    
    # 해당 이미지에 대한 가장 최근 대화 확인
    print(f"[DEBUG][start_chat] 최근 conversation 조회 시작")
    stmt = select(Conversation).where(
        Conversation.photo_id == photo_uuid
    ).order_by(Conversation.created_at.desc())
    print(f"[DEBUG][start_chat] Conversation 조회 쿼리: {stmt}")
    result = await db.execute(stmt)
    latest_conversation = result.scalars().first()
    print(f"[DEBUG][start_chat] latest_conversation: {latest_conversation}")

    first_question = None
    audio_path = None
    is_continuation = False

    if latest_conversation:
        # 가장 최근 턴 가져오기
        print(f"[DEBUG][start_chat] 최근 Turn 조회 시작")
        stmt = select(Turn).where(
            Turn.conv_id == latest_conversation.id
        ).order_by(Turn.recorded_at.desc())
        print(f"[DEBUG][start_chat] Turn 조회 쿼리: {stmt}")
        result = await db.execute(stmt)
        latest_turn = result.scalars().first()
        print(f"[DEBUG][start_chat] latest_turn: {latest_turn}")

        if latest_turn and latest_turn.turn:
            # 세션이 완료되었는지 확인
            is_session_completed = (
                latest_turn.turn.get("q_text") == "session_completed" or 
                latest_turn.turn.get("a_text") == "session_completed"
            )
            print(f"[DEBUG][start_chat] is_session_completed: {is_session_completed}")
            
            if not is_session_completed:
                # 이전 대화가 있고 세션이 완료되지 않은 경우에만 이어서 대화 생성
                conversation_id = latest_conversation.id
                previous_question = latest_turn.turn.get("q_text")
                previous_answer = latest_turn.turn.get("a_text")
                print(f"[DEBUG][start_chat] previous_question: {previous_question}, previous_answer: {previous_answer}")
                
                if previous_answer and previous_answer != "session_completed":
                    print(f"[DEBUG][start_chat] generate_next_question 호출")
                    first_question, audio_path = system.generate_next_question(previous_question, previous_answer)
                    print(f"[DEBUG][start_chat] generate_next_question 결과: {first_question}, {audio_path}")
                    is_continuation = True

    # conversation 생성이 필요한 경우 first_question,audio_path 만들어야 함
    if not is_continuation:
        # [1] Conversation 데이터 생성 & 첫 질문 LLM 생성 및 
        try:
            print(f"[DEBUG][start_chat] 새 Conversation 생성 시도")
            new_conversation = Conversation(
                id=uuid4(),
                photo_id=photo_uuid,
                # created_at은 자동으로 처리됨 -> 과연
                created_at=datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
            )
            db.add(new_conversation)
            await db.commit()
            await db.refresh(new_conversation)
            print(f"[DEBUG][start_chat] 새 Conversation 생성 완료: {new_conversation}")
        except Exception as e:
            print(f"[ERROR][start_chat] Conversation DB 저장 실패: {str(e)}")
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"데이터베이스 저장 실패: {str(e)}")
        
        print(f"[DEBUG][start_chat] analyze_and_start_conversation 호출: {image_path}")
        first_question, audio_path = system.analyze_and_start_conversation(image_path)
        print(f"[DEBUG][start_chat] analyze_and_start_conversation 결과: {first_question}, {audio_path}")
        conversation_id = new_conversation.id
    else:
        print(f"[DEBUG][start_chat] 기존 conversation 이어서 진행: {conversation_id}")
    
    # [2] audio Blob 저장
    try:
        print(f"[DEBUG][start_chat] Blob Storage 업로드 시작: {audio_path}")
        blob_service_client = get_blob_service_client("talking-voice")
        original_filename = os.path.basename(audio_path)
        blob_url = await upload_audio_to_blob(audio_path, original_filename, blob_service_client)
        print(f"[DEBUG][start_chat] Blob 업로드 성공: {blob_url}")
    except Exception as e:
        print(f"[ERROR][start_chat] Blob 업로드 실패: {str(e)}")
        blob_url = "블롭 스토리지 에러"
    
    # [3] turn 데이터 추가
    print(f"[DEBUG][start_chat] Turn 데이터 추가 시작")
    new_turn = Turn(
        id=uuid4(),
        conv_id=conversation_id,
        turn={
            "q_text": first_question,
            "q_voice": blob_url,
            "a_text": None,
            "a_voice": None
        },
        recorded_at=datetime.now()
    )
    db.add(new_turn)
    db.commit()
    print(f"[DEBUG][start_chat] Turn 추가 완료: {new_turn}")

    # [4] 응답 생성
    response_data = {
        "status": "ok",
        "conversation_id": str(conversation_id),
        "question": first_question,
        "audio_url": blob_url,
        "photo_info": {
            "id": str(photo.id),
            "name": photo.name,
            "url": photo.url
        },
        "is_continuation": is_continuation
    }
    print(f"[DEBUG][start_chat] 응답 데이터: {response_data}")
    
    # [5] 임시 파일 정리
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"🗑️ 임시 파일 삭제: {image_path}")
    except Exception as e:
        print(f"⚠️ 임시 파일 삭제 실패: {str(e)}")
    
    print(f"[DEBUG][start_chat] 종료")
    return JSONResponse(content=response_data)


# 답변 받고 Turn DB 업데이트
@router.post("/user_answer")
async def answer_chat(
    conversation_id: UUID = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    print(f"[DEBUG][answer_chat] 호출됨 - conversation_id: {conversation_id}, audio.filename: {audio.filename}, audio.content_type: {audio.content_type}")
    #print(f"[INFO] audio.spool max_size: {audio.spool_max_size}")  # 옵션 확인
    
    # 1. 마지막 턴 가져오기
    print(f"[DEBUG][answer_chat] 마지막 Turn 조회 시작")
    stmt = select(Turn).where(Turn.conv_id == conversation_id).order_by(Turn.recorded_at.desc())
    print(f"[DEBUG][answer_chat] Turn 조회 쿼리: {stmt}")
    result = await db.execute(stmt)
    last_turn = result.scalars().first()
    print(f"[DEBUG][answer_chat] last_turn: {last_turn}")

    if not last_turn or not last_turn.turn:
        print(f"[ERROR][answer_chat] No previous turn found")
        raise HTTPException(status_code=404, detail="No previous turn found")
    
    AUDIO_DIR = "audio_files"
    # 1. 고유 임시 파일 경로 설정
    unique_name = f"{uuid.uuid4().hex}.wav"
    temp_path = os.path.join(AUDIO_DIR, unique_name)
    print(f"[DEBUG][answer_chat] 임시 오디오 파일 경로: {temp_path}")
    
    # 디렉토리가 없으면 생성
    os.makedirs(AUDIO_DIR, exist_ok=True)
    
    # 오디오 파일 저장
    content = await audio.read()
    with open(temp_path, "wb") as f:
        f.write(content)
        print(f"[DEBUG][answer_chat] 오디오 파일 저장 완료: {temp_path}")

    # [2] audio Blob 저장
    try:
        print(f"[DEBUG][answer_chat] Blob Storage 업로드 시작: {temp_path}")
        blob_service_client = get_blob_service_client("talking-voice")
        original_filename = os.path.basename(temp_path)
        blob_url = await upload_audio_to_blob(temp_path, original_filename, blob_service_client)
        print(f"[DEBUG][answer_chat] Blob 업로드 성공: {blob_url}")
    except Exception as e:
        print(f"[ERROR][answer_chat] Blob 업로드 실패: {str(e)}")
        blob_url = "블롭 스토리지 에러"

    # [2-1] 다시 다운로드
    print(f"[DEBUG][answer_chat] Blob에서 오디오 다운로드 시작: {blob_url}")
    audio_bytes = await download_file_from_url(blob_url)
    print(f"[DEBUG][answer_chat] 다운로드된 오디오 바이트 크기: {len(audio_bytes)}")
    
    # 임시 파일로 저장
    file_extension = os.path.splitext(blob_url)[-1] or '.wav'
    temp_filename = f"_tmp{file_extension}"
    audio_path = os.path.join(AUDIO_DIR, temp_filename)
    print(f"[DEBUG][answer_chat] 다운로드 오디오 임시 경로: {audio_path}")
    
    with open(audio_path, 'wb') as f:
        f.write(audio_bytes)
        print(f"[DEBUG][answer_chat] 다운로드 오디오 파일 저장 완료: {audio_path}")
        
    print(f"✅ 오디오 다운로드 완료: {audio_path}")
        
    question = last_turn.turn.get("q_text")
    print(f"[DEBUG][answer_chat] _run_conversation 호출: question={question}, audio_path={audio_path}")
    user_answer, audio_path, should_end = system._run_conversation(question, audio_path, is_voice=True)
    print(f"[DEBUG][answer_chat] _run_conversation 결과: user_answer={user_answer}, audio_path={audio_path}, should_end={should_end}")

    # 3. 기존 턴에 유저 응답 업데이트
    updated_turn = last_turn.turn.copy()
    updated_turn["a_text"] = user_answer
    updated_turn["a_voice"] = blob_url
    print(f"[DEBUG][answer_chat] updated_turn: {updated_turn}")

    # JSON 직렬화 시 이스케이프 방지
    last_turn.turn = json.loads(json.dumps(updated_turn, ensure_ascii=False))
    db.commit()
    print(f"[DEBUG][answer_chat] DB 커밋 완료")

    # 5. 처리 끝나면 무조건 임시 파일 삭제
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
            print(f"[DEBUG][answer_chat] 임시 오디오 파일 삭제됨: {temp_path}")
        except Exception as cleanup_err:
            print(f"[ERROR][answer_chat] 파일 삭제 실패: {cleanup_err}")
    if os.path.exists(audio_path):
        try:
            os.remove(audio_path)
            print(f"[DEBUG][answer_chat] 임시 오디오 파일 삭제됨: {audio_path}")
        except Exception as cleanup_err:
            print(f"[ERROR][answer_chat] 파일 삭제 실패: {cleanup_err}")

    print(f"[DEBUG][answer_chat] 종료")
    return JSONResponse(content={
        "answer": user_answer, 
        #"audio_url": blob_url, 
        "should_end": should_end
    })

# 강제 대화 종료 (프런트에서 종료 버튼 클릭 시)
@router.post("/force-end")
async def force_end_chat(
    conversation_id: UUID = Form(...), 
    current_question: str = Form(None),  # 현재 진행 중인 질문 (있다면)
    db: Session = Depends(get_db)
):
    """프런트에서 강제 종료 버튼을 눌렀을 때 사용"""
    
    # 현재 진행 중인 질문이 있다면 답변 null로 저장
    if current_question and current_question.strip():
        # 사용자가 답변하지 않은 질문을 답변 null로 저장
        force_end_turn = Turn(
            id=uuid4(),
            conv_id=conversation_id,
            turn={
                "q_text": current_question,
                "q_voice": None,
                "a_text": "session_completed",  # 답변하지 않고 종료된 경우
                "a_voice": None
            },
            recorded_at=datetime.now()
        )
        db.add(force_end_turn)
        await db.commit()
        
        print(f"🔚 강제 종료: 미답변 질문을 session_completed로 처리하여 저장했습니다. (conversation_id: {conversation_id})")
    else:
        # 마지막 턴을 찾아서 질문에 session_completed 표시
        stmt = select(Turn).where(Turn.conv_id == conversation_id).order_by(Turn.recorded_at.desc())
        result = await db.execute(stmt)
        latest_turn = result.scalar_one_or_none()
        
        if latest_turn:
            latest_turn.turn["q_text"] = "session_completed"
            await db.commit()
            print(f"🔚 강제 종료: 마지막 질문을 session_completed로 처리했습니다. (conversation_id: {conversation_id})")
    
    # 기존 end 로직 호출
    return await end_chat(conversation_id, db)

# 대화 종료 및 분석/요약 생성
@router.post("/end")
async def end_chat(conversation_id: UUID = Form(...), db: Session = Depends(get_db)):
    # 1. conversation_id로 모든 Turn 데이터 가져오기
    stmt = select(Turn).where(Turn.conv_id == conversation_id).order_by(Turn.recorded_at.asc())
    result = await db.execute(stmt)
    turns = result.scalars().all()
    
    if not turns:
        raise HTTPException(status_code=404, detail="No turns found for this conversation")
    
    # 2. Turn 데이터를 스토리 생성에 사용할 수 있는 형태로 변환
    results = system.generate_complete_analysis_from_turns(turns, conversation_id)
    analysis_file = results.get("analysis_file")
    story_txt = results.get("story_content")

    with open(analysis_file, "r", encoding="utf-8") as file:
        analysis_txt = file.read()

    try:
        # 기존 대화 찾기
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        
        # summary_text에 story_txt 저장
        conversation.summary_text = story_txt
        
        await db.commit()
        await db.refresh(conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"요약 업데이트 실패: {str(e)}")
    

    # [] Anomaly Report 데이터 생성
    try:
        new_report = AnomalyReport(
            id=uuid4(),
            conv_id=conversation_id,
            anomaly_report = analysis_txt,
            anomaly_turn = None
        )
        db.add(new_report)
        await db.commit()
        await db.refresh(new_report)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"데이터베이스 저장 실패: {str(e)}")

    return results

# 🧪 테스트용 엔드포인트들
@router.post("/test/upload-image")
async def upload_test_image(image: UploadFile = File(...)):
    """테스트용 이미지 업로드"""
    TEMP_DIR = "./temp_images"
    
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    
    # 파일 저장
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{image.filename}"
    file_path = os.path.join(TEMP_DIR, filename)
    
    with open(file_path, "wb") as f:
        content = await image.read()
        f.write(content)
    
    return {
        "status": "success",
        "file_id": file_id,
        "filename": filename,
        "path": file_path,
        "message": "이미지가 업로드되었습니다. 이제 /start 엔드포인트에서 이 file_id를 사용하세요."
    }

@router.get("/test/conversations")
async def get_conversations(db: Session = Depends(get_db)):
    """모든 대화 목록 조회"""
    stmt = select(Conversation).order_by(Conversation.created_at.desc())
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    
    return {
        "conversations": [
            {
                "id": str(conv.id),
                "photo_id": conv.photo_id,
                "created_at": conv.created_at.isoformat()
            }
            for conv in conversations
        ]
    }

@router.get("/test/turns/{conversation_id}")
async def get_turns(conversation_id: UUID, db: Session = Depends(get_db)):
    """특정 대화의 모든 턴 조회"""
    stmt = select(Turn).where(Turn.conv_id == conversation_id).order_by(Turn.recorded_at.asc())
    result = await db.execute(stmt)
    turns = result.scalars().all()
    
    return {
        "conversation_id": str(conversation_id),
        "turns": [
            {
                "id": str(turn.id),
                "turn": turn.turn,
                "recorded_at": turn.recorded_at.isoformat()
            }
            for turn in turns
        ]
    }

@router.post("/test/quick-chat")
async def quick_chat_test(
    image_id: str = Form("test-image-001"),
    user_messages: str = Form("안녕하세요, 이 사진 정말 좋네요, 종료")  # 쉼표로 구분된 메시지들
):
    """빠른 대화 테스트 (여러 메시지를 한번에 처리)"""
    messages = [msg.strip() for msg in user_messages.split(",")]
    
    # 대화 시작
    conversation_id, first_question = system.analyze_and_start_conversation("./temp_images/test.jpg")
    
    results = {
        "conversation_id": str(conversation_id),
        "first_question": first_question,
        "turns": []
    }
    
    current_question = first_question
    
    # 각 메시지 처리
    for i, user_answer in enumerate(messages):
        # 종료 키워드 체크
        should_end = system.check_end_keywords(user_answer)
        
        # Turn 저장 (실제 DB 저장은 생략)
        turn_data = {
            "question": current_question,
            "answer": user_answer,
            "should_end": should_end
        }
        
        results["turns"].append(turn_data)
        
        if should_end:
            break
            
        # 다음 질문 생성
        try:
            next_question = system.generate_next_question(current_question, user_answer)
            current_question = next_question
            turn_data["next_question"] = next_question
        except:
            break
    
    return results