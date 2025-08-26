"""
gpt-5-nano 단독 테스트
"""
import os
import openai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GPT_API_KEY")

client = openai.OpenAI(api_key=API_KEY)

# 다양한 설정으로 테스트
test_configs = [
    {"max_completion_tokens": 50},
    {"max_completion_tokens": 100}, 
    {"max_completion_tokens": 200},
    {"max_completion_tokens": 500},
    {"max_completion_tokens": 1000},
    {},  # 매개변수 없음
]

simple_message = [{"role": "user", "content": "안녕하세요"}]

for i, config in enumerate(test_configs, 1):
    print(f"\n=== 테스트 {i}: {config} ===")
    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=simple_message,
            **config
        )
        
        content = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason
        
        print(f"응답: '{content}'")
        print(f"종료 사유: {finish_reason}")
        print(f"응답 길이: {len(content) if content else 0}")
        
    except Exception as e:
        print(f"오류: {e}")