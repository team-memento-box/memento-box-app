from konlpy.tag import Okt, Kkma
import re, requests

# function schema 정의
functions = [
    {
        "name": "analyze_type_token",
        "description": "한국어 발화 텍스트 분석 (MLU, MATTR, 기능어-내용어 비율 등)",
        "parameters": {
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "분석할 한국어 문장 리스트"
                }
            },
            "required": ["texts"]
        }
    },
    {
        "name": "analyze_demon",
        "description": "한국어 발화 텍스트 분석 (지시어 사용 개수)",
        "parameters": {
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "분석할 한국어 문장 리스트"
                }
            },
            "required": ["texts"]
        }
    }
]


# 내용어-기능어 비율/MATTR/MLU 분석 함수
def analyze_type_token(texts):
    
    # texts가 리스트가 아니면 리스트로 변환
    if isinstance(texts, str):
        texts = [texts]
    
    refine_text = ' '.join(texts)

    # 각 분석기 객체 생성
    okt = Okt()
    kkma = Kkma()

    kkma_sentences = kkma.sentences(refine_text)
    # print("문장 분석 결과: ", kkma_sentences, '\n')
    print("문장 개수:", len(kkma_sentences), '\n')

    total_words = []
    content_words_cnt = 0
    function_words_cnt = 0

    for sentence in kkma_sentences:
        morphs = okt.pos(sentence, norm=True)

        # 구두점 제거
        clean_sentence = re.sub(r'[^\w\s가-힣]', '', sentence)
        words = okt.morphs(clean_sentence, norm=True)
        total_words.extend(words)

        # 내용어와 기능어 구분
        content_tags = ['Noun', 'Verb', 'Adjective', 'Adverb']
        function_tags = ['Josa', 'Eomi', 'Conjunction', 'Interjection', 'Determiner', 'Exclamation', 'PreEomi']

        content_words = [w for w, t in morphs if t in content_tags]
        function_words = [w for w, t in morphs if t in function_tags]

        # print("형태소 분석 결과:", morphs, '\n')
        # print("실질 단어(내용어) 리스트:", content_words, '\n')
        # print("기능어 리스트:", function_words, '\n')
        # print("***************************************************\n")

        content_words_cnt += len(content_words)
        function_words_cnt += len(function_words)

    total_words_cnt = len(total_words)
        
    def mattr(words, window_size):
        """
        words: 단어 리스트 (형태소 분석 후 content word 등)
        window_size: 슬라이딩 윈도우 크기
        """
        if len(words) < window_size:
            # 단어 수가 window_size보다 작으면 그냥 전체 TTR 계산
            return len(set(words)) / len(words) if words else 0

        ttr_list = []
        for i in range(len(words) - window_size + 1):
            window = words[i:i+window_size]
            ttr = len(set(window)) / len(window)
            ttr_list.append(ttr)

        return sum(ttr_list) / len(ttr_list)
    

    total_words_cnt = content_words_cnt + function_words_cnt
    content_ratio = content_words_cnt / total_words_cnt if total_words_cnt > 0 else 0
    function_ratio = function_words_cnt / total_words_cnt if total_words_cnt > 0 else 0
    mattr_value = mattr(total_words, window_size=20)
    mlu = content_words_cnt / len(kkma_sentences) if len(kkma_sentences) > 0 else 0

    # print("전체 단어 리스트:", total_words, "\n")

    print("전체 단어 개수:", total_words_cnt)
    print("내용어 개수:", content_words_cnt)
    print("기능어 개수:", function_words_cnt, "\n")

    print("내용어 비율:", round(content_ratio, 2))
    print("기능어 비율:", round(function_ratio, 2), "\n")

    print("MATTR:", round(mattr_value, 3), "\n")

    print("평균 발화 길이:", content_words_cnt / len(kkma_sentences))

    return {
        "total_words_cnt": total_words_cnt,
        "content_ratio": round(content_ratio, 2),
        "function_ratio": round(function_ratio, 2),
        "MATTR": round(mattr_value, 3),
        "MLU": round(mlu, 2)
    }



# 지시어 사용 개수 분석 함수
def analyze_demon(texts):
    
    # texts가 리스트가 아니면 리스트로 변환
    if isinstance(texts, str):
        texts = [texts]
    
    refine_text = ' '.join(texts)

    # 형태소 분석을 위한 ETRI API 호출
    def call_etri_api(refine_text):

        # 언어 분석 기술(구어)
        api_url = "http://epretx.etri.re.kr:8000/api/WiseNLU_spoken"

        access_key = "7addb5e9-7ac3-4997-83ae-8da6f31b4106"

        """
        요청할 분석 코드로서 요청할 수 있는 분석 요청은 아래와 같음
        형태소 분석 (문어/구어) : "morp",
        어휘의미 분석 (동음이의어 분석)(문어) : "wsd"
        어휘의미 분석 (다의어 분석)(문어) : "wsd_poly"
        개체명 인식 (문어/구어) : "ner"
        의존 구문 분석 (문어) : "dparse"
        의미역 인식 (문어) : "srl"
        """

        analysis_code = "morp"
        headers = {"Content-Type": "application/json; charset=UTF-8",
                "Authorization" :  access_key}

        request_json = {
            "accessKey": access_key,
            "argument": {
                "text": refine_text,
                "analysis_code": analysis_code
            }
        }

        response = requests.post(
            api_url,
            json=request_json,
            headers=headers,
        )

        if response.status_code != 200:
            print("HTTP 오류:", response.status_code)
        else:
            response_json = response.json()  # JSON으로 파싱
            result = response_json['return_object']['sentence']
            # print(json.dumps(result, ensure_ascii=False, indent=2))
            print("Call Completed")

        return result
    
    words = call_etri_api(refine_text)

    demonstratives = {"그거", "저거", "이거", "여기", "거기", "저기", "이렇게", "그렇게", "저렇게", "이것", "저것", "그것", "거시기", "뭐", "무엇"}
    found = False
    count = 0

    for word in words:
        for morph in word.get("morp", []):
            if morph.get("type") == "NP" and morph.get("lemma") in demonstratives:
                found = True
                print(morph.get("lemma"))
                count += 1
        if found:
            break
    
    print("지시어 사용 횟수:", count)
    
    return {
        "demonstrative_count": count
    }


# 발화 점수 계산을 위한 OpenAI 함수
def calculate_speech_score(analysis_results):
    """
    4가지 언어 분석 지표를 통합하여 발화 점수를 계산
    """
    # 분석 결과에서 필요한 값들 추출
    type_token_result = None
    demon_result = None
    
    for result in analysis_results:
        if result["function"] == "analyze_type_token":
            type_token_result = result["result"]
        elif result["function"] == "analyze_demon":
            demon_result = result["result"]
    
    if not type_token_result or not demon_result:
        return {"error": "필요한 분석 결과가 없습니다"}
    
    # 분석 데이터 구성
    analysis_data = {
        "content_word_ratio": type_token_result.get("content_ratio", 0),
        "function_word_ratio": type_token_result.get("function_ratio", 0),
        "mattr": type_token_result.get("MATTR", 0),
        "mlu": type_token_result.get("MLU", 0),
        "demonstrative_count": demon_result.get("demonstrative_count", 0),
        "total_words_count": type_token_result.get("total_words_cnt", 0)
    }
    
    return analysis_data

# 발화 점수 계산 함수 스키마
speech_score_function = {
    "name": "calculate_final_speech_score",
    "description": "4가지 언어 분석 지표(어휘 다양성, 평균 발화 길이, 지시어 사용, 발화 속도)를 종합하여 0-100점 발화 점수를 계산",
    "parameters": {
        "type": "object", 
        "properties": {
            "content_ratio": {
                "type": "number",
                "description": "내용어 비율 (0.0-1.0)"
            },
            "function_ratio": {
                "type": "number", 
                "description": "기능어 비율 (0.0-1.0)"
            },
            "mattr": {
                "type": "number",
                "description": "어휘 다양성 지수 MATTR"
            },
            "mlu": {
                "type": "number",
                "description": "평균 발화 길이 MLU"
            },
            "demonstrative_count": {
                "type": "integer",
                "description": "지시어 사용 횟수"
            },
            "total_words": {
                "type": "integer", 
                "description": "전체 단어 수"
            }
        },
        "required": ["content_ratio", "function_ratio", "mattr", "mlu", "demonstrative_count", "total_words"]
    }
}