#!/usr/bin/env python3
"""
Audio Analysis Background Tasks for Memento-Box
Celery 백그라운드 작업으로 오디오 분석 파이프라인 처리
"""

from celery import Celery
from .celery_config import supabase_admin
import asyncio
from datetime import datetime
import tempfile
import os
import uuid
from typing import Dict, Any, Optional

# story_tasks.py에서 사용하는 동일한 Celery 앱 재사용
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

@celery_app.task(bind=True)
def process_full_audio_analysis_pipeline_background(
    self, 
    session_id: str, 
    photo_id: Optional[str] = None,
    target_sr: int = 16000, 
    normalize: bool = True, 
    force_concat: bool = False
):
    """
    전체 오디오 분석 파이프라인을 백그라운드에서 실행
    - 음성 병합 → 특징 추출 → 치매 감지
    """
    
    job_id = self.request.id
    
    try:
        # UUID 검증
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise Exception(f"유효하지 않은 세션 ID 형식입니다: {session_id}")

        # 1단계: 음성 파일 병합 (20% 진행률)
        self.update_state(state='PROCESSING', meta={
            'step': 'concat',
            'progress': 20,
            'message': '음성 파일을 병합하고 있습니다...',
            'session_id': session_id
        })
        
        concat_result = asyncio.run(process_audio_concat_async(
            session_id, target_sr, normalize, force_concat
        ))
        
        # 2단계: 특징 추출 (60% 진행률)
        self.update_state(state='PROCESSING', meta={
            'step': 'features',
            'progress': 60,
            'message': '오디오 특징을 추출하고 있습니다...',
            'session_id': session_id,
            'concat_result': {
                'duration_sec': concat_result.get('duration_sec'),
                'storage_url': concat_result.get('storage_url')
            }
        })
        
        feature_result = asyncio.run(process_audio_features_async(session_id))
        
        # 3단계: 치매 감지 (90% 진행률)
        self.update_state(state='PROCESSING', meta={
            'step': 'detection',
            'progress': 90,
            'message': '치매 감지 분석을 실행하고 있습니다...',
            'session_id': session_id,
            'feature_count': len(feature_result.get('feature_names', []))
        })
        
        detection_result = asyncio.run(process_dementia_detection_async(session_id, photo_id))
        
        # 완료 (100%)
        final_result = {
            'session_id': session_id,
            'status': 'completed',
            'message': '오디오 분석 파이프라인이 완료되었습니다.',
            'pipeline_steps': {
                'concat': {
                    'success': True,
                    'duration_sec': concat_result.get('duration_sec'),
                    'storage_url': concat_result.get('storage_url')
                },
                'feature_extraction': {
                    'success': feature_result.get('success', False),
                    'total_segments': feature_result.get('total_segments', 0),
                    'feature_count': len(feature_result.get('feature_names', []))
                },
                'dementia_detection': {
                    'success': detection_result.get('success', False),
                    'dementia_detected': detection_result.get('dementia_detected', False),
                    'dementia_ratio': detection_result.get('dementia_ratio', 0.0),
                    'risk_level': detection_result.get('risk_level', 'unknown')
                }
            },
            'final_result': detection_result
        }
        
        return final_result
        
    except Exception as e:
        # 실패 시 상태 업데이트
        self.update_state(state='FAILURE', meta={
            'error': str(e),
            'session_id': session_id,
            'message': f'오디오 분석 중 오류가 발생했습니다: {str(e)}'
        })
        raise e


async def process_audio_concat_async(
    session_id: str, 
    target_sr: int, 
    normalize: bool, 
    force_concat: bool
) -> Dict[str, Any]:
    """음성 파일 병합 비동기 처리"""
    
    # 기존 병합 파일 확인
    session_response = supabase_admin.table("sessions").select(
        "merged_audio_url"
    ).eq("id", session_id).execute()
    
    if not session_response.data:
        raise Exception("세션을 찾을 수 없습니다.")
    
    existing_merged_url = session_response.data[0].get("merged_audio_url")
    
    # 기존 파일이 있고 force_concat이 False인 경우 건너뛰기
    if existing_merged_url and not force_concat:
        return {
            'success': True,
            'skipped': True,
            'existing_url': existing_merged_url,
            'message': '기존 병합 파일을 사용합니다.'
        }
    
    # audio_analysis 라우터의 concat 로직 재사용을 위해 임포트
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'routers'))
    
    from audio_analysis import (
        _fetch_ordered_audio_urls_from_db,
        _get_session_user_family_info,
        _upload_merged_audio_to_storage,
        _update_session_merged_audio_url,
        _resolve_storage_url,
        _download_wav,
        _resample_if_needed,
        _peak_normalize
    )
    
    import numpy as np
    import soundfile as sf
    
    # URL 목록 획득
    print(f"🔍 세션 ID로 오디오 URL 조회 시작: {session_id}")
    ordered = await _fetch_ordered_audio_urls_from_db(session_id, supabase_admin)
    print(f"📊 조회된 오디오 URL 개수: {len(ordered) if ordered else 0}")
    if ordered:
        for i, (order, url) in enumerate(ordered):
            print(f"  - URL {i+1}: order={order}, url={url[:100]}{'...' if len(url) > 100 else ''}")
    if not ordered:
        raise Exception("해당 세션의 오디오 파일이 없습니다.")

    # 다운로드 + 전처리 + 병합
    chunks = []
    for order, url in ordered:
        try:
            # Service Role Key로 더 안정적인 Signed URL 생성
            if url.startswith(('http://', 'https://')):
                resolved_url = url
            else:
                try:
                    # 2시간 만료 Signed URL 생성
                    response = supabase_admin.storage.from_("voice").create_signed_url(
                        url, expires_in=7200
                    )
                    if response and response.get('signedURL'):
                        resolved_url = response['signedURL']
                        print(f"✅ Signed URL 생성 성공 (order={order})")
                    else:
                        raise Exception("Signed URL 생성 실패")
                except Exception as url_error:
                    print(f"⚠️ URL 해결 실패 (order={order}): {url_error}")
                    continue
            
            y, sr = await _download_wav(resolved_url)
            y = _resample_if_needed(y, sr, target_sr)
            if normalize:
                y = _peak_normalize(y)
            chunks.append(y.astype(np.float32))
            print(f"✅ 파일 처리 완료 (order={order})")
            
        except Exception as e:
            print(f"⚠️ 파일 다운로드 실패 (order={order}, url={url}): {str(e)}")
            # 개별 파일 실패 시에도 다른 파일들로 계속 진행
            continue

    if not chunks:
        raise Exception("병합할 오디오가 없습니다.")

    cat = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]

    # 임시 wav 생성
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    fname = f"session_{session_id}_{ts}.wav"
    tmpdir = tempfile.mkdtemp(prefix="concatwav_")
    fpath = os.path.join(tmpdir, fname)

    sf.write(fpath, cat, target_sr, subtype="PCM_16")
    
    # Supabase Storage에 업로드
    user_id, family_id = await _get_session_user_family_info(session_id, supabase_admin)
    storage_path = await _upload_merged_audio_to_storage(
        session_id, user_id, family_id, fpath, supabase_admin
    )
    await _update_session_merged_audio_url(session_id, storage_path, supabase_admin)
    
    # 임시 파일 정리
    try:
        os.unlink(fpath)
        os.rmdir(tmpdir)
    except:
        pass
    
    return {
        'success': True,
        'duration_sec': round(len(cat) / float(target_sr), 3),
        'storage_url': storage_path
    }


async def process_audio_features_async(session_id: str) -> Dict[str, Any]:
    """오디오 특징 추출 비동기 처리"""
    
    # audio_analysis 라우터의 특징 추출 로직 재사용
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'routers'))
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))
    
    from audio_analysis import _resolve_storage_url
    from audio_feature_extractor import AudioFeatureExtractor
    import httpx
    import tempfile
    
    # 병합된 오디오 파일 경로 가져오기
    response = supabase_admin.table("sessions").select(
        "merged_audio_url"
    ).eq("id", session_id).execute()
    
    if not response.data:
        raise Exception("세션을 찾을 수 없습니다.")
    
    merged_url = response.data[0].get("merged_audio_url")
    if not merged_url:
        raise Exception("병합된 오디오 파일이 없습니다. concat 단계를 먼저 실행하세요.")
    
    # Supabase Storage URL을 실제 파일로 다운로드
    resolved_url = _resolve_storage_url(merged_url, supabase_admin)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(resolved_url)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(response.content)
            audio_file_path = tmp_file.name
    
    try:
        # 특징 추출 실행
        extractor = AudioFeatureExtractor()
        features_list = extractor.extract_features(audio_file_path)
        
        if not features_list:
            raise Exception("특징 추출에 실패했습니다.")
        
        # 결과 반환
        features_df = extractor.features_to_dataframe(features_list)
        
        return {
            'success': True,
            'total_segments': len(features_list),
            'feature_names': extractor.feature_names,
            'features': features_df.to_dict('records') if features_df is not None else []
        }
        
    finally:
        # 임시 파일 정리
        try:
            os.unlink(audio_file_path)
        except:
            pass


async def process_dementia_detection_async(session_id: str, photo_id: Optional[str] = None) -> Dict[str, Any]:
    """치매 감지 비동기 처리"""
    
    # audio_analysis 라우터의 치매 감지 로직 재사용
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'routers'))
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))
    
    from audio_analysis import (
        _resolve_storage_url, 
        _get_session_user_family_info
    )
    from audio_dementia_detector import get_dementia_detector_service
    import httpx
    import tempfile
    
    # 병합된 오디오 파일 경로 가져오기
    response = supabase_admin.table("sessions").select(
        "merged_audio_url"
    ).eq("id", session_id).execute()
    
    if not response.data:
        raise Exception("세션을 찾을 수 없습니다.")
    
    merged_url = response.data[0].get("merged_audio_url")
    if not merged_url:
        raise Exception("병합된 오디오 파일이 없습니다.")
    
    resolved_url = _resolve_storage_url(merged_url, supabase_admin)
    
    # 임시 파일로 다운로드
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(resolved_url)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(response.content)
            audio_file_path = tmp_file.name
    
    try:
        # 치매 감지 서비스 사용
        detector = get_dementia_detector_service()
        if detector is None:
            raise Exception("치매 감지 서비스를 초기화할 수 없습니다.")
        
        # 치매 감지 실행
        result = await detector.detect_dementia_from_audio(audio_file_path)
        
        # 결과를 DB에 저장
        if result.get("success"):
            try:
                # session_id로 기존 레코드 확인
                existing = supabase_admin.table("session_audio_analysis").select(
                    "*"
                ).eq("session_id", session_id).execute()
                
                # user_id, family_id 가져오기
                user_id, family_id = await _get_session_user_family_info(session_id, supabase_admin)
                
                # photo_id 결정: 전달받은 값 우선, 없으면 sessions에서 추출
                final_photo_id = photo_id
                if not final_photo_id:
                    session_response = supabase_admin.table("sessions").select(
                        "selected_photos"
                    ).eq("id", session_id).execute()
                    
                    if session_response.data and session_response.data[0].get("selected_photos"):
                        selected_photos = session_response.data[0]["selected_photos"]
                        if isinstance(selected_photos, list) and len(selected_photos) > 0:
                            final_photo_id = selected_photos[0]
                
                # DB 저장 데이터 구성
                analysis_data = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "family_id": family_id,
                    "photo_id": final_photo_id,  # 결정된 photo_id 사용
                    "merged_audio_path": merged_url,
                    "total_slices": result["total_segments"],
                    "dementia_slices": result["dementia_segments_count"],
                    "risk_level": "risk" if result["dementia_ratio"] >= 0.6 else "suspect" if result["dementia_ratio"] >= 0.3 else "normal",
                    "adjusted_mean": None
                }
                
                if existing.data:
                    # 기존 레코드 업데이트
                    update_data = {k: v for k, v in analysis_data.items() if k != "session_id"}
                    supabase_admin.table("session_audio_analysis").update(
                        update_data
                    ).eq("session_id", session_id).execute()
                else:
                    # 새 레코드 생성
                    supabase_admin.table("session_audio_analysis").insert(
                        analysis_data
                    ).execute()
                
            except Exception as db_error:
                print(f"⚠️ DB 저장 실패 (결과는 반환): {db_error}")
        
        # 결과 반환
        result["session_id"] = session_id
        return result
        
    finally:
        # 임시 파일 정리
        try:
            os.unlink(audio_file_path)
        except:
            pass