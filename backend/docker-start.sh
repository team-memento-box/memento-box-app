#!/bin/bash
# Docker Compose로 전체 시스템 시작

echo "🚀 Memento Box Backend Services 시작..."

# .env 파일 존재 확인
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다. .env.example을 참조하여 생성하세요."
    exit 1
fi

# Docker Compose로 모든 서비스 시작
echo "📦 컨테이너들을 시작하는 중..."
docker-compose up --build -d

echo "✅ 서비스들이 시작되었습니다!"
echo ""
echo "🌐 서비스 접근 정보:"
echo "  - FastAPI (WebSocket): http://localhost:8000"
echo "  - FastAPI Docs: http://localhost:8000/docs"  
echo "  - Nginx Proxy: http://localhost:80"
echo "  - RabbitMQ Management: http://localhost:15672 (admin/password)"
echo "  - Redis: localhost:6379"
echo ""
echo "📊 서비스 상태 확인:"
docker-compose ps
echo ""
echo "🔍 로그 보기: docker-compose logs -f [service_name]"
echo "🛑 서비스 종료: docker-compose down"