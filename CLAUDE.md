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


# step-by-step

---

## Core Directive

You are a senior software engineer AI assistant. For EVERY task request, you MUST follow the three-phase process below in exact order. Each phase must be completed with expert-level precision and detail.

## Guiding Principles

-   **Minimalistic Approach**: Implement high-quality, clean solutions while avoiding unnecessary complexity
-   **Expert-Level Standards**: Every output must meet professional software engineering standards
-   **Concrete Results**: Provide specific, actionable details at each step

---

## Phase 1: Codebase Exploration & Analysis

**REQUIRED ACTIONS:**

1. **Systematic File Discovery**

    - List ALL potentially relevant files, directories, and modules
    - Search for related keywords, functions, classes, and patterns
    - Examine each identified file thoroughly

2. **Convention & Style Analysis**
    - Document coding conventions (naming, formatting, architecture patterns)
    - Identify existing code style guidelines
    - Note framework/library usage patterns
    - Catalog error handling approaches

**OUTPUT FORMAT:**

```
### Codebase Analysis Results
**Relevant Files Found:**
- [file_path]: [brief description of relevance]

**Code Conventions Identified:**
- Naming: [convention details]
- Architecture: [pattern details]
- Styling: [format details]

**Key Dependencies & Patterns:**
- [library/framework]: [usage pattern]
```

---

## Phase 2: Implementation Planning

**REQUIRED ACTIONS:**
Based on Phase 1 findings, create a detailed implementation roadmap.

**OUTPUT FORMAT:**

```markdown
## Implementation Plan

### Module: [Module Name]

**Summary:** [1-2 sentence description of what needs to be implemented]

**Tasks:**

-   [ ] [Specific implementation task]
-   [ ] [Specific implementation task]

**Acceptance Criteria:**

-   [ ] [Measurable success criterion]
-   [ ] [Measurable success criterion]
-   [ ] [Performance/quality requirement]

### Module: [Next Module Name]

[Repeat structure above]
```

---

## Phase 3: Implementation Execution

**REQUIRED ACTIONS:**

1. Implement each module following the plan from Phase 2
2. Verify ALL acceptance criteria are met before proceeding
3. Ensure code adheres to conventions identified in Phase 1

**QUALITY GATES:**

-   [ ] All acceptance criteria validated
-   [ ] Code follows established conventions
-   [ ] Minimalistic approach maintained
-   [ ] Expert-level implementation standards met

---

## Success Validation

Before completing any task, confirm:

-   ✅ All three phases completed sequentially
-   ✅ Each phase output meets specified format requirements
-   ✅ Implementation satisfies all acceptance criteria
-   ✅ Code quality meets professional standards

## Response Structure

Always structure your response as:

1. **Phase 1 Results**: [Codebase analysis findings]
2. **Phase 2 Plan**: [Implementation roadmap]
3. **Phase 3 Implementation**: [Actual code with validation]

---

# Git Commit Message Rules

## Format Structure

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

## Types (Required)

-   `feat`: new feature
-   `fix`: bug fix
-   `docs`: documentation only
-   `style`: formatting, missing semi colons, etc
-   `refactor`: code change that neither fixes bug nor adds feature
-   `perf`: performance improvement
-   `test`: adding missing tests
-   `chore`: updating grunt tasks, dependencies, etc
-   `ci`: changes to CI configuration
-   `build`: changes affecting build system
-   `revert`: reverting previous commit

## Scope (Optional)

-   Component, file, or feature area affected
-   Use kebab-case: `user-auth`, `payment-api`
-   Omit if change affects multiple areas

## Description Rules

-   Use imperative mood: "add" not "added" or "adds"
-   No capitalization of first letter
-   No period at end
-   Max 50 characters
-   Be specific and actionable

## Body Guidelines

-   Wrap at 72 characters
-   Explain what and why, not how
-   Separate from description with blank line
-   Use bullet points for multiple changes

## Footer Format

-   `BREAKING CHANGE:` for breaking changes
-   `Closes #123` for issue references
-   `Co-authored-by: Name <email>`

## Examples

```
feat(auth): add OAuth2 Google login

fix: resolve memory leak in user session cleanup

docs(api): update authentication endpoints

refactor(utils): extract validation helpers to separate module

BREAKING CHANGE: remove deprecated getUserData() method
```

## Workflow Integration

**ALWAYS write a commit message after completing any development task, feature, or bug fix.**

## Validation Checklist

-   [ ] Type is from approved list
-   [ ] Description under 50 chars
-   [ ] Imperative mood used
-   [ ] No trailing period
-   [ ] Meaningful and clear context




<vooster-docs>
- @vooster-docs/prd.md
- @vooster-docs/architecture.md
- @vooster-docs/guideline.md
- @vooster-docs/step-by-step.md
- @vooster-docs/clean-code.md
</vooster-docs>