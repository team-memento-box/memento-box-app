# -*- coding: utf-8 -*-
"""
8. 캐싱폴백 테스트: gpt

목표 흐름:
[이전 히스토리: '염소', '강아지' 언급]
-> 사용자: "고양이를 길렀어"
-> (AI 예상질문 예: "염소, 고양이, 강아지를 좋아하는 순서대로 알려주세요")
-> 문맥 부적합 점수로 임계치 미달 → 질문을 캐싱하고 casual로 폴백(경량 gpt-3.5-turbo 호출)
-> 다음 턴: "아까 말한 염소, 고양이, 강아지를 좋아하는 순서대로 알려줄래?"
-> 캐시된 질문 발견 → 맥락 검증 → assessment 질문 출력
"""
import time
import os
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()
API_KEY = os.getenv("GPT_API_KEY")
client = OpenAI(api_key = API_KEY)

conversation_history = []  # 전역

# ---- 유틸: 시간 로깅 ----
def log_time(start, end, step_name):
    print(f"[{step_name}] 소요 시간: {end - start:.3f}초")

# ---- 1. 예상질문 생성 + 캐싱 시뮬 ----
def turn1(user_message, history):
    print("\n=== 턴1 시작 ===")
    start = time.time()

    # AI 예상질문 생성 (실제 API 호출)
    q_start = time.time()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "너는 문맥 기반 예상 질문을 생성하는 AI야."},
            {"role": "user", "content": f"이전 대화: {history}\n사용자: {user_message}\n\n맥락 기반 예상 질문 3개 생성해줘"}
        ]
    )
    candidate_questions = response.choices[0].message.content.split("\n")
    q_end = time.time()
    log_time(q_start, q_end, "예상질문 생성")

    # 문맥 부적합 필터링 (여기서는 임의로 탈락 처리)
    valid_questions = []
    rejected_questions = candidate_questions
    print("문맥 부적합으로 캐싱됨:", rejected_questions)

    # 캐싱 저장소
    cache = rejected_questions

    # 경량모델 호출 (사용자에게 임시 질문)
    l_start = time.time()
    light_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "너는 임시 질문을 던지는 경량모델이야."},
            {"role": "user", "content": f"{user_message} 에 맞는 간단한 질문 1개만 해줘"}
        ]
    )
    light_question = light_response.choices[0].message.content
    l_end = time.time()
    log_time(l_start, l_end, "경량모델 호출")

    end = time.time()
    log_time(start, end, "턴1 전체")

    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": light_question})
    return cache, light_question


# ---- 2. 캐싱된 질문 검증 후 출력 ----
def turn2(user_answer, cache):
    print("\n=== 턴2 시작 ===")
    start = time.time()

    # 캐싱된 질문 불러오기
    cached_question = cache[0] if cache else None
    print("캐싱된 질문 후보:", cached_question)

    # 검증 단계 (API 호출)
    v_start = time.time()
    validation = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "너는 질문-답변 맥락 검증기야."},
            {"role": "user", "content": f"질문: {cached_question}\n사용자 답변: {user_answer}\n\n맥락이 맞으면 '적합', 아니면 '부적합'이라고 답해"}
        ]
    )
    verdict = validation.choices[0].message.content
    v_end = time.time()
    log_time(v_start, v_end, "검증")

    if "적합" in verdict:
        print("검증 통과 ✅ 캐싱된 질문 출력:", cached_question)
    else:
        print("검증 실패 ❌ 캐싱된 질문 사용 안함")

    end = time.time()
    log_time(start, end, "턴2 전체")

    conversation_history.append({"role": "user", "content": user_answer})
    if "적합" in verdict:
        conversation_history.append({"role": "assistant", "content": cached_question})


# ---- 실행 시뮬레이션 ----
if __name__ == "__main__":
    history = "사용자가 염소, 강아지를 언급했음"
    user_msg1 = "고양이를 길렀어"
    cache, light_q = turn1(user_msg1, history)
    print("경량모델 질문:", light_q)

    user_msg2 = "고양이 귀엽지"
    turn2(user_msg2, cache)

    print("\n=== 전체 대화 히스토리 ===")
    for msg in conversation_history:
        print(f"{msg['role'].upper()}: {msg['content']}")