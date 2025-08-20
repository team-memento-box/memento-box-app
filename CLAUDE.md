# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a dual-platform application called "Memento Box" - a photo-sharing and conversation platform with AI capabilities:

### Frontend (Flutter App)
- **Location**: `Memento-Box/` directory
- **Language**: Dart/Flutter
- **Purpose**: Mobile application for iOS/Android with photo sharing, gallery, conversation features
- **Key Dependencies**: Provider for state management, Kakao SDK for authentication, HTTP client for backend communication

### Backend (FastAPI)
- **Location**: `fastapi-app/` directory  
- **Language**: Python
- **Purpose**: REST API server with AI chat, image analysis, voice synthesis, and conversation management
- **Key Dependencies**: FastAPI, OpenAI, PostgreSQL, aiohttp, pygame for audio

## Development Commands

### Flutter App Commands
```bash
cd Memento-Box/

# Install dependencies
flutter pub get

# Run the app (development)
flutter run

# Build for production
flutter build apk          # Android
flutter build ios          # iOS

# Run tests
flutter test

# Analyze code (linting)
flutter analyze

# Clean build artifacts
flutter clean
```

### FastAPI Backend Commands
```bash
cd fastapi-app/

# Install dependencies
pip install -r app/requirements.txt

# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run with Docker Compose (full stack)
docker-compose up --build

# Run individual service
docker-compose up web db
```

## Architecture

### Flutter App Structure
- **State Management**: Provider pattern (`user_provider.dart`)
- **Routing**: Custom route generation in `main.dart`
- **Screens**: Modular screen components in `screens/` directory
- **Authentication**: Kakao OAuth integration with environment variables from `.env`
- **Assets**: Images and photos stored in `assets/` directory

### FastAPI Backend Structure
- **Routers**: Modular API routes (`routers/auth.py`, `routers/chat.py`, etc.)
- **Services**: Business logic (`services/chat_system.py`, `services/image_analyzer.py`, etc.)
- **Core**: Configuration and authentication (`core/config.py`, `core/auth.py`)
- **Database**: PostgreSQL with async drivers (asyncpg)
- **AI Integration**: OpenAI API for chat and image analysis

### Infrastructure
- **Containerization**: Docker Compose setup with FastAPI, PostgreSQL, Nginx, and Fish-Speech TTS
- **Networking**: Internal Docker network (`memento_net`)
- **SSL**: Self-signed certificates for HTTPS
- **File Storage**: Volume mounts for uploads and model outputs

## Environment Configuration

Both applications require `.env` files:
- Flutter app expects `.env` in `Memento-Box/` for Kakao OAuth credentials
- FastAPI expects `.env` in `fastapi-app/` for database and API configurations

## Key Integration Points

- Flutter app communicates with FastAPI backend via HTTP requests
- Authentication flow uses Kakao OAuth with token-based session management
- Image uploads from mobile app are processed by backend AI services
- Real-time conversation features connect mobile UI with AI chat system