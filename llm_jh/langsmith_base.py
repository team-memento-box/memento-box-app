import os
from dotenv import load_dotenv
from langchain_teddynote import logging


load_dotenv()

LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT")

# 1. 추적 시작
logging.langsmith("memento")

# 2. 추적 해제
from langchain_teddynote import logging
# set_enable=False 로 지정하면 추적을 하지 않습니다.
logging.langsmith("랭체인 튜토리얼 프로젝트", set_enable=False)