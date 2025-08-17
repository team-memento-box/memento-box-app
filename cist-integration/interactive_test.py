#!/usr/bin/env python3
"""
CIST 대화형 테스트 - 실시간 사용자 입력
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# 현재 스크립트 디렉토리의 .env 파일 로드
current_dir = Path(__file__).parent
load_dotenv(current_dir / ".env")

# 환경변수에서 API 키 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def interactive_conversation():
    """실시간 대화형 CIST 테스트"""
    
    print("=" * 60)
    print("🧠 CIST 대화형 테스트")
    print("=" * 60)
    print("💡 'exit' 또는 'quit'을 입력하면 종료됩니다.")
    print("💡 API 키가 없으면 모킹된 응답이 사용됩니다.")
    print()
    
    try:
        from services.cist_service import CISTIntegrationService
        
        # API 키 여부에 따라 모델 설정
        if OPENAI_API_KEY:
            print("🔑 OpenAI API 키 감지됨 - 실제 LLM 사용")
            cist_service = CISTIntegrationService(
                openai_api_key=OPENAI_API_KEY,
                openai_model="gpt-4o-mini"  # 더 저렴한 모델 사용
            )
        else:
            print("⚠️  OpenAI API 키 없음 - 모킹 모드로 실행")
            # 모킹 모드에서는 더미 키로 초기화 (실제로는 모킹된 응답 사용)
            cist_service = CISTIntegrationService(
                openai_api_key="dummy-key",
                openai_model="gpt-4o-mini"
            )
        
        print("🚀 CIST 통합 서비스 초기화 완료")
        
    except Exception as e:
        print(f"❌ 서비스 초기화 실패: {e}")
        return
    
    # 대화 세션 시작
    conversation_id = "interactive-conversation"
    
    # 사진 분석 결과 (기본값)
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
    
    try:
        # 대화 시작
        start_result = await cist_service.start_conversation(
            conversation_id=conversation_id,
            user_id="interactive-user",
            photo_id="interactive-photo", 
            photo_analysis=photo_analysis
        )
        
        print(f"\n🎯 대화 시작!")
        print(f"🤖 어시스턴트: {start_result['message']}")
        
        # 대화 루프
        turn = 1
        while True:
            print(f"\n--- 턴 {turn} ---")
            
            # 사용자 입력
            user_input = input("👤 사용자: ").strip()
            
            # 종료 조건
            if user_input.lower() in ['exit', 'quit', '종료', '끝']:
                print("👋 대화를 종료합니다.")
                break
            
            if not user_input:
                print("💭 입력이 비어있습니다. 다시 입력해주세요.")
                continue
            
            try:
                # 사용자 입력 처리
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
                    
                turn += 1
                
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
        
        # 세션 정리
        success = cist_service.cleanup_conversation(conversation_id)
        print(f"\n🧹 세션 정리: {'성공' if success else '실패'}")
        
    except Exception as e:
        print(f"❌ 대화 실행 실패: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(interactive_conversation())
    except KeyboardInterrupt:
        print("\n\n👋 사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")