import os
import openai 
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GPT_API_KEY")


client = openai.OpenAI(api_key=API_KEY)

print("1. gpt-3.5-turbo 테스트:")
try:
    response1 = client.chat.completions.create(       
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello, this is a test"}]
    )
    print(f"✅ 성공: {response1.choices[0].message.content}")
except Exception as e:
    print(f"❌ 실패: {e}")

print("\n2. gpt-5-nano 테스트:")
try:
    response2 = client.chat.completions.create(       
        model="gpt-5-nano",
        messages=[{"role": "user", "content": "Hello, this is a test"}]
    )
    print(f"✅ 성공: {response2.choices[0].message.content}")
except Exception as e:
    print(f"❌ 실패: {e}")

#사용가능 모델 호출
#client = OpenAI(api_key=API_KEY)
#3models = client.models.list()
#for m in models.data:
#    print(m.id)