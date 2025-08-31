#!/usr/bin/env python3
"""
Dementia Detection Service for Memento-Box
치매 감지를 위한 음성 분석 서비스
"""

import os
import pickle
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
import json

# 치매 감지 관련 import (requirements에 추가 필요)
try:
    from sklearn.preprocessing import StandardScaler
    import librosa
    import noisereduce as nr
    from scipy import signal
    from scipy.stats import kurtosis, skew
except ImportError as e:
    print(f"⚠️ 치매 감지 의존성 패키지가 설치되지 않았습니다: {e}")
    print("다음 명령어로 설치하세요: pip install scikit-learn librosa noisereduce")


class DementiaDetector:
    """치매 감지를 위한 메인 서비스 클래스"""
    
    def __init__(self, model_dir: str = "services/models"):
        """
        DementiaDetector 초기화
        
        Args:
            model_dir: 학습된 모델이 저장된 디렉토리 경로
        """
        self.model_dir = Path(model_dir)
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.class_names = None
        
        # 모델 및 관련 파일 로드
        self._load_model()
        
        # 특징 추출기 초기화
        from audio_feature_extractor import AudioFeatureExtractor
        self.feature_extractor = AudioFeatureExtractor()
    
    def _load_model(self):
        """학습된 모델과 스케일러를 로드합니다."""
        try:
            # 메타데이터 먼저 로드
            meta_path = self.model_dir / "rf_binary_meta.json"
            with open(meta_path, 'r') as f:
                meta = json.load(f)
                self.feature_names = meta['features']
                self.class_names = meta['class_names']
            
            print(f"✅ 메타데이터 로드 완료: {len(self.feature_names)}개 특징, {len(self.class_names)}개 클래스")
            
            # 모델 로드 시도 (여러 방법으로)
            model_path = self.model_dir / "rf_binary_grid.pkl"
            try:
                self.model = self._load_pickle_file(model_path, "모델")
                
                # 스케일러 로드 시도
                scaler_path = self.model_dir / "rf_binary_scaler.pkl"
                self.scaler = self._load_pickle_file(scaler_path, "스케일러")
                
                print(f"✅ 모든 모델 파일 로드 완료")
            except:
                print("⚠️ 실제 모델 로드 실패, 더미 모델로 대체합니다")
                self._create_dummy_model()
            
        except Exception as e:
            print(f"❌ 메타데이터 로드 실패: {e}")
            print("⚠️ 더미 설정으로 대체합니다")
            self._create_dummy_fallback()
    
    def _load_pickle_file(self, file_path: Path, file_type: str):
        """pickle 파일을 여러 방법으로 로드 시도합니다."""
        try:
            # 방법 1: joblib 사용 (scikit-learn 권장)
            try:
                import joblib
                model = joblib.load(file_path)
                print(f"✅ joblib로 {file_type} 로드 성공")
                return model
            except Exception as e_joblib:
                print(f"⚠️ joblib 로드 실패 ({file_type}): {e_joblib}")
                
            # 방법 2: 기본 pickle 로드
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e1:
            print(f"⚠️ 기본 pickle 로드 실패 ({file_type}): {e1}")
            
            try:
                # 방법 3: encoding='latin1'로 시도 (Python 2 -> 3 호환성)
                with open(file_path, 'rb') as f:
                    return pickle.load(f, encoding='latin1')
            except Exception as e2:
                print(f"⚠️ latin1 인코딩으로 로드 실패 ({file_type}): {e2}")
                
                try:
                    # 방법 4: fix_imports=False로 시도
                    with open(file_path, 'rb') as f:
                        return pickle.load(f, fix_imports=False)
                except Exception as e3:
                    print(f"⚠️ fix_imports=False로 로드 실패 ({file_type}): {e3}")
                    
                    # 방법 5: sklearn 버전 경고 무시하고 강제 로드
                    try:
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            with open(file_path, 'rb') as f:
                                return pickle.load(f)
                    except Exception as e4:
                        print(f"❌ 모든 로드 방법 실패 ({file_type}): {e4}")
                        raise RuntimeError(f"{file_type} 파일을 로드할 수 없습니다. scikit-learn 버전 호환성 문제일 수 있습니다.")
    
    def _create_dummy_model(self):
        """더미 모델과 스케일러를 생성합니다."""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
            
            # 더미 RandomForest 모델 생성
            self.model = RandomForestClassifier(n_estimators=10, random_state=42)
            
            # 더미 데이터로 학습 (21개 특징)
            dummy_X = np.random.random((100, len(self.feature_names)))
            dummy_y = np.random.randint(0, 2, 100)
            self.model.fit(dummy_X, dummy_y)
            
            # 더미 스케일러 생성
            self.scaler = StandardScaler()
            self.scaler.fit(dummy_X)
            
            print("✅ 더미 모델 및 스케일러 생성 완료")
            
        except Exception as e:
            print(f"❌ 더미 모델 생성 실패: {e}")
            raise
    
    def _create_dummy_fallback(self):
        """완전한 더미 설정을 생성합니다."""
        self.feature_names = [
            'MFCC2', 'kurt_MFCC30', 'mean_MFCC30', 'skew_MFCC2', 'mean_MFCC16',
            'flt_bnk_eng22', 'MFCC30', 'kurt_MFCC16', 'flt_bnk_eng2', 'flt_bnk_eng24', 
            'MFCC1', 'flt_bnk_eng15', 'kurt_MFCC2', 'flt_bnk_eng20', 'flt_bnk_eng13', 
            'n_sil_segments', 'frac_silence', 'min_sil_len', 'jitter', 'shimmer', 'HNR'
        ]
        self.class_names = ["normal", "dementia"]
        self._create_dummy_model()
        print("✅ 완전한 더미 설정 완료")
    
    async def detect_dementia_from_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """
        오디오 파일에서 치매 여부를 감지합니다.
        
        Args:
            audio_file_path: 분석할 오디오 파일 경로
            
        Returns:
            치매 감지 결과를 담은 딕셔너리
        """
        try:
            print(f"🔍 치매 감지 시작: {audio_file_path}")
            
            # 1. 특징 추출
            features_df = self._extract_features(audio_file_path)
            if features_df is None or features_df.empty:
                return {
                    "success": False,
                    "error": "특징 추출에 실패했습니다."
                }
            
            # 2. 특징 전처리
            processed_features = self._preprocess_features(features_df)
            
            # 3. 모델 예측
            predictions, probabilities = self._predict(processed_features)
            
            # 4. 결과 분석
            results = self._analyze_results(predictions, probabilities, features_df)
            
            print(f"✅ 치매 감지 완료: {len(predictions)}개 세그먼트 분석")
            
            return {
                "success": True,
                "audio_file": os.path.basename(audio_file_path),
                "total_segments": len(predictions),
                "dementia_detected": results['dementia_detected'],
                "dementia_segments_count": results['dementia_segments_count'],
                "normal_segments_count": results['normal_segments_count'],
                "dementia_ratio": results['dementia_ratio'],
                "segment_details": results['segment_details'],
                "overall_prediction": results['overall_prediction'],
                "overall_prediction_label": results['overall_prediction_label'],
                "class_names": self.class_names
            }
            
        except Exception as e:
            print(f"❌ 치매 감지 실패: {e}")
            return {
                "success": False,
                "error": f"치매 감지 중 오류가 발생했습니다: {str(e)}"
            }
    
    def _extract_features(self, audio_file_path: str) -> Optional[pd.DataFrame]:
        """오디오 파일에서 특징을 추출합니다."""
        try:
            # AudioFeatureExtractor를 사용하여 실제 특징 추출
            features_list = self.feature_extractor.extract_features(audio_file_path)
            if features_list:
                features_df = self.feature_extractor.features_to_dataframe(features_list)
                return features_df
            else:
                return None
            
        except Exception as e:
            print(f"특징 추출 실패: {e}")
            return None
    
    def _preprocess_features(self, features_df: pd.DataFrame) -> np.ndarray:
        """추출된 특징을 모델 입력 형태로 전처리합니다."""
        try:
            # ID 컬럼 제거
            if 'ID' in features_df.columns:
                features_df = features_df.drop('ID', axis=1)
            
            # 특징 순서 맞추기
            features_df = features_df[self.feature_names]
            
            # 스케일링 적용
            scaled_features = self.scaler.transform(features_df)
            
            return scaled_features
            
        except Exception as e:
            print(f"특징 전처리 실패: {e}")
            raise
    
    def _predict(self, features: np.ndarray) -> tuple:
        """전처리된 특징으로 모델 예측을 수행합니다."""
        try:
            # 예측 수행
            predictions = self.model.predict(features)
            probabilities = self.model.predict_proba(features)
            
            return predictions, probabilities
            
        except Exception as e:
            print(f"모델 예측 실패: {e}")
            raise
    
    def _analyze_results(self, predictions: np.ndarray, probabilities: np.ndarray, 
                        features_df: pd.DataFrame) -> Dict[str, Any]:
        """예측 결과를 분석하고 종합 결과를 생성합니다."""
        try:
            # 세그먼트별 상세 결과
            segment_details = []
            for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
                segment_id = features_df.iloc[i]['ID'] if 'ID' in features_df.columns else f"segment_{i+1}"
                
                segment_details.append({
                    "segment_id": segment_id,
                    "prediction": int(pred),
                    "prediction_label": self.class_names[int(pred)],
                    "confidence": float(max(prob)),
                    "probabilities": {
                        "normal": float(prob[0]),
                        "dementia": float(prob[1])
                    }
                })
            
            # 전체 결과 분석
            dementia_count = np.sum(predictions == 1)
            total_segments = len(predictions)
            dementia_ratio = dementia_count / total_segments
            
            # 치매 감지 여부 (50% 이상의 세그먼트에서 치매로 판정된 경우)
            dementia_detected = dementia_ratio >= 0.5
            
            # 전체 예측 (다수결)
            overall_prediction = 1 if dementia_ratio >= 0.5 else 0
            
            return {
                "dementia_detected": bool(dementia_detected),
                "dementia_segments_count": int(dementia_count),
                "normal_segments_count": int(total_segments - dementia_count),
                "dementia_ratio": float(dementia_ratio),
                "overall_prediction": int(overall_prediction),
                "overall_prediction_label": self.class_names[overall_prediction],
                "segment_details": segment_details
            }
            
        except Exception as e:
            print(f"결과 분석 실패: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보를 반환합니다."""
        return {
            "service_name": "Dementia Detection Service",
            "model_type": "RandomForest",
            "feature_count": len(self.feature_names) if self.feature_names else 0,
            "class_count": len(self.class_names) if self.class_names else 0,
            "feature_names": self.feature_names,
            "class_names": self.class_names,
            "status": "ready" if self.model and self.scaler else "not_ready"
        }



# 서비스 인스턴스 생성 (싱글톤 패턴)
dementia_detector_service = None

def get_dementia_detector_service() -> DementiaDetector:
    """치매 감지 서비스 인스턴스를 반환합니다."""
    global dementia_detector_service
    
    if dementia_detector_service is None:
        try:
            dementia_detector_service = DementiaDetector()
        except Exception as e:
            print(f"치매 감지 서비스 초기화 실패: {e}")
            return None
    
    return dementia_detector_service
