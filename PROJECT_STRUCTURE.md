# Kavalan Project Structure

This document describes the complete project structure for the Kavalan production-ready browser extension system.

## Overview

Kavalan is organized as a monorepo with two main packages:
- **Extension**: Browser extension (TypeScript + React)
- **Backend**: Microservices backend (Python + FastAPI)

## Directory Structure

```
kavalan/
├── packages/
│   ├── backend/                    # Backend services (Python)
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py            # FastAPI application entry point
│   │   │   ├── config.py          # Configuration management
│   │   │   ├── celery_app.py      # Celery task queue configuration
│   │   │   ├── db/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── postgres.py    # PostgreSQL connection manager
│   │   │   │   └── mongodb.py     # MongoDB connection manager
│   │   │   └── tasks/
│   │   │       ├── __init__.py
│   │   │       ├── audio_tasks.py # Audio transcription tasks
│   │   │       ├── visual_tasks.py# Visual analysis tasks
│   │   │       └── liveness_tasks.py # Liveness detection tasks
│   │   ├── db/
│   │   │   ├── init-postgres.sql  # PostgreSQL schema initialization
│   │   │   └── init-mongodb.js    # MongoDB schema initialization
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py        # Pytest fixtures
│   │   │   └── test_api.py        # API tests
│   │   ├── .dockerignore
│   │   ├── .env.example           # Environment variables template
│   │   ├── .gitignore
│   │   ├── Dockerfile             # Backend container image
│   │   ├── pyproject.toml         # Python project configuration
│   │   ├── requirements.txt       # Python dependencies
│   │   └── requirements-dev.txt   # Development dependencies
│   │
│   └── extension/                  # Browser extension (TypeScript)
│       ├── src/
│       │   └── manifest.json      # Extension manifest (Manifest V3)
│       ├── .eslintrc.cjs          # ESLint configuration
│       ├── .gitignore
│       ├── package.json           # Node.js dependencies
│       ├── tsconfig.json          # TypeScript configuration
│       ├── tsconfig.node.json     # TypeScript config for build tools
│       └── vite.config.ts         # Vite build configuration
│
├── .gitignore                      # Root gitignore
├── docker-compose.yml              # Multi-container orchestration
├── Makefile                        # Development commands
├── README.md                       # Project overview
├── SETUP_GUIDE.md                  # Detailed setup instructions
├── PROJECT_STRUCTURE.md            # This file
├── setup.sh                        # Automated setup script
└── verify-setup.sh                 # Setup verification script
```

## Package Details

### Backend Package (`packages/backend/`)

The backend is a Python-based microservices architecture using FastAPI and Celery.

#### Key Components:

1. **FastAPI Application** (`app/main.py`)
   - REST API endpoints
   - WebSocket support for real-time alerts
   - CORS middleware
   - Health check endpoints

2. **Configuration** (`app/config.py`)
   - Environment-based settings using Pydantic
   - Database URLs
   - API keys
   - JWT configuration

3. **Celery Task Queue** (`app/celery_app.py`)
   - Asynchronous task processing
   - Task routing to specialized queues
   - Retry logic with exponential backoff

4. **Database Managers** (`app/db/`)
   - PostgreSQL: Structured data (users, sessions, threat events)
   - MongoDB: Unstructured data (evidence, digital FIRs)

5. **Task Workers** (`app/tasks/`)
   - Audio transcription (Whisper)
   - Visual analysis (Gemini Vision)
   - Liveness detection (MediaPipe)

6. **Database Schemas** (`db/`)
   - PostgreSQL: Tables for users, sessions, threat_events, audit_logs
   - MongoDB: Collections for evidence and digital_fir

#### Dependencies:

- **Web Framework**: FastAPI, Uvicorn
- **Task Queue**: Celery, Redis
- **Databases**: asyncpg (PostgreSQL), motor (MongoDB)
- **AI/ML**: OpenAI Whisper, Google Gemini, MediaPipe
- **Security**: cryptography, PyJWT
- **Testing**: pytest, pytest-asyncio, hypothesis

### Extension Package (`packages/extension/`)

The extension is a TypeScript-based browser extension using React for the UI.

#### Key Components:

1. **Manifest** (`src/manifest.json`)
   - Manifest V3 configuration
   - Permissions: storage, tabs, activeTab
   - Host permissions for Meet, Zoom, Teams
   - Content scripts and background service worker

2. **Build Configuration** (`vite.config.ts`)
   - Vite bundler setup
   - React plugin
   - Web extension plugin

3. **TypeScript Configuration** (`tsconfig.json`)
   - Strict type checking
   - Chrome types
   - React JSX support

#### Future Structure (to be implemented):

```
src/
├── background/
│   └── service-worker.ts      # Background service worker
├── content/
│   └── content-script.ts      # WebRTC interception
├── popup/
│   ├── popup.html             # Popup UI
│   ├── popup.tsx              # React components
│   └── popup.css              # Styles
├── types/
│   └── index.ts               # TypeScript type definitions
└── utils/
    ├── encryption.ts          # AES-256-GCM encryption
    └── platform-detector.ts   # Platform detection
```

## Infrastructure

### Docker Compose Services

The `docker-compose.yml` defines the following services:

1. **postgres**: PostgreSQL 16 database
   - Port: 5432
   - Volume: postgres_data
   - Health checks enabled

2. **mongodb**: MongoDB 7.0 database
   - Port: 27017
   - Volume: mongodb_data
   - Health checks enabled

3. **redis**: Redis 7 message broker
   - Port: 6379
   - Volume: redis_data
   - Persistence enabled

4. **backend-api**: FastAPI application
   - Port: 8000
   - Depends on: postgres, mongodb, redis
   - Hot reload enabled in development

5. **celery-worker**: Celery task workers
   - Concurrency: 4 workers
   - Depends on: postgres, mongodb, redis
   - Processes audio, visual, liveness tasks

### Volumes

- `postgres_data`: PostgreSQL data persistence
- `mongodb_data`: MongoDB data persistence
- `redis_data`: Redis data persistence

## Development Workflow

### Backend Development

```bash
# Start infrastructure
docker-compose up -d

# Run API locally (alternative to Docker)
cd packages/backend
uvicorn app.main:app --reload

# Run Celery worker
celery -A app.celery_app worker --loglevel=info

# Run tests
pytest

# Linting
black . && flake8 . && mypy .
```

### Extension Development

```bash
# Install dependencies
cd packages/extension
npm install

# Development mode
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint
```

## Configuration Files

### Backend Configuration

- `.env`: Environment variables (created from `.env.example`)
  - Database URLs
  - API keys (Gemini, OpenAI)
  - JWT secret
  - CORS origins

- `pyproject.toml`: Python tooling configuration
  - Black formatter
  - isort import sorting
  - mypy type checking
  - pytest configuration

### Extension Configuration

- `package.json`: Node.js dependencies and scripts
- `tsconfig.json`: TypeScript compiler options
- `.eslintrc.cjs`: ESLint rules
- `vite.config.ts`: Build configuration

## Database Schemas

### PostgreSQL Tables

1. **users**: User accounts and preferences
2. **sessions**: Video call sessions
3. **threat_events**: Detected threats with scores
4. **audit_logs**: DPDP compliance audit trail

### MongoDB Collections

1. **evidence**: Audio/visual/liveness evidence
2. **digital_fir**: Generated FIR packages

## Testing

### Backend Tests

- Location: `packages/backend/tests/`
- Framework: pytest
- Coverage: pytest-cov
- Property-based: hypothesis

### Extension Tests

- To be implemented in future tasks
- Framework: Vitest (recommended)
- E2E: Playwright (recommended)

## Build Artifacts

### Backend

- Docker images: Built from `packages/backend/Dockerfile`
- Python packages: Installed in container

### Extension

- Build output: `packages/extension/dist/`
- Loadable in Chrome/Firefox as unpacked extension

## Scripts

### Setup Scripts

- `setup.sh`: Automated project setup
- `verify-setup.sh`: Verify setup completion

### Development Scripts

- `Makefile`: Common development commands
  - `make setup`: Initial setup
  - `make start`: Start services
  - `make stop`: Stop services
  - `make test`: Run tests
  - `make lint`: Run linters
  - `make clean`: Clean up

## Next Steps

After infrastructure setup (Task 1), the following tasks will add:

1. **Extension Core** (Task 2):
   - Content scripts for WebRTC interception
   - Background service worker
   - Platform detection

2. **Backend Services** (Tasks 6-10):
   - API endpoints
   - Inference engines
   - Threat fusion

3. **Integration** (Tasks 11-23):
   - End-to-end testing
   - CI/CD pipeline
   - Deployment configuration

## References

- Main README: `README.md`
- Setup Guide: `SETUP_GUIDE.md`
- Spec Document: `.kiro/specs/production-ready-browser-extension/`
- Requirements: `.kiro/specs/production-ready-browser-extension/requirements.md`
- Design: `.kiro/specs/production-ready-browser-extension/design.md`
- Tasks: `.kiro/specs/production-ready-browser-extension/tasks.md`
