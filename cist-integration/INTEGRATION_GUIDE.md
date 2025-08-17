# CIST 통합 시스템 - 기존 시스템 통합 가이드

## 개요

이 문서는 새로 개발된 CIST(Cognitive Impairment Screening Test) 통합 시스템을 기존 Memento Box 시스템에 통합하는 방법을 설명합니다.

## 아키텍처 통합 방식

### 1. 마이크로서비스 방식 (권장)

```
[기존 app/] ←→ [CIST Service] ←→ [dialogue/]
```

**장점:**
- 기존 시스템 변경 최소화
- 독립적인 개발/배포 가능
- 확장성 및 유지보수성 높음

**구현 방법:**
1. CIST 서비스를 별도 FastAPI 애플리케이션으로 배포
2. HTTP API를 통해 기존 시스템과 통신
3. 데이터베이스는 기존 DB 활용 또는 별도 DB 사용

### 2. 라이브러리 통합 방식

```
[기존 app/] ← [CIST Integration Library]
```

**장점:**
- 단일 애플리케이션으로 관리
- 네트워크 통신 오버헤드 없음

**구현 방법:**
1. cist-integration을 Python 패키지로 패키징
2. 기존 app/의 requirements.txt에 추가
3. 기존 서비스 클래스에서 직접 import하여 사용

## 기존 시스템 연동 포인트

### 1. 대화 시작 시점 연동

**기존 시스템:** `app/routers/chat.py`의 `/start` 엔드포인트

```python
# 기존 코드 수정 예시
@router.post("/start")
async def start_chat(image_id: str, db: Session = Depends(get_db)):
    # ... 기존 로직 ...
    
    # CIST 통합 서비스 초기화
    from cist_integration.services.cist_service import CISTIntegrationService
    
    cist_service = CISTIntegrationService(
        openai_api_key=settings.AZURE_OPENAI_KEY
    )
    
    # 사진 분석 결과를 CIST 서비스에 전달
    photo_analysis = {
        "caption": "사진 설명",
        "mood": "따뜻함",
        "objects": ["사람", "테이블"],
        "people_count": 2
    }
    
    # CIST 대화 세션 시작
    cist_result = await cist_service.start_conversation(
        conversation_id=str(conversation_id),
        user_id=user_id,
        photo_id=image_id,
        photo_analysis=photo_analysis
    )
    
    # 기존 응답에 CIST 정보 추가
    response_data["cist_enabled"] = True
    response_data["cist_message"] = cist_result.get("message")
    
    return JSONResponse(content=response_data)
```

### 2. 사용자 응답 처리 연동

**기존 시스템:** `app/routers/chat.py`의 사용자 응답 처리 부분

```python
# 새로운 엔드포인트 또는 기존 엔드포인트 확장
@router.post("/user_answer_with_cist")
async def answer_chat_with_cist(
    conversation_id: UUID = Form(...),
    user_input: str = Form(...),
    db: Session = Depends(get_db)
):
    # CIST 서비스로 사용자 입력 처리
    cist_service = get_cist_service()  # 싱글톤 또는 의존성 주입
    
    cist_result = await cist_service.process_user_input(
        conversation_id=str(conversation_id),
        user_input=user_input
    )
    
    # 기존 Turn 데이터베이스에 CIST 평가 결과 추가 저장
    if cist_result.get("current_cist_item"):
        # CIST 평가 결과를 Turn 테이블의 JSON 필드에 저장
        last_turn = get_last_turn(db, conversation_id)
        if last_turn:
            last_turn.turn["cist_evaluation"] = {
                "item_id": cist_result["current_cist_item"]["item_id"],
                "score": cist_result["current_score"]
            }
            db.commit()
    
    return JSONResponse(content=cist_result)
```

### 3. 대화 종료 시 연동

**기존 시스템:** `app/routers/chat.py`의 `/end` 엔드포인트

```python
@router.post("/end")
async def end_chat(conversation_id: UUID = Form(...), db: Session = Depends(get_db)):
    # ... 기존 로직 ...
    
    # CIST 평가 결과 생성
    cist_service = get_cist_service()
    cist_summary = await cist_service.get_evaluation_summary(str(conversation_id))
    cist_report = await cist_service.get_detailed_report(str(conversation_id))
    
    # AnomalyReport에 CIST 결과 추가
    try:
        new_report = AnomalyReport(
            id=uuid4(),
            conv_id=conversation_id,
            anomaly_report=analysis_txt,  # 기존 분석
            anomaly_turn=None,
            cist_evaluation=cist_summary,  # 새로 추가
            cist_detailed_report=cist_report  # 새로 추가
        )
        db.add(new_report)
        db.commit()
    except Exception as e:
        # 에러 처리
        pass
    
    # CIST 세션 정리
    cist_service.cleanup_conversation(str(conversation_id))
    
    return results
```

## 데이터베이스 스키마 확장

### 1. AnomalyReport 테이블 확장

```python
# app/db/models/anomaly_report.py 수정
class AnomalyReport(Base):
    # ... 기존 필드들 ...
    
    # CIST 평가 결과 추가
    cist_evaluation = Column(JSON, nullable=True)  # CIST 요약 결과
    cist_detailed_report = Column(Text, nullable=True)  # CIST 상세 보고서
    cist_completed_at = Column(DateTime, nullable=True)  # CIST 완료 시각
```

### 2. Turn 테이블 JSON 필드 활용

```python
# 기존 Turn 테이블의 turn JSON 필드에 CIST 정보 추가
turn_data = {
    "q_text": "질문 텍스트",
    "q_voice": "질문 음성 URL",
    "a_text": "답변 텍스트", 
    "a_voice": "답변 음성 URL",
    # CIST 관련 정보 추가
    "cist_item_id": "orientation_time",  # 해당 턴에서 평가된 CIST 문항
    "cist_score": 3,  # 해당 문항 점수
    "cist_integrated": True  # CIST 문항이 자연스럽게 통합되었는지 여부
}
```

## 환경 설정

### 1. 의존성 추가

```txt
# app/requirements.txt에 추가
langchain>=0.1.0
langgraph>=0.0.40
langchain-openai>=0.1.0
```

### 2. 환경 변수 설정

```env
# .env 파일에 CIST 관련 설정 추가
CIST_ENABLED=true
CIST_MIN_ITEMS_TO_COMPLETE=5
CIST_MAX_CONVERSATION_TURNS=50
```

## API 엔드포인트 추가

### 1. CIST 전용 라우터 생성

```python
# app/routers/cist.py (새로 생성)
from fastapi import APIRouter, Depends
from cist_integration.services.cist_service import CISTIntegrationService

router = APIRouter(prefix="/cist", tags=["cist"])

@router.get("/evaluation/{conversation_id}")
async def get_cist_evaluation(conversation_id: str):
    """CIST 평가 결과 조회"""
    service = get_cist_service()
    return await service.get_evaluation_summary(conversation_id)

@router.get("/report/{conversation_id}")
async def get_cist_report(conversation_id: str):
    """CIST 상세 보고서 조회"""
    service = get_cist_service()
    return await service.get_detailed_report(conversation_id)

@router.get("/status/{conversation_id}")
async def get_cist_status(conversation_id: str):
    """CIST 진행 상태 조회"""
    service = get_cist_service()
    return service.get_conversation_status(conversation_id)
```

### 2. 메인 앱에 라우터 등록

```python
# app/main.py 수정
from routers import auth, photo, conversation, chat, report, cist

app.include_router(cist.router)  # 추가
```

## 프론트엔드 연동 가이드

### 1. 대화 UI 확장

```javascript
// CIST 진행 상태 표시
const showCistProgress = (cist_info) => {
    if (cist_info.current_cist_item) {
        // 현재 평가 중인 문항 표시
        showNotification(`인지기능 평가 중: ${cist_info.current_cist_item.item_name}`);
    }
    
    // 진행률 표시
    const progress = (cist_info.completed_items / cist_info.total_items) * 100;
    updateProgressBar(progress);
};

// 평가 완료 시 결과 표시
const showCistResults = async (conversation_id) => {
    const response = await fetch(`/cist/evaluation/${conversation_id}`);
    const evaluation = await response.json();
    
    displayEvaluationSummary(evaluation);
};
```

### 2. 평가 결과 대시보드

```javascript
// CIST 평가 결과 대시보드 컴포넌트
const CistDashboard = ({ conversation_id }) => {
    const [evaluation, setEvaluation] = useState(null);
    
    useEffect(() => {
        fetchEvaluation();
    }, [conversation_id]);
    
    const fetchEvaluation = async () => {
        const response = await fetch(`/cist/evaluation/${conversation_id}`);
        const data = await response.json();
        setEvaluation(data);
    };
    
    return (
        <div className="cist-dashboard">
            <h3>인지기능 평가 결과</h3>
            <div className="score-summary">
                총점: {evaluation?.total_score}/{evaluation?.max_score} 
                ({evaluation?.percentage}%)
            </div>
            <div className="domain-scores">
                {/* 영역별 점수 표시 */}
            </div>
            <div className="recommendations">
                {/* 권고사항 표시 */}
            </div>
        </div>
    );
};
```

## 배포 및 운영

### 1. Docker 컨테이너 설정

```dockerfile
# CIST 서비스 전용 Dockerfile (마이크로서비스 방식 선택 시)
FROM python:3.11-slim

WORKDIR /app
COPY cist-integration/ .
COPY requirements.txt .

RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 2. 모니터링 포인트

- CIST 평가 완료율
- 각 문항별 평균 점수
- 대화 중 CIST 통합 성공률
- 평가 결과의 위험도 분포

## 테스트 시나리오

### 1. 단위 테스트

```python
# tests/test_cist_integration.py
import pytest
from cist_integration.services.cist_service import CISTIntegrationService

@pytest.mark.asyncio
async def test_start_conversation():
    service = CISTIntegrationService("test-api-key")
    result = await service.start_conversation(
        conversation_id="test-123",
        photo_analysis={"caption": "테스트 사진"}
    )
    assert result["status"] == "started"

@pytest.mark.asyncio  
async def test_cist_item_integration():
    # CIST 문항 통합 테스트
    pass

@pytest.mark.asyncio
async def test_evaluation_scoring():
    # 평가 점수 계산 테스트
    pass
```

### 2. 통합 테스트

```python
# tests/test_system_integration.py
@pytest.mark.asyncio
async def test_full_conversation_flow():
    """전체 대화 흐름 통합 테스트"""
    # 1. 대화 시작
    # 2. 사용자 입력 처리
    # 3. CIST 문항 자동 통합
    # 4. 평가 결과 생성
    # 5. 대화 종료
    pass
```

## 주의사항 및 고려사항

### 1. 성능 고려사항

- LLM API 호출 최적화 (배치 처리, 캐싱)
- 대화 상태 메모리 관리 (Redis 활용 고려)
- 긴 대화에서의 토큰 제한 관리

### 2. 보안 고려사항

- 개인정보 보호 (대화 내용, 평가 결과)
- API 키 보안 관리
- 평가 결과 접근 권한 관리

### 3. 사용자 경험 고려사항

- CIST 평가가 자연스럽게 느껴지도록
- 평가 결과에 대한 적절한 설명 제공
- 의료진이 아닌 사용자도 이해할 수 있는 표현

이 가이드를 따라 단계적으로 통합을 진행하시면 기존 시스템에 CIST 기능을 성공적으로 추가할 수 있습니다.