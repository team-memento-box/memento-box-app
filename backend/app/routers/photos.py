from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import uuid
from datetime import datetime
import tempfile
import os

from core.auth import get_current_user_from_header
from core.config import supabase_admin, settings
from services.image_analyzer import ImageAnalyzer

router = APIRouter()

class PhotoAnalysisResponse(BaseModel):
    photo_id: str
    analysis_result: dict
    analyzed_at: datetime
    success: bool
    message: str

@router.post("/photos/{photo_id}/analyze", response_model=PhotoAnalysisResponse)
async def analyze_photo(
    photo_id: str,
    user_info: dict = Depends(get_current_user_from_header)
):
    """
    사진을 OpenAI GPT-4o로 분석하고 결과를 DB에 저장
    """
    print(f"\n" + "="*80)
    print(f"🚀 [PHOTO_ANALYSIS] 엔드포인트 호출됨")
    print(f"📷 [PHOTO_ANALYSIS] photo_id: {photo_id}")
    print(f"👤 [PHOTO_ANALYSIS] 인증된 사용자: {user_info}")
    print(f"⏰ [PHOTO_ANALYSIS] 요청 시간: {datetime.now().isoformat()}")
    print("="*80)
    try:
        user_id = user_info["id"]
        print(f"📤 [PHOTO_ANALYSIS] 사용자 인증 완료 - user_id: {user_id}")
        
        # 1. 사용자가 해당 사진의 소유자인지 확인
        print(f"🔍 [PHOTO_ANALYSIS] STEP 1: DB에서 사진 정보 조회 시작")
        print(f"🔍 [PHOTO_ANALYSIS] 조회 조건 - photo_id: {photo_id}, user_id: {user_id}")
        
        try:
            photo_response = supabase_admin.table("photos").select("*").eq("id", photo_id).eq("user_id", user_id).execute()
            print(f"✅ [PHOTO_ANALYSIS] DB 조회 성공")
            print(f"📊 [PHOTO_ANALYSIS] DB 조회 결과: {len(photo_response.data) if photo_response.data else 0}개 레코드")
            
            if photo_response.data:
                print(f"📋 [PHOTO_ANALYSIS] 첫 번째 레코드 키들: {list(photo_response.data[0].keys())}")
            
        except Exception as db_error:
            print(f"❌ [PHOTO_ANALYSIS] DB 조회 실패: {db_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"DB 조회 중 오류 발생: {str(db_error)}"
            )
        
        if not photo_response.data:
            print(f"❌ [PHOTO_ANALYSIS] 사진을 찾을 수 없음 - photo_id: {photo_id}, user_id: {user_id}")
            # 디버깅: 해당 photo_id가 존재하는지 확인
            print(f"🔍 [PHOTO_ANALYSIS] 디버깅: photo_id 존재 여부 확인")
            all_photos_response = supabase_admin.table("photos").select("id,user_id").eq("id", photo_id).execute()
            if all_photos_response.data:
                actual_user_id = all_photos_response.data[0]["user_id"]
                print(f"⚠️ [PHOTO_ANALYSIS] 사진은 존재하지만 다른 사용자 소유: actual_user_id={actual_user_id}")
            else:
                print(f"⚠️ [PHOTO_ANALYSIS] photo_id가 DB에 존재하지 않음")
                
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사진을 찾을 수 없거나 접근 권한이 없습니다."
            )
        
        photo_data = photo_response.data[0]
        file_path = photo_data["file_path"]
        print(f"✅ [PHOTO_ANALYSIS] STEP 1 완료 - 사진 정보 확인됨")
        print(f"📁 [PHOTO_ANALYSIS] file_path: {file_path}")
        print(f"📸 [PHOTO_ANALYSIS] 사진 메타데이터: filename={photo_data.get('filename', 'N/A')}, size={photo_data.get('file_size', 'N/A')}")
        
        # 2. Supabase Storage에서 이미지 파일 다운로드
        print(f"🔍 [PHOTO_ANALYSIS] STEP 2: Supabase Storage에서 이미지 다운로드 시작")
        print(f"📁 [PHOTO_ANALYSIS] 다운로드 경로: {file_path}")
        
        try:
            file_response = supabase_admin.storage.from_("photos").download(file_path)
            image_bytes = file_response
            print(f"✅ [PHOTO_ANALYSIS] 이미지 다운로드 완료")
            print(f"📏 [PHOTO_ANALYSIS] 파일 크기: {len(image_bytes)} bytes ({len(image_bytes)/1024:.1f} KB)")
            
            # 이미지 타입 확인 (첫 몇 바이트로 파일 타입 추측)
            if len(image_bytes) > 10:
                header = image_bytes[:10]
                if header[:2] == b'\xff\xd8':
                    file_type = "JPEG"
                elif header[:8] == b'\x89PNG\r\n\x1a\n':
                    file_type = "PNG"
                elif header[:6] in (b'GIF87a', b'GIF89a'):
                    file_type = "GIF"
                else:
                    file_type = f"Unknown (header: {header.hex()})"
                print(f"🖼️ [PHOTO_ANALYSIS] 파일 타입: {file_type}")
            
        except Exception as e:
            print(f"❌ [PHOTO_ANALYSIS] 이미지 다운로드 실패")
            print(f"❌ [PHOTO_ANALYSIS] 에러 타입: {type(e).__name__}")
            print(f"❌ [PHOTO_ANALYSIS] 에러 메시지: {str(e)}")
            import traceback
            print(f"📋 [PHOTO_ANALYSIS] 상세 스택 트레이스:")
            print(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"이미지 파일을 다운로드할 수 없습니다: {str(e)}"
            )
        
        # 3. 임시 파일로 저장 (ImageAnalyzer가 파일 경로를 필요로 함)
        print(f"🔍 [PHOTO_ANALYSIS] STEP 3: 임시 파일 생성 및 이미지 분석")
        temp_file = None
        try:
            print(f"📄 [PHOTO_ANALYSIS] 임시 파일 생성 중...")
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file.write(image_bytes)
            temp_file.close()
            print(f"✅ [PHOTO_ANALYSIS] 임시 파일 생성 완료")
            print(f"📁 [PHOTO_ANALYSIS] 임시 파일 경로: {temp_file.name}")
            print(f"📏 [PHOTO_ANALYSIS] 임시 파일 크기 확인: {os.path.getsize(temp_file.name)} bytes")
            
            # 4. ImageAnalyzer로 분석 수행
            print(f"🤖 [PHOTO_ANALYSIS] STEP 4: ImageAnalyzer 초기화")
            try:
                analyzer = ImageAnalyzer()
                print(f"✅ [PHOTO_ANALYSIS] ImageAnalyzer 초기화 성공")
            except Exception as init_error:
                print(f"❌ [PHOTO_ANALYSIS] ImageAnalyzer 초기화 실패: {init_error}")
                raise
            
            print(f"🔍 [PHOTO_ANALYSIS] 이미지 분석 시작...")
            analysis_start_time = datetime.now()
            
            try:
                analysis_result = analyzer.analyze_image(temp_file.name)
                analysis_end_time = datetime.now()
                analysis_duration = (analysis_end_time - analysis_start_time).total_seconds()
                
                print(f"✅ [PHOTO_ANALYSIS] 이미지 분석 완료")
                print(f"⏱️ [PHOTO_ANALYSIS] 분석 소요 시간: {analysis_duration:.2f}초")
                print(f"📊 [PHOTO_ANALYSIS] 분석 결과 존재 여부: {analysis_result is not None}")
                
                if analysis_result is not None:
                    print(f"🔑 [PHOTO_ANALYSIS] 분석 결과 키들: {list(analysis_result.keys()) if isinstance(analysis_result, dict) else 'Not a dict'}")
                    print(f"📝 [PHOTO_ANALYSIS] 분석 결과 타입: {type(analysis_result)}")
                    if isinstance(analysis_result, dict):
                        for key, value in analysis_result.items():
                            if isinstance(value, str):
                                print(f"📄 [PHOTO_ANALYSIS] {key}: {value[:100]}{'...' if len(str(value)) > 100 else ''}")
                            else:
                                print(f"📄 [PHOTO_ANALYSIS] {key}: {type(value)} - {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
            
            except Exception as analysis_error:
                print(f"❌ [PHOTO_ANALYSIS] 이미지 분석 실패")
                print(f"❌ [PHOTO_ANALYSIS] 분석 에러 타입: {type(analysis_error).__name__}")
                print(f"❌ [PHOTO_ANALYSIS] 분석 에러 메시지: {str(analysis_error)}")
                raise analysis_error
            
            if analysis_result is None:
                print(f"❌ [PHOTO_ANALYSIS] ImageAnalyzer에서 None 반환")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="이미지 분석에 실패했습니다."
                )
            
        except Exception as analyzer_error:
            print(f"❌ [PHOTO_ANALYSIS] ImageAnalyzer 전체 예외 발생")
            print(f"❌ [PHOTO_ANALYSIS] 예외 타입: {type(analyzer_error).__name__}")
            print(f"❌ [PHOTO_ANALYSIS] 예외 메시지: {str(analyzer_error)}")
            import traceback
            print(f"📋 [PHOTO_ANALYSIS] 상세 스택 트레이스:")
            print(traceback.format_exc())
            raise
        finally:
            # 임시 파일 정리
            if temp_file and os.path.exists(temp_file.name):
                print(f"🗑️ [PHOTO_ANALYSIS] 임시 파일 삭제: {temp_file.name}")
                os.unlink(temp_file.name)
                print(f"✅ [PHOTO_ANALYSIS] 임시 파일 삭제 완료")
        
        # 5. 분석 결과를 DB에 저장
        print(f"🔍 [PHOTO_ANALYSIS] STEP 5: 분석 결과 DB 저장")
        analyzed_at = datetime.now()
        print(f"⏰ [PHOTO_ANALYSIS] 분석 완료 시간: {analyzed_at.isoformat()}")
        
        try:
            print(f"💾 [PHOTO_ANALYSIS] DB 업데이트 시작...")
            update_response = supabase_admin.table("photos").update({
                "photo_analyze_result": analysis_result,
                "analyzed_at": analyzed_at.isoformat()
            }).eq("id", photo_id).eq("user_id", user_id).execute()
            
            print(f"✅ [PHOTO_ANALYSIS] DB 업데이트 성공")
            print(f"📊 [PHOTO_ANALYSIS] 업데이트된 레코드 수: {len(update_response.data) if update_response.data else 0}개")
            
            if update_response.data:
                updated_record = update_response.data[0]
                print(f"📋 [PHOTO_ANALYSIS] 업데이트된 레코드 ID: {updated_record.get('id', 'N/A')}")
                print(f"📋 [PHOTO_ANALYSIS] 분석 결과 저장 확인: {updated_record.get('photo_analyze_result') is not None}")
                
        except Exception as db_update_error:
            print(f"❌ [PHOTO_ANALYSIS] DB 업데이트 실패")
            print(f"❌ [PHOTO_ANALYSIS] DB 에러 타입: {type(db_update_error).__name__}")
            print(f"❌ [PHOTO_ANALYSIS] DB 에러 메시지: {str(db_update_error)}")
            import traceback
            print(f"📋 [PHOTO_ANALYSIS] DB 에러 스택 트레이스:")
            print(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"분석 결과 저장 중 오류 발생: {str(db_update_error)}"
            )
        
        if not update_response.data:
            print(f"❌ [PHOTO_ANALYSIS] DB 업데이트 실패 - 응답 데이터가 없음")
            print(f"🔍 [PHOTO_ANALYSIS] 디버깅: photo_id와 user_id 조합 재확인")
            # 다시 한 번 해당 레코드가 존재하는지 확인
            check_response = supabase_admin.table("photos").select("id").eq("id", photo_id).eq("user_id", user_id).execute()
            if check_response.data:
                print(f"⚠️ [PHOTO_ANALYSIS] 레코드는 존재하지만 업데이트가 안됨")
            else:
                print(f"⚠️ [PHOTO_ANALYSIS] 업데이트 중에 레코드가 사라짐")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="분석 결과 저장에 실패했습니다."
            )
        
        print(f"🎉 [PHOTO_ANALYSIS] *** 사진 분석 전체 프로세스 완료 ***")
        print(f"📷 [PHOTO_ANALYSIS] Photo ID: {photo_id}")
        print(f"👤 [PHOTO_ANALYSIS] User ID: {user_id}")
        print(f"⏰ [PHOTO_ANALYSIS] 완료 시간: {analyzed_at.isoformat()}")
        print(f"✅ [PHOTO_ANALYSIS] 성공적으로 응답 반환")
        print("="*80)
        
        return PhotoAnalysisResponse(
            photo_id=photo_id,
            analysis_result=analysis_result,
            analyzed_at=analyzed_at,
            success=True,
            message="사진 분석이 완료되었습니다."
        )
        
    except HTTPException as http_exc:
        print(f"\n❌ [PHOTO_ANALYSIS] *** HTTP 예외 발생 ***")
        print(f"❌ [PHOTO_ANALYSIS] 상태 코드: {http_exc.status_code}")
        print(f"❌ [PHOTO_ANALYSIS] 에러 메시지: {http_exc.detail}")
        print(f"❌ [PHOTO_ANALYSIS] 헤더: {http_exc.headers}")
        print("="*80)
        raise
    except Exception as e:
        print(f"\n❌ [PHOTO_ANALYSIS] *** 예상치 못한 예외 발생 ***")
        print(f"❌ [PHOTO_ANALYSIS] 예외 타입: {type(e).__name__}")
        print(f"❌ [PHOTO_ANALYSIS] 예외 메시지: {str(e)}")
        import traceback
        print(f"📋 [PHOTO_ANALYSIS] 전체 스택 트레이스:")
        print(traceback.format_exc())
        print("="*80)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사진 분석 중 예상치 못한 오류가 발생했습니다: {str(e)}"
        )

@router.get("/photos/{photo_id}/analysis")
async def get_photo_analysis(
    photo_id: str,
    user_info: dict = Depends(get_current_user_from_header)
):
    """
    특정 사진의 분석 결과 조회
    """
    try:
        user_id = user_info["id"]
        
        photo_response = supabase_admin.table("photos").select(
            "id, photo_analyze_result, analyzed_at"
        ).eq("id", photo_id).eq("user_id", user_id).execute()
        
        if not photo_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사진을 찾을 수 없거나 접근 권한이 없습니다."
            )
        
        photo_data = photo_response.data[0]
        
        return {
            "photo_id": photo_id,
            "analysis_result": photo_data.get("photo_analyze_result"),
            "analyzed_at": photo_data.get("analyzed_at"),
            "has_analysis": photo_data.get("photo_analyze_result") is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get photo analysis error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"분석 결과 조회 중 오류가 발생했습니다: {str(e)}"
        )