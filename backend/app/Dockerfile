# WebSocket + Celery 지원 개발용
FROM python:3.11-slim
WORKDIR /app

# 시스템 라이브러리 설치
RUN apt-get update && apt-get install -y \
    libssl-dev \
    libasound2 \
    libpulse-dev \
    libc6 \
    libgcc1 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 방식으로 변경
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 추가 의존성 설치 (Celery, Redis)
RUN pip install celery[redis]==5.3.6 redis==5.0.1

COPY . .

# FastAPI 서버 실행 (기본 명령)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]



# 배포용
# FROM python:3.11-slim
# WORKDIR /app
# RUN pip install poetry
# ENV POETRY_NO_INTERACTION=1 \
#     POETRY_VENV_IN_PROJECT=1 \
#     POETRY_CACHE_DIR=/tmp/poetry_cache
# COPY pyproject.toml poetry.lock ./
# RUN poetry install --only=main && rm -rf $POETRY_CACHE_DIR
# COPY ./app /app
# CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]