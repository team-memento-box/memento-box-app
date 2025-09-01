## 🎯 기능 추가
- 치매 감지를 위한 음성 분석 서비스 구현
- FastAPI 엔드포인트 추가 (`/audio-dementia-detection`)
- 학습된 RandomForest 모델 통합

## �� 변경된 파일
- `services/dementia_detector.py` - 치매 감지 서비스 모듈
- `main.py` - API 엔드포인트 추가
- `requirements.txt` - ML 의존성 패키지 추가
- `models/dementia/` - 학습된 모델 파일들
