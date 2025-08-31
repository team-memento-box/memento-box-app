#!/usr/bin/env python3
"""
Audio Analysis Router for Memento-Box
음성 분석 관련 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict, Any, Optional, Literal, Tuple
import uuid
from pydantic import BaseModel, Field
import asyncio
import os
from datetime import datetime
import io
import tempfile

# ===== (NEW) Audio processing deps =====
import numpy as np
import soundfile as sf
import librosa
import httpx
# ======================================

# Supabase 클라이언트
from supabase import create_client, Client

router = APIRouter(
    prefix="/audio-analysis",
    tags=["audio-analysis"],
    responses={404: {"description": "Not found"}},
)

# Supabase 클라이언트 설정
def get_supabase_client() -> Client:
    """Supabase 클라이언트를 반환합니다."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase 설정이 누락되었습니다."
        )
    
    return create_client(url, key)

# ---------------------------------------------------------------------------
# Request/Response 모델들
# ---------------------------------------------------------------------------
class SessionAudioRequest(BaseModel):
    """세션 오디오 요청 모델"""
    session_id: str = Field(..., description="세션 ID")

class AudioFileInfo(BaseModel):
    """오디오 파일 정보 모델"""
    conversation_id: str
    conversation_order: int
    ai_output: str
    user_response_audio_url: Optional[str]
    user_input: Optional[str]
    question_type: str
    created_at: str

class SessionAudioResponse(BaseModel):
    """세션 오디오 응답 모델"""
    session_id: str
    total_conversations: int
    audio_files_count: int
    audio_files: List[AudioFileInfo]

# ---------------------------------------------------------------------------
# 조회 엔드포인트 (기존)
# ---------------------------------------------------------------------------
@router.get("/session/{session_id}/audio-files", response_model=SessionAudioResponse)
async def get_session_audio_files(
    session_id: str,
    supabase: Client = Depends(get_supabase_client)
) -> SessionAudioResponse:
    """
    세션 ID로 해당 세션의 모든 사용자 응답 오디오 파일 URL을 가져옵니다.
    """
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 세션 ID 형식입니다: {session_id}"
        )
    
    try:
        # 세션의 모든 대화 조회 (conversation_order 순서대로)
        response = supabase.table("conversations").select(
            "id, conversation_order, ai_output, user_input, "
            "user_response_audio_url, question_type, created_at"
        ).eq(
            "session_id", session_id
        ).order(
            "conversation_order", desc=False
        ).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"세션 ID {session_id}에 대한 대화를 찾을 수 없습니다."
            )
        
        conversations = response.data
        
        # 오디오 파일 정보 구성
        audio_files = []
        audio_count = 0
        
        for conv in conversations:
            audio_info = AudioFileInfo(
                conversation_id=str(conv["id"]),
                conversation_order=conv["conversation_order"],
                ai_output=conv["ai_output"],
                user_input=conv["user_input"],
                user_response_audio_url=conv["user_response_audio_url"],
                question_type=conv["question_type"],
                created_at=conv["created_at"]
            )
            audio_files.append(audio_info)
            if conv["user_response_audio_url"]:
                audio_count += 1
        
        return SessionAudioResponse(
            session_id=session_id,
            total_conversations=len(conversations),
            audio_files_count=audio_count,
            audio_files=audio_files
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/session/audio-files", response_model=SessionAudioResponse)
async def get_session_audio_files_post(
    request: SessionAudioRequest,
    supabase: Client = Depends(get_supabase_client)
) -> SessionAudioResponse:
    """
    POST 방식으로 세션 오디오 파일들을 조회합니다.
    (프론트엔드에서 body로 session_id를 전달하는 경우)
    """
    return await get_session_audio_files(request.session_id, supabase)

@router.get("/session/{session_id}/audio-urls-only")
async def get_session_audio_urls_only(
    session_id: str,
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    세션의 오디오 URL만 간단히 반환합니다. (음성 분석 모듈용)
    """
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 세션 ID 형식입니다: {session_id}"
        )
    
    try:
        # user_response_audio_url이 NULL이 아닌 대화만 조회
        response = supabase.table("conversations").select(
            "id, conversation_order, user_response_audio_url"
        ).eq(
            "session_id", session_id
        ).not_.is_(
            "user_response_audio_url", "null"
        ).order(
            "conversation_order", desc=False
        ).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"세션 ID {session_id}에 오디오 파일이 있는 대화를 찾을 수 없습니다."
            )
        
        conversations = response.data
        
        audio_urls = [
            {
                "conversation_id": conv["id"],
                "conversation_order": conv["conversation_order"],
                "audio_url": conv["user_response_audio_url"]
            }
            for conv in conversations
        ]
        
        return {
            "session_id": session_id,
            "audio_files_count": len(audio_urls),
            "audio_urls": audio_urls
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """음성 분석 라우터 헬스 체크"""
    return {
        "status": "healthy",
        "service": "audio-analysis",
        "message": "Audio Analysis API is running"
    }

# ---------------------------------------------------------------------------
# (NEW) 오디오 병합 유틸리티
# ---------------------------------------------------------------------------

async def _fetch_ordered_audio_urls_from_db(
    session_id: str,
    supabase: Client
) -> List[Tuple[int, str]]:
    """
    DB에서 (conversation_order, audio_url) 목록을 정렬하여 반환.
    """
    response = supabase.table("conversations").select(
        "conversation_order, user_response_audio_url"
    ).eq(
        "session_id", session_id
    ).not_.is_(
        "user_response_audio_url", "null"
    ).order(
        "conversation_order", desc=False
    ).execute()

    items = response.data or []
    # 빈 값/None 필터
    ordered = [
        (it["conversation_order"], it["user_response_audio_url"])
        for it in items
        if it.get("user_response_audio_url")
    ]
    # 보장 차원에서 정렬
    ordered.sort(key=lambda x: x[0])
    return ordered

async def _get_session_user_family_info(session_id: str, supabase: Client) -> Tuple[str, str]:
    """
    세션 ID로부터 user_id와 family_id를 조회합니다.
    """
    # sessions 테이블에서 user_id를 가져오고, users 테이블과 조인해서 current_family_id를 가져옵니다
    response = supabase.table("sessions").select(
        "user_id, users!inner(current_family_id)"
    ).eq("id", session_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    session_data = response.data[0]
    user_id = session_data["user_id"]
    family_id = session_data["users"]["current_family_id"]
    
    if not family_id:
        raise HTTPException(status_code=400, detail="사용자의 가족 정보가 없습니다.")
    
    return user_id, family_id

def _resolve_storage_url(storage_path: str, supabase: Client) -> str:
    """
    Supabase Storage의 상대 경로를 전체 URL로 변환합니다.
    """
    if storage_path.startswith(('http://', 'https://')):
        return storage_path
    
    try:
        # Signed URL 생성 (24시간 유효)
        response = supabase.storage.from_("voice").create_signed_url(
            storage_path, 
            expires_in=86400  # 24 hours in seconds
        )
        return response.get('signedURL', storage_path)
    except Exception:
        # Fallback to public URL
        url = os.getenv("SUPABASE_URL")
        bucket = "voice"
        return f"{url}/storage/v1/object/public/{bucket}/{storage_path}"

async def _upload_merged_audio_to_storage(
    session_id: str, 
    user_id: str, 
    family_id: str, 
    file_path: str, 
    supabase: Client
) -> str:
    """
    병합된 오디오 파일을 Supabase Storage에 업로드하고 저장 경로를 반환합니다.
    """
    storage_path = f"{family_id}/{user_id}/{session_id}/merged/session_merged.wav"
    
    with open(file_path, 'rb') as f:
        response = supabase.storage.from_("voice").upload(
            storage_path,
            f,
            {"content-type": "audio/wav", "upsert": "true"}
        )
    
    if hasattr(response, 'error') and response.error:
        raise HTTPException(
            status_code=500, 
            detail=f"Storage 업로드 실패: {response.error.message}"
        )
    
    return storage_path

async def _update_session_merged_audio_url(
    session_id: str, 
    merged_audio_url: str, 
    supabase: Client
) -> None:
    """
    sessions 테이블에 merged_audio_url을 업데이트합니다.
    """
    response = supabase.table("sessions").update({
        "merged_audio_url": merged_audio_url
    }).eq("id", session_id).execute()
    
    if hasattr(response, 'error') and response.error:
        raise HTTPException(
            status_code=500, 
            detail=f"DB 업데이트 실패: {response.error.message}"
        )

async def _download_wav(url: str) -> Tuple[np.ndarray, int]:
    """
    WAV 파일을 다운로드하여 (waveform[np.float32, mono], sample_rate)를 반환.
    """
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = io.BytesIO(r.content)

    # soundfile로 읽기 (always_2d=True로 채널 차원 확보)
    y, sr = sf.read(data, dtype="float32", always_2d=True)  # (n_samples, n_channels)
    # 모노 변환(평균)
    y = y.mean(axis=1).astype(np.float32)  # (n_samples,)
    return y, sr

def _resample_if_needed(y: np.ndarray, sr_src: int, sr_tgt: int) -> np.ndarray:
    if sr_src == sr_tgt:
        return y
    return librosa.resample(y, orig_sr=sr_src, target_sr=sr_tgt)

def _peak_normalize(y: np.ndarray, peak: float = 0.98) -> np.ndarray:
    m = float(np.max(np.abs(y))) if y.size else 1.0
    if m == 0.0:
        return y
    return (y / m) * peak

# ---------------------------------------------------------------------------
# (NEW) 세션 오디오 병합 엔드포인트
# ---------------------------------------------------------------------------
@router.post("/session/{session_id}/concat-wav", summary="Concat all session audio into one WAV")
async def concat_session_wav(
    session_id: str,
    target_sr: int = Query(16000, ge=8000, le=48000),
    normalize: bool = Query(True),
    mode: Literal["stream", "temp_path"] = Query("stream"),
    save_to_storage: bool = Query(True, description="Supabase Storage에 병합 파일 저장 여부"),
    supabase: Client = Depends(get_supabase_client),
):
    """
    세션의 모든 사용자 응답 오디오(.wav)를 순서대로 이어붙여 단일 WAV로 반환합니다.
    - mode=stream: 파일 다운로드로 스트리밍 응답
    - mode=temp_path: 서버 임시경로에 저장 후 JSON으로 경로 반환
    """
    # 1) UUID 검증
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 세션 ID 형식입니다: {session_id}"
        )

    # 2) URL 목록 획득
    ordered = await _fetch_ordered_audio_urls_from_db(session_id, supabase)
    if not ordered:
        raise HTTPException(status_code=404, detail="해당 세션의 오디오 파일이 없습니다.")

    # 3) 다운로드 + 전처리 + 병합
    chunks: List[np.ndarray] = []
    for order, url in ordered:
        try:
            # URL을 전체 URL로 변환
            resolved_url = _resolve_storage_url(url, supabase)
            y, sr = await _download_wav(resolved_url)
            y = _resample_if_needed(y, sr, target_sr)
            if normalize:
                y = _peak_normalize(y)
            # float32 유지
            chunks.append(y.astype(np.float32))
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"오디오 다운로드/파싱 실패 (order={order}): {str(e)}"
            )

    if not chunks:
        raise HTTPException(status_code=404, detail="병합할 오디오가 없습니다.")

    cat = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]

    # 4) 임시 wav 생성
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    fname = f"session_{session_id}_{ts}.wav"
    tmpdir = tempfile.mkdtemp(prefix="concatwav_")
    fpath = os.path.join(tmpdir, fname)

    # 16-bit PCM으로 저장 (대부분의 플레이어 호환)
    sf.write(fpath, cat, target_sr, subtype="PCM_16")
    
    # 5) Supabase Storage에 업로드 (옵션)
    storage_url = None
    if save_to_storage:
        try:
            user_id, family_id = await _get_session_user_family_info(session_id, supabase)
            storage_path = await _upload_merged_audio_to_storage(
                session_id, user_id, family_id, fpath, supabase
            )
            await _update_session_merged_audio_url(session_id, storage_path, supabase)
            storage_url = storage_path
        except Exception as e:
            # Storage 업로드 실패해도 기본 기능은 유지
            print(f"Storage 업로드 실패 (무시됨): {str(e)}")

    if mode == "temp_path":
        result = {
            "session_id": session_id,
            "sample_rate": target_sr,
            "duration_sec": round(len(cat) / float(target_sr), 3),
            "path": fpath
        }
        if storage_url:
            result["storage_url"] = storage_url
        return JSONResponse(result)

    # 6) 스트리밍 응답
    f = open(fpath, "rb")
    headers = {"Content-Disposition": f'attachment; filename="{fname}"'}
    return StreamingResponse(f, media_type="audio/wav", headers=headers)


# ---------------------------------------------------------------------------
# (NEW) 특징 추출 엔드포인트
# ---------------------------------------------------------------------------
@router.post("/audio-feature-extractor", summary="Extract audio features for ML analysis")
async def extract_audio_features(
    session_id: str,
    audio_file_path: Optional[str] = None,
    supabase: Client = Depends(get_supabase_client),
):
    """
    세션의 병합된 오디오 또는 지정된 오디오 파일에서 특징을 추출합니다.
    """
    try:
        # 1) 오디오 파일 경로 결정
        if audio_file_path is None:
            # session_id로부터 병합된 오디오 파일 경로 가져오기
            response = supabase.table("sessions").select("merged_audio_url").eq("id", session_id).execute()
            
            if not response.data:
                raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
            
            merged_url = response.data[0].get("merged_audio_url")
            if not merged_url:
                raise HTTPException(status_code=404, detail="병합된 오디오 파일이 없습니다. concat-wav를 먼저 실행하세요.")
            
            # Supabase Storage URL을 실제 파일 경로로 변환
            resolved_url = _resolve_storage_url(merged_url, supabase)
            
            # 임시 파일로 다운로드
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(resolved_url)
                response.raise_for_status()
                
                # 임시 파일 생성
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_file.write(response.content)
                    audio_file_path = tmp_file.name
        
        # 2) 특징 추출 서비스 사용
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))
        
        from audio_feature_extractor import AudioFeatureExtractor
        
        extractor = AudioFeatureExtractor()
        features_list = extractor.extract_features(audio_file_path)
        
        if not features_list:
            raise HTTPException(status_code=500, detail="특징 추출에 실패했습니다.")
        
        # 3) 결과 반환
        features_df = extractor.features_to_dataframe(features_list)
        
        return {
            "success": True,
            "session_id": session_id,
            "total_segments": len(features_list),
            "feature_names": extractor.feature_names,
            "features": features_df.to_dict('records') if features_df is not None else []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"특징 추출 실패: {str(e)}")
    finally:
        # 임시 파일 정리
        if 'tmp_file' in locals() and os.path.exists(audio_file_path):
            try:
                os.unlink(audio_file_path)
            except:
                pass


# ---------------------------------------------------------------------------
# (NEW) 치매 감지 엔드포인트
# ---------------------------------------------------------------------------
@router.post("/audio-dementia-detector", summary="Detect dementia from audio features")
async def detect_dementia_from_audio(
    session_id: str,
    audio_file_path: Optional[str] = None,
    supabase: Client = Depends(get_supabase_client),
):
    """
    세션의 병합된 오디오에서 치매 여부를 감지합니다.
    """
    try:
        # 1) 오디오 파일 경로 결정 (특징 추출과 동일한 로직)
        if audio_file_path is None:
            response = supabase.table("sessions").select("merged_audio_url").eq("id", session_id).execute()
            
            if not response.data:
                raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
            
            merged_url = response.data[0].get("merged_audio_url")
            if not merged_url:
                raise HTTPException(status_code=404, detail="병합된 오디오 파일이 없습니다. concat-wav를 먼저 실행하세요.")
            
            resolved_url = _resolve_storage_url(merged_url, supabase)
            
            # 임시 파일로 다운로드
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(resolved_url)
                response.raise_for_status()
                
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_file.write(response.content)
                    audio_file_path = tmp_file.name
        
        # 2) 치매 감지 서비스 사용
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))
        
        from audio_dementia_detector import get_dementia_detector_service
        
        detector = get_dementia_detector_service()
        if detector is None:
            raise HTTPException(status_code=500, detail="치매 감지 서비스를 초기화할 수 없습니다.")
        
        # 3) 치매 감지 실행
        result = await detector.detect_dementia_from_audio(audio_file_path)
        
        # 4) 결과를 DB에 저장
        if result.get("success"):
            try:
                # session_id로 기존 레코드 확인
                existing = supabase.table("session_audio_analysis").select("*").eq("session_id", session_id).execute()
                
                # user_id, family_id 가져오기
                user_id, family_id = await _get_session_user_family_info(session_id, supabase)
                
                # 병합된 오디오 URL 가져오기
                session_response = supabase.table("sessions").select("merged_audio_url").eq("id", session_id).execute()
                merged_audio_path = session_response.data[0].get("merged_audio_url") if session_response.data else None
                
                # DB 저장 데이터 구성 (새로운 스키마에 맞춤)
                analysis_data = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "family_id": family_id,
                    "merged_audio_path": merged_audio_path,
                    "total_slices": result["total_segments"],
                    "dementia_slices": result["dementia_segments_count"],
                    "risk_level": "risk" if result["dementia_ratio"] >= 0.6 else "suspect" if result["dementia_ratio"] >= 0.3 else "normal",
                    "adjusted_mean": None  # API에서 제공하지 않으므로 NULL
                }
                
                if existing.data:
                    # 기존 레코드 업데이트 (session_id 제외)
                    update_data = {k: v for k, v in analysis_data.items() if k != "session_id"}
                    supabase.table("session_audio_analysis").update(update_data).eq("session_id", session_id).execute()
                    print(f"✅ DB 업데이트 완료: session_id={session_id}")
                else:
                    # 새 레코드 생성
                    supabase.table("session_audio_analysis").insert(analysis_data).execute()
                    print(f"✅ DB 삽입 완료: session_id={session_id}")
                
            except Exception as db_error:
                print(f"⚠️ DB 저장 실패 (결과는 반환): {db_error}")
                import traceback
                print(f"상세 오류: {traceback.format_exc()}")
        
        # 5) 결과 반환
        result["session_id"] = session_id
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"치매 감지 실패: {str(e)}")
    finally:
        # 임시 파일 정리
        if 'tmp_file' in locals() and os.path.exists(audio_file_path):
            try:
                os.unlink(audio_file_path)
            except:
                pass


# ---------------------------------------------------------------------------
# (NEW) 통합 파이프라인 엔드포인트  
# ---------------------------------------------------------------------------
@router.post("/session/{session_id}/full-analysis", summary="Complete audio analysis pipeline")
async def full_audio_analysis_pipeline(
    session_id: str,
    target_sr: int = Query(16000, ge=8000, le=48000),
    normalize: bool = Query(True),
    force_concat: bool = Query(False, description="기존 병합 파일이 있어도 다시 병합할지 여부"),
    supabase: Client = Depends(get_supabase_client),
):
    """
    음성 병합 → 특징 추출 → 치매 감지까지 전체 파이프라인을 실행합니다.
    """
    try:
        results = {
            "session_id": session_id,
            "pipeline_steps": {},
            "final_result": None
        }
        
        # 1단계: 음성 파일 병합 (필요시)
        print(f"🔄 1단계: 음성 파일 병합 확인 - session_id: {session_id}")
        
        # 기존 병합 파일 확인
        session_response = supabase.table("sessions").select("merged_audio_url").eq("id", session_id).execute()
        
        if not session_response.data:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        existing_merged_url = session_response.data[0].get("merged_audio_url")
        
        if not existing_merged_url or force_concat:
            print("  음성 파일 병합 실행...")
            concat_result = await concat_session_wav(
                session_id=session_id,
                target_sr=target_sr,
                normalize=normalize,
                mode="temp_path",
                save_to_storage=True,
                supabase=supabase
            )
            results["pipeline_steps"]["concat"] = {
                "success": True,
                "duration_sec": concat_result["duration_sec"],
                "storage_url": concat_result.get("storage_url")
            }
            print(f"  ✅ 음성 병합 완료: {concat_result['duration_sec']:.1f}초")
        else:
            print("  기존 병합 파일 사용")
            results["pipeline_steps"]["concat"] = {
                "success": True,
                "skipped": True,
                "existing_url": existing_merged_url
            }
        
        # 2단계: 특징 추출
        print("🔄 2단계: 특징 추출 실행...")
        
        feature_result = await extract_audio_features(
            session_id=session_id,
            supabase=supabase
        )
        
        results["pipeline_steps"]["feature_extraction"] = {
            "success": feature_result["success"],
            "total_segments": feature_result["total_segments"],
            "feature_count": len(feature_result["feature_names"])
        }
        print(f"  ✅ 특징 추출 완료: {feature_result['total_segments']}개 세그먼트")
        
        # 3단계: 치매 감지
        print("🔄 3단계: 치매 감지 실행...")
        
        detection_result = await detect_dementia_from_audio(
            session_id=session_id,
            supabase=supabase
        )
        
        results["pipeline_steps"]["dementia_detection"] = {
            "success": detection_result["success"],
            "dementia_detected": detection_result.get("dementia_detected", False),
            "dementia_ratio": detection_result.get("dementia_ratio", 0.0),
            "risk_level": detection_result.get("risk_level", "unknown")
        }
        
        results["final_result"] = detection_result
        
        print(f"  ✅ 치매 감지 완료: 치매비율={detection_result.get('dementia_ratio', 0):.2%}")
        print(f"🎉 전체 파이프라인 완료!")
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파이프라인 실행 실패: {str(e)}")


# ---------------------------------------------------------------------------
# (NEW) 백그라운드 파이프라인 엔드포인트
# ---------------------------------------------------------------------------
@router.post("/session/{session_id}/full-analysis-async", summary="Start background audio analysis pipeline")
async def start_full_audio_analysis_background(
    session_id: str,
    photo_id: Optional[str] = Query(None, description="분석과 연관된 photo ID"),
    target_sr: int = Query(16000, ge=8000, le=48000),
    normalize: bool = Query(True),
    force_concat: bool = Query(False, description="기존 병합 파일이 있어도 다시 병합할지 여부"),
    supabase: Client = Depends(get_supabase_client),
):
    """
    전체 오디오 분석 파이프라인을 백그라운드에서 실행합니다.
    작업 ID를 반환하여 진행상황을 추적할 수 있습니다.
    """
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 세션 ID 형식입니다: {session_id}"
        )
    
    # 세션 존재 여부 확인
    session_response = supabase.table("sessions").select("id").eq("id", session_id).execute()
    if not session_response.data:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    # Celery 작업 시작
    from tasks.audio_analysis_tasks import process_full_audio_analysis_pipeline_background
    
    task = process_full_audio_analysis_pipeline_background.delay(
        session_id=session_id,
        photo_id=photo_id,
        target_sr=target_sr,
        normalize=normalize,
        force_concat=force_concat
    )
    
    return {
        "session_id": session_id,
        "task_id": task.id,
        "status": "started",
        "message": "오디오 분석 파이프라인이 백그라운드에서 시작되었습니다."
    }


@router.get("/task/{task_id}/status", summary="Get background task status")
async def get_task_status(task_id: str):
    """
    백그라운드 작업의 진행상황을 조회합니다.
    """
    from tasks.audio_analysis_tasks import celery_app
    from celery.result import AsyncResult
    
    try:
        # Celery 작업 결과 조회
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state == 'PENDING':
            response = {
                'task_id': task_id,
                'state': result.state,
                'status': 'pending',
                'message': '작업이 대기 중입니다.'
            }
        elif result.state == 'PROCESSING':
            response = {
                'task_id': task_id,
                'state': result.state,
                'status': 'processing',
                'step': result.info.get('step', 'unknown'),
                'progress': result.info.get('progress', 0),
                'message': result.info.get('message', '처리 중...'),
                'session_id': result.info.get('session_id')
            }
            # 단계별 추가 정보
            if 'concat_result' in result.info:
                response['concat_result'] = result.info['concat_result']
            if 'feature_count' in result.info:
                response['feature_count'] = result.info['feature_count']
                
        elif result.state == 'SUCCESS':
            response = {
                'task_id': task_id,
                'state': result.state,
                'status': 'completed',
                'progress': 100,
                'message': '작업이 완료되었습니다.',
                'result': result.result
            }
        else:  # FAILURE or other states
            response = {
                'task_id': task_id,
                'state': result.state,
                'status': 'failed',
                'error': str(result.info) if result.info else 'Unknown error',
                'message': '작업이 실패했습니다.'
            }
            
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"작업 상태 조회 실패: {str(e)}"
        )
