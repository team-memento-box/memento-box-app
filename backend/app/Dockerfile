# 개발용
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

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]



# 배포용
# FROM python:3.11
# WORKDIR /app
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# COPY ./app /app
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]