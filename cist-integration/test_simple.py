#!/usr/bin/env python3
"""
간단한 CIST 테스트 - 그래프 없이 기본 기능만 테스트
"""

import asyncio
from schemas.conversation_state import ConversationState, ConversationPhase
from schemas.evaluation import CISTEvaluation


def test_basic_components():
    """기본 컴포넌트들 테스트"""
    
    print("=" * 60)
    print("🧠 CIST 기본 컴포넌트 테스트")
    print("=" * 60)
    
    # 1. ConversationState 생성 테스트
    print("\n1. ConversationState 생성 테스트")
    try:
        cist_evaluation = CISTEvaluation(
            conversation_id="test-001",
            user_id="test-user-001"
        )
        
        conversation_state = ConversationState(
            conversation_id="test-001",
            user_id="test-user-001",
            cist_evaluation=cist_evaluation
        )
        
        print(f"✅ ConversationState 생성 성공")
        print(f"   - conversation_id: {conversation_state.conversation_id}")
        print(f"   - current_phase: {conversation_state.current_phase}")
        print(f"   - max_graph_executions: {conversation_state.max_graph_executions}")
        print(f"   - max_integration_attempts: {conversation_state.max_integration_attempts}")
        
    except Exception as e:
        print(f"❌ ConversationState 생성 실패: {e}")
        return
    
    # 2. CIST 문항 정보 테스트
    print("\n2. CIST 문항 정보 테스트")
    try:
        from models.cist_items import cist_registry, CognitiveDomain
        
        total_score = cist_registry.get_total_possible_score()
        print(f"✅ CIST 문항 정보 로드 성공")
        print(f"   - 총 가능 점수: {total_score}점")
        
        for domain in CognitiveDomain:
            items = cist_registry.get_items_by_domain(domain)
            domain_score = sum(item.max_score for item in items)
            print(f"   - {domain.value}: {domain_score}점 ({len(items)}개 문항)")
            
    except Exception as e:
        print(f"❌ CIST 문항 정보 로드 실패: {e}")
        return
    
    # 3. 개별 평가기 테스트  
    print("\n3. 개별 평가기 테스트")
    try:
        from evaluators.scoring import CISTScorer
        
        # OpenAI API 키 없이 사용
        scorer = CISTScorer()
        
        # 테스트 케이스
        test_cases = [
            {
                "item_id": "memory_registration",
                "user_response": "빨간 장미가 정원에서 아름답게 피었습니다",
                "context": {"target_sentence": "빨간 장미가 정원에서 아름답게 피었습니다"}
            },
            {
                "item_id": "attention_forward", 
                "user_response": "5-8-2",
                "context": {"target_digits": "5-8-2"}
            }
        ]
        
        for case in test_cases:
            result = scorer.evaluate_response(
                item_id=case["item_id"],
                user_response=case["user_response"],
                context=case["context"]
            )
            
            print(f"   ✅ {case['item_id']}: {result.raw_score}/{result.max_score}점")
            
    except Exception as e:
        print(f"❌ 개별 평가기 테스트 실패: {e}")
        return
    
    print("\n🎉 모든 기본 컴포넌트 테스트 통과!")
    print("📝 원래 오류는 LangGraph의 재귀 문제였습니다.")
    print("🔧 해결 방법: recursion_limit 설정 및 무한 루프 방지 로직 추가")


if __name__ == "__main__":
    test_basic_components()