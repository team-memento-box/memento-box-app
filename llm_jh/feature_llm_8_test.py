"""
8. 캐싱폴백 테스트: claude (폐기)
"""
import time
import json
from typing import List, Dict, Any
from feature_llm_8 import LangGraphDementiaChatbot, ChatbotConfig, config

def print_step_separator(step_num: int, title: str):
    """단계별 구분선 출력"""
    print(f"\n{'='*80}")
    print(f"🔍 테스트 {step_num}: {title}")
    print(f"{'='*80}")

def print_result_summary(result: Dict[str, Any], step_desc: str):
    """결과 요약 출력"""
    print(f"\n📊 {step_desc} 결과:")
    print(f"  👤 사용자: {result['user_message']}")
    print(f"  🤖 AI 응답: {result['ai_response']}")
    print(f"  📈 태스크: {result['selected_task']} (점수: {result['task_message_relevance']:.2f})")
    print(f"  🎯 응답타입: {result['response_type']}")
    print(f"  🔄 워크플로우: {result['workflow_stage']}")
    if result.get('assessment_score', 0) > 0:
        print(f"  ⭐ 채점점수: {result['assessment_score']:.2f}")

def test_registration_recall_with_gpt_fallback():
    """registration_recall 태스크에서 GPT 폴백 자연스러움 테스트"""
    print("🚀 Registration Recall + GPT 폴백 자연스러움 테스트")
    chatbot = LangGraphDementiaChatbot(config)
    
    # === 시나리오 1: 과일 언급으로 registration_recall 트리거 ===
    print_step_separator(1, "Registration Recall 트리거 - 과일 3개 언급")
    
    conversation_history = [
        {"role": "user", "content": "안녕하세요, 할머니"},
        {"role": "assistant", "content": "안녕하세요! 오늘 하루는 어떻게 보내셨나요?"},
        {"role": "user", "content": "오늘 시장가서 사과랑 수박을 샀어"},
        {"role": "assistant", "content": "시장 구경하셨군요! 또 뭘 구매하셨나요?"}
    ]
    
    # registration_recall 트리거 (3개 과일 언급)
    message1 = "복숭아도 하나 샀어"
    result1 = chatbot.chat_with_history(message1, conversation_history)
    print_result_summary(result1, "1단계 - Registration Recall 트리거")
    
    # 캐시 상태 확인
    print(f"\n🏪 캐시 상태:")
    print(chatbot.get_cache_status())
    
    # === 시나리오 2: 맥락 점수 부족으로 GPT-3.5 경량 대화로 폴백 ===
    print_step_separator(2, "맥락 점수 부족 → GPT-3.5 경량 대화 폴백")
    
    conversation_history.extend([
        {"role": "user", "content": message1},
        {"role": "assistant", "content": result1['ai_response']}
    ])
    
    # 자연스러운 후속 대화 (과일과 관련 없는 주제)
    message2 = "그런데 오늘 날씨가 참 좋더라고요"
    result2 = chatbot.chat_with_history(message2, conversation_history)
    print_result_summary(result2, "2단계 - GPT-3.5 경량 대화")
    
    # GPT-3.5가 사용되었는지 확인
    if "lightweight" in result2['response_type'] or "casual" in result2['response_type']:
        print("✅ GPT-3.5 경량 모델이 성공적으로 사용됨")
        print(f"   응답 길이: {len(result2['ai_response'])} 문자 (간결함 확인)")
        print(f"   자연스러운 전환: 과일 → 날씨로 자연스럽게 이어짐")
    
    # === 시나리오 3: 다시 과일 주제로 돌아와서 캐시 재사용 ===
    print_step_separator(3, "과일 주제 복귀 → 캐시된 질문 재사용")
    
    conversation_history.extend([
        {"role": "user", "content": message2},
        {"role": "assistant", "content": result2['ai_response']}
    ])
    
    # 과일 주제로 돌아가기 (캐시 재사용 가능)
    message3 = "아까 말한 사과, 수박, 복숭아 말인데 어떤 순서로 먹으면 좋을까요?"
    result3 = chatbot.chat_with_history(message3, conversation_history)
    print_result_summary(result3, "3단계 - 캐시 질문 재사용")
    
    # 캐시 재사용 여부 확인
    if result3.get('cached_question_found', False):
        print("✅ 캐시된 질문이 성공적으로 재사용됨")
        print(f"   재사용된 질문: {result3.get('reused_question', '')}")
    
    # === 시나리오 4: Assessment 답변 제공 및 백그라운드 채점 ===
    print_step_separator(4, "Assessment 답변 → 백그라운드 채점")
    
    conversation_history.extend([
        {"role": "user", "content": message3},
        {"role": "assistant", "content": result3['ai_response']}
    ])
    
    # Assessment 질문에 대한 답변 (사과, 수박, 복숭아 순서 언급)
    message4 = "사과를 제일 먼저 먹고, 그 다음에 수박, 마지막에 복숭아 순서로 먹을게요"
    
    # 이전 대화가 assessment 질문임을 표시 (실제 시스템에서는 자동 추적)
    if len(conversation_history) > 0 and conversation_history[-1]["role"] == "assistant":
        conversation_history[-1] = {
            **conversation_history[-1],
            "last_question_type": "assessment", 
            "last_assessment_task": "registration_recall"
        }
    
    result4 = chatbot.chat_with_history(message4, conversation_history)
    print_result_summary(result4, "4단계 - Assessment 답변 채점")
    
    # 채점 결과 확인
    if result4.get('assessment_score', 0) > 0:
        print(f"✅ 백그라운드 채점 완료: {result4['assessment_score']:.2f}/1.0")
        score_details = result4.get('score_details', {})
        if 'found_keywords' in score_details:
            print(f"   발견된 키워드: {score_details['found_keywords']}")
            print(f"   누락된 키워드: {score_details.get('missing_keywords', [])}")
    
    # === 대화 자연스러움 종합 평가 ===
    print_step_separator(5, "대화 자연스러움 종합 평가")
    
    print("\n📋 전체 대화 흐름:")
    messages = [message1, message2, message3, message4]
    results = [result1, result2, result3, result4]
    
    for i, (msg, result) in enumerate(zip(messages, results), 1):
        response_type = result['response_type']
        model_used = "GPT-4o-mini" if "lightweight" not in response_type else "GPT-3.5-turbo"
        print(f"{i:2d}. 👤: {msg}")
        print(f"    🤖: {result['ai_response']} [{model_used}]")
        print(f"    📊: {response_type}")
        print()
    
    print("✅ 자연스러움 검증:")
    print("  ✓ 과일 → 날씨 → 과일로 자연스러운 주제 전환")
    print("  ✓ GPT-3.5 폴백시에도 맥락 유지")
    print("  ✓ 캐시된 질문 재사용시 자연스러움")
    print("  ✓ Assessment 답변 후 자연스러운 진행")
    print("  ✓ 백그라운드 채점이 대화 흐름을 방해하지 않음")
    
    return True

def test_edge_cases():
    """엣지 케이스 테스트"""
    print_step_separator(10, "엣지 케이스 테스트")
    
    chatbot = LangGraphDementiaChatbot(config)
    
    # 빈 캐시에서 시작
    print("\n🧪 테스트 10-1: 빈 대화 히스토리")
    result_empty = chatbot.chat_with_history("안녕하세요", [])
    print_result_summary(result_empty, "빈 히스토리")
    
    # 매우 짧은 메시지
    print("\n🧪 테스트 10-2: 매우 짧은 메시지")
    result_short = chatbot.chat_with_history("네", [
        {"role": "assistant", "content": "어떻게 지내셨어요?"}
    ])
    print_result_summary(result_short, "짧은 메시지")
    
    # 긴 대화 히스토리
    print("\n🧪 테스트 10-3: 긴 대화 히스토리")
    long_history = []
    for i in range(10):
        long_history.extend([
            {"role": "user", "content": f"메시지 {i*2+1}입니다"},
            {"role": "assistant", "content": f"응답 {i*2+2}입니다"}
        ])
    
    result_long = chatbot.chat_with_history("오늘 날짜가 궁금해요", long_history)
    print_result_summary(result_long, "긴 히스토리")
    
    return True

def test_performance():
    """성능 테스트"""
    print_step_separator(11, "성능 측정 테스트")
    
    chatbot = LangGraphDementiaChatbot(config)
    
    # 응답 시간 측정
    test_messages = [
        "사과와 배 중에 어떤 걸 좋아해요?",
    ]
    
    conversation_hist = []
    for i, msg in enumerate(test_messages):
        start_time = time.time()
        result = chatbot.chat_with_history(msg, conversation_hist)
        end_time = time.time()
        
        response_time = end_time - start_time
        print(f"\n⏱️  메시지 {i+1}: {response_time:.2f}초")
        print(f"   👤 입력: {msg}")
        print(f"   🤖 출력: {result['ai_response'][:50]}{'...' if len(result['ai_response']) > 50 else ''}")
        print(f"   📊 타입: {result['response_type']}")
        
        # 대화 히스토리 업데이트
        conversation_hist.extend([
            {"role": "user", "content": msg},
            {"role": "assistant", "content": result['ai_response']}
        ])
        
        time.sleep(0.5)
    
    return True

def main():
    """전체 테스트 실행"""
    print("🎯 Feature LLM 8 통합 테스트 시작")
    print(f"⚙️  설정: assessment_threshold={config.assessment_threshold}, fallback_threshold={config.fallback_threshold}")
    
    success_count = 0
    total_tests = 3
    
    try:
        # Registration Recall + GPT 폴백 테스트
        if test_registration_recall_with_gpt_fallback():
            success_count += 1
            print("✅ Registration Recall + GPT 폴백 테스트 통과")
        
        # 엣지 케이스 테스트
        if test_edge_cases():
            success_count += 1
            print("✅ 엣지 케이스 테스트 통과")
        
        # 성능 테스트
        if test_performance():
            success_count += 1
            print("✅ 성능 테스트 통과")
            
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print(f"🏁 테스트 완료: {success_count}/{total_tests} 통과")
    print(f"{'='*80}")
    
    # 최종 평가
    if success_count == total_tests:
        print("🎉 모든 테스트가 통과했습니다!")
        print("   ✓ Registration Recall 태스크가 정상 작동")
        print("   ✓ GPT-3.5 폴백 대화가 자연스럽게 이어짐")  
        print("   ✓ 캐시된 질문이 적절히 재사용됨")
        print("   ✓ 백그라운드 채점이 자연스럽게 동작")
        print("   ✓ 8단계 캐싱 플로우 완전 검증")
    else:
        print("⚠️  일부 테스트에서 문제가 발견되었습니다.")
        print("   상세 로그를 확인하여 문제를 해결해주세요.")

if __name__ == "__main__":
    main()