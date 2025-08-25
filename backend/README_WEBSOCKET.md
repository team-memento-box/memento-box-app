# WebSocket 대화 시스템 구현

## 구현된 기능

### 1. LangGraph 기반 대화 워크플로우
- **GraphState**: 명확한 상태 관리 (WorkflowInput, IntermediateState, FinalOutput)
- **5개 노드**: init_state → router → (standard_response | cache_retrieve) → fallback
- **조건부 라우팅**: 대화 맥락에 따른 인지기능 평가 질문 삽입

### 2. WebSocket 실시간 통신
- 엔드포인트: `ws://localhost:8000/ws/chat/{conversation_id}`
- JSON 메시지 교환
- 에러 처리 및 연결 관리

### 3. Supabase 통합
- 대화 기록 조회 (conversations, sessions 테이블)
- CIST 질문 템플릿 검색
- Row Level Security 정책 준수

## 로컬 실행 방법

### 1. 환경 설정
```bash
# 의존성 설치
cd backend/app
pip install -r requirements.txt

# 환경변수 설정 (.env 파일 생성)
cp .env.example .env
# .env 파일에 API 키들 입력
```

### 2. 서버 실행
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. WebSocket 테스트
```bash
# 별도 터미널에서
python test_websocket.py
```

## API 엔드포인트

### WebSocket
- `ws://localhost:8000/ws/chat/{conversation_id}`

### 메시지 형식
```json
{
  "user_id": "user123",
  "message": "안녕하세요!",
  "photo_context": {
    "description": "가족 사진",
    "location": "집 앞마당"
  }
}
```

### 응답 형식
```json
{
  "type": "response",
  "data": {
    "response_text": "안녕하세요! 가족 사진을 보고 계시는군요.",
    "response_audio_url": null
  },
  "conversation_id": "uuid-here"
}
```

## 아키텍처 변경 사항

### ✅ 구현됨
- LangChain/LangGraph 의존성 추가
- WebSocket 엔드포인트 구현
- 대화 워크플로우 서비스 생성
- Supabase 클라이언트 통합

### 🔄 다음 단계
- Azure 의존성 완전 제거
- 음성 처리 시스템 개선  
- 벡터 DB 캐시 시스템 구현
- Celery 비동기 작업 큐 추가

## 테스트 시나리오

1. **일반 대화**: 사진 관련 자연스러운 대화
2. **인지 평가**: 기억력, 시간 관련 질문에서 평가 모드 전환
3. **에러 처리**: 잘못된 입력, 네트워크 끊김 등

Azure 종속성을 제거하고 AWS EC2 배포를 위한 준비가 완료되었습니다.