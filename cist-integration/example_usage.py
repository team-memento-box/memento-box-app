"""
CIST 통합 시스템 사용 예시
"""

import asyncio
import os
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# 현재 스크립트 디렉토리의 .env 파일 로드
current_dir = Path(__file__).parent
load_dotenv(current_dir / ".env")

# 환경변수에서 API 키 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def example_conversation_flow():
    """CIST 통합 대화 예시"""
    
    # 서비스 초기화 (실제로는 의존성 주입이나 싱글톤 패턴 사용)
    try:
        from services.cist_service import CISTIntegrationService
        
        cist_service = CISTIntegrationService(
            openai_api_key=OPENAI_API_KEY,
            openai_model="gpt-4.1-nano"
        )
        
        print("🚀 CIST 통합 서비스 초기화 완료")
        
    except Exception as e:
        print(f"❌ 서비스 초기화 실패: {e}")
        print("💡 OPENAI_API_KEY 환경변수를 설정해주세요.")
        return
    
    # 대화 세션 시작
    conversation_id = "example-conversation-001"
    
    # 사진 분석 결과 (실제로는 기존 image_analyzer에서 가져옴)
    photo_analysis = {
        "caption": "가족이 함께 식사하는 따뜻한 모습",
        "mood": "따뜻함, 행복감",
        "objects": ["사람", "테이블", "음식", "그릇"],
        "people_count": 3,
        "time_period": "1980년대",
        "time_of_day": "저녁"
    }
    
    print("\n📸 사진 분석 결과:")
    for key, value in photo_analysis.items():
        print(f"  {key}: {value}")
    
    # 대화 시작
    print(f"\n🎯 대화 시작 (ID: {conversation_id})")
    
    try:
        start_result = await cist_service.start_conversation(
            conversation_id=conversation_id,
            user_id="test-user-001",
            photo_id="test-photo-001", 
            photo_analysis=photo_analysis
        )
        
        print(f"✅ 대화 시작 성공")
        print(f"💬 첫 메시지: {start_result['message']}")
        
    except Exception as e:
        print(f"❌ 대화 시작 실패: {e}")
        return
    
    # 시뮬레이션된 사용자 응답들
    user_responses = [
        "이 사진을 보니 옛날 생각이 나네요. 가족들과 함께 밥 먹던 시절이 그립습니다.",
        "2024년이죠. 12월이고, 오늘이 화요일인 것 같아요.",  # 지남력 평가
        "저는 지금 집에 있어요.",  # 장소 지남력
        "빨간 장미가 정원에서 아름답게 피었습니다.",  # 기억 등록
        "5-8-2",  # 주의력 (숫자 따라하기)
        "사과, 배, 바나나, 포도, 딸기, 복숭아, 수박, 참외, 오렌지, 자두, 키위",  # 집행기능 (언어 유창성)
        "장미가 정원에서 피었다고 말씀하셨어요.",  # 기억 회상
        "안녕하세요",  # 언어 이해력
        "이제 그만 대화를 마치고 싶어요."  # 종료
    ]
    
    print(f"\n🗣️ 시뮬레이션된 대화 진행:")
    
    for i, user_input in enumerate(user_responses, 1):
        print(f"\n--- 턴 {i} ---")
        print(f"👤 사용자: {user_input}")
        
        try:
            result = await cist_service.process_user_input(
                conversation_id=conversation_id,
                user_input=user_input
            )
            
            print(f"🤖 어시스턴트: {result['message']}")
            print(f"📊 현재 점수: {result['current_score']}")
            print(f"📈 완료된 항목: {result['completed_items']}/{result['total_items']}")
            
            if result.get('current_cist_item'):
                item_info = result['current_cist_item']
                print(f"🧠 CIST 평가 중: {item_info['item_name']} ({item_info['domain']})")
            
            if result['is_completed']:
                print("🎉 대화 완료!")
                break
                
        except Exception as e:
            print(f"❌ 대화 처리 실패: {e}")
            break
    
    # 평가 요약 조회
    print(f"\n📋 최종 평가 요약:")
    
    try:
        summary = await cist_service.get_evaluation_summary(conversation_id)
        
        print(f"  총점: {summary['total_score']}/{summary['max_score']} ({summary['percentage']:.1f}%)")
        print(f"  위험도: {summary['risk_level']}")
        print(f"  영역별 점수:")
        
        for domain, score in summary['domain_scores'].items():
            print(f"    {domain}: {score}점")
        
        print(f"  권고사항:")
        for rec in summary['recommendations']:
            print(f"    - {rec}")
            
    except Exception as e:
        print(f"❌ 평가 요약 조회 실패: {e}")
    
    # 상세 보고서 조회  
    print(f"\n📄 상세 평가 보고서:")
    
    try:
        detailed_report = await cist_service.get_detailed_report(conversation_id)
        print(detailed_report[:500] + "..." if len(detailed_report) > 500 else detailed_report)
        
    except Exception as e:
        print(f"❌ 상세 보고서 조회 실패: {e}")
    
    # 세션 정리
    success = cist_service.cleanup_conversation(conversation_id)
    print(f"\n🧹 세션 정리: {'성공' if success else '실패'}")


async def test_individual_cist_items():
    """개별 CIST 문항 테스트"""
    
    print("\n🧪 개별 CIST 문항 테스트")
    
    try:
        from models.cist_items import cist_registry
        from evaluators.scoring import CISTScorer
        from langchain_openai import ChatOpenAI
        
        # 스코어러 초기화 
        scorer = CISTScorer(api_key=OPENAI_API_KEY, model="gpt-4.1-nano") if OPENAI_API_KEY else CISTScorer()
        
        # 테스트 케이스들
        test_cases = [
            {
                "item_id": "orientation_time",
                "user_response": "2024년 12월 17일 화요일이에요",
                "context": {}
            },
            {
                "item_id": "memory_registration", 
                "user_response": "빨간 장미가 정원에서 아름답게 피었습니다",
                "context": {"target_sentence": "빨간 장미가 정원에서 아름답게 피었습니다"}
            },
            {
                "item_id": "attention_forward",
                "user_response": "5-8-2",
                "context": {"target_digits": "5-8-2"}
            },
            {
                "item_id": "executive_verbal_fluency",
                "user_response": "사과 배 바나나 포도 딸기 복숭아 수박 참외 오렌지 자두",
                "context": {}
            }
        ]
        
        for test_case in test_cases:
            print(f"\n🔍 테스트: {test_case['item_id']}")
            print(f"  입력: {test_case['user_response']}")
            
            try:
                result = scorer.evaluate_response(
                    item_id=test_case['item_id'],
                    user_response=test_case['user_response'],
                    context=test_case['context']
                )
                
                print(f"  점수: {result.raw_score}/{result.max_score}")
                print(f"  상태: {result.status}")
                if result.evaluation_details:
                    print(f"  세부사항: {result.evaluation_details}")
                    
            except Exception as e:
                print(f"  ❌ 평가 실패: {e}")
                
    except ImportError as e:
        print(f"❌ 모듈 import 실패: {e}")
        print("💡 필요한 라이브러리가 설치되지 않았을 수 있습니다.")


def show_cist_items_info():
    """CIST 문항 정보 출력"""
    
    print("\n📚 CIST 문항 정보")
    
    try:
        from models.cist_items import cist_registry, CognitiveDomain
        
        print(f"총 평가 가능 점수: {cist_registry.get_total_possible_score()}점")
        
        for domain in CognitiveDomain:
            items = cist_registry.get_items_by_domain(domain)
            domain_score = sum(item.max_score for item in items)
            
            print(f"\n🧠 {domain.value} 영역 ({domain_score}점):")
            
            for item in items:
                print(f"  📝 {item.name} ({item.max_score}점)")
                print(f"     {item.description}")
                print(f"     전략: {item.natural_integration_strategy}")
                if item.example_questions:
                    print(f"     예시: {item.example_questions[0]}")
                    
    except ImportError as e:
        print(f"❌ 모듈 import 실패: {e}")


async def main():
    """메인 실행 함수"""
    
    print("=" * 60)
    print("🧠 CIST 통합 시스템 데모")
    print("=" * 60)
    
    # CIST 문항 정보 출력
    show_cist_items_info()
    
    # 개별 문항 테스트 (LLM 없이 가능)
    await test_individual_cist_items()
    
    # 전체 대화 흐름 테스트 (LLM API 키 필요)
    if OPENAI_API_KEY:
        await example_conversation_flow()
    else:
        print("\n⚠️  전체 대화 테스트를 위해서는 OPENAI_API_KEY가 필요합니다.")
        print("   .env 파일에 OPENAI_API_KEY=your-actual-api-key 추가하거나")
        print("   export OPENAI_API_KEY='your-actual-api-key' 설정하세요")


if __name__ == "__main__":
    asyncio.run(main())