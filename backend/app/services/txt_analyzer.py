import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from txt_analyzer_functions import *
from openai import OpenAI
import os, json
from dotenv import load_dotenv

load_dotenv()

# 클라이언트 생성
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 단계 1: 문법 교정만 수행
def correct_sentence(raw_text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",  
        messages=[
            {
                "role": "system", 
                "content": "너는 한국어 문장을 교정하는 도우미야. 텍스트의 띄어쓰기와 구두점을 수정해줘. 이외 문법이나 텍스트 자체는 절대 변경하면 안돼."
            },
            {
                "role": "user", 
                "content": raw_text
            }
        ]
    )
    corrected_text = response.choices[0].message.content.strip()
    print("교정된 텍스트:", corrected_text)
    return corrected_text

# 단계 2: 교정된 텍스트로 모든 분석 함수 실행
def analyze_with_all_functions(corrected_text):
    analysis_results = []
    
    # analyze_type_token 함수 실행
    try:
        result = analyze_type_token([corrected_text])
        analysis_results.append({
            "function": "analyze_type_token",
            "result": result
        })
    except Exception as e:
        analysis_results.append({
            "function": "analyze_type_token",
            "error": str(e)
        })
    
    # analyze_demon 함수 실행
    try:
        result = analyze_demon([corrected_text])
        analysis_results.append({
            "function": "analyze_demon", 
            "result": result
        })
    except Exception as e:
        analysis_results.append({
            "function": "analyze_demon",
            "error": str(e)
        })
    
    return analysis_results

# 통합 함수: 교정 + 분석
def correct_sentence_and_analyze(raw_text):
    # 1단계: 문법 교정
    corrected_text = correct_sentence(raw_text)
    
    # 2단계: 함수 호출로 분석
    analysis_results = analyze_with_all_functions(corrected_text)
    
    return {
        "corrected_text": corrected_text,
        "analysis_results": analysis_results
    }


# 최종 점수 계산 함수
def calculate_categorical_score(analysis_results):
    """
    OpenAI를 사용하여 4가지 언어학적 지표를 종합한 점수 계산
    """
    # 분석 데이터 추출
    speech_data = calculate_speech_score(analysis_results)
    
    if "error" in speech_data:
        return speech_data
    
    # 발화 시간 ======> 실제 발화 시간(초)로 교체 필요
    speech_duration = 25.0
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """당신은 언어 병리학 전문가입니다. 주어진 발화 데이터를 4종의 언어 분석 지표로 분석해주세요.

## 4개 언어 분석 지표 계산 방식:

### 1. 어휘 다양성 (0-1 값으로 표현)
- 내용어 비율과 MATTR을 적절한 가중치로 결합
- **계산 공식**: (내용어 비율 × 0.4) + (MATTR × 0.6)
- 결과값을 0-1 범위로 정규화

### 2. 평균 발화 길이 
- MLU 값을 그대로 사용

### 3. 지시어 사용 비율
- 지시어 비율을 그대로 사용

### 4. 발화 속도
- 발화 속도를 그대로 사용


## 결과 형식:
각 지표의 원본 분석값을 가공하여 다음과 같이 반환:
- lexical_diversity: 0-1 범위의 값
- mlu: MLU 원본값
- demonstrative_ratio: 전체 단어 수 대비 지시어 사용 비율
- speech_rate: 초당 발화 단어 수

JSON 형식으로 4개 지표 값을 제공해주세요."""
            },
            {
                "role": "user", 
                "content": f"""다음 발화 분석 데이터를 4종의 언어 분석 지표로 점수 계산해주세요:

**언어 분석 데이터:**
- 내용어 비율: {speech_data['content_word_ratio']:.3f}
- 기능어 비율: {speech_data['function_word_ratio']:.3f}  
- MATTR (어휘 다양성): {speech_data['mattr']:.3f}
- MLU (평균 발화 길이): {speech_data['mlu']:.3f}
- 지시어 사용 횟수: {speech_data['demonstrative_count']}개
- 전체 단어 수: {speech_data['total_words_count']}개
- 지시어 비율: {(speech_data['demonstrative_count'] / speech_data['total_words_count']) if speech_data['total_words_count'] > 0 else 0:.4f}%
- 발화 속도: {speech_data["total_words_count"] / speech_duration if speech_duration > 0 else 0:.2f} 단어/초

**계산 요청:**
1. 어휘 다양성(lexical_diversity): (내용어 비율 × 0.4) + (MATTR × 0.6) → 0-1 값
2. 평균 발화 길이(mlu): MLU 값 그대로 사용
3. 지시어 사용 비율(demonstrative_ratio): 지시어 비율 값 그대로 사용
4. 발화 속도(speech_rate): 발화 속도 값 그대로 사용

JSON 형식으로 4개 지표 값을 제공해주세요."""
            }
        ],
        response_format={"type": "json_object"}
    )
    
    try:
        score_result = json.loads(response.choices[0].message.content)
        return {
            "raw_data": speech_data,
            "ai_scoring": score_result
        }
    except Exception as e:
        return {
            "raw_data": speech_data,
            "ai_scoring_error": str(e)
        }


# 통합 함수: 교정 + 분석 + 점수 계산
def complete_speech_analysis(raw_text):
    """
    전체 언어 분석 파이프라인: 교정 → 분석 → 점수 계산
    """
    # 1단계: 교정 및 분석
    analysis_result = correct_sentence_and_analyze(raw_text)
    
    # 2단계: 점수 계산
    score_result = calculate_categorical_score(analysis_result["analysis_results"])
    
    return {
        "corrected_text": analysis_result["corrected_text"],
        "analysis_results": analysis_result["analysis_results"], 
        "categorical_score": score_result
    }
