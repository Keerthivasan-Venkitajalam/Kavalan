# Kavalan Setup Guide

This guide will help you set up the Kavalan development environment.

## Prerequisites

Before starting, ensure you have the following installed:

- **Docker** (20.10+) and **Docker Compose** (2.0+)
- **Node.js** (18+) and **npm**
- **Python** (3.11+)
- **Git**

## Quick Setup

### Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
./setup.sh
```

This will:
1. Check prerequisites
2. Create backend `.env` file
3. Install extension dependencies
4. Start Docker services (PostgreSQL, MongoDB, Redis)

### Option 2: Manual Setup

#### 1. Backend Setup

```bash
cd packages/backend

# Create environment file
cp .env.example .env

# Edit .env and add your API keys:
# - GEMINI_API_KEY
# - OPENAI_API_KEY
# - JWT_SECRET

# Create Python virtual environment (optional for local development)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 2. Extension Setup

```bash
cd packages/extension

# Install dependencies
npm install

# Build extension
npm run build
```

#### 3. Start Infrastructure

```bash
# From project root
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

## Verify Installation

### 1. Check Database Connections

```bash
# PostgreSQL
docker exec -it kavalan-postgres psql -U kavalan_user -d kavalan -c "\dt"

# MongoDB
docker exec -it kavalan-mongodb mongosh -u kavalan_user -p kavalan_dev_password --authenticationDatabase admin kavalan --eval "db.getCollectionNames()"

# Redis
docker exec -it kavalan-redis redis-cli ping
```

### 2. Check Backend API

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected","redis":"connected"}
```

### 3. Load Extension in Browser

#### Chrome:
1. Open `chrome://extensions`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select `packages/extension/dist` directory

#### Firefox:
1. Open `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `packages/extension/dist/manifest.json`

## Development Workflow

### Backend Development

```bash
cd packages/backend

# Run API server locally (alternative to Docker)
uvicorn app.main:app --reload --port 8000

# Run Celery worker
celery -A app.celery_app worker --loglevel=info --concurrency=4

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Linting
black .
flake8 .
mypy .
```

### Extension Development

```bash
cd packages/extension

# Development mode with hot reload
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
npm run build
```

## Common Issues

### Issue: Docker services won't start

**Solution:**
```bash
# Stop all services
docker-compose down

# Remove volumes
docker-compose down -v

# Restart
docker-compose up -d
```

### Issue: Port already in use

**Solution:**
```bash
# Check what's using the port
lsof -i :5432  # PostgreSQL
lsof -i :27017 # MongoDB
lsof -i :6379  # Redis
lsof -i :8000  # Backend API

# Kill the process or change ports in docker-compose.yml
```

### Issue: Extension not loading

**Solution:**
1. Ensure `npm run build` completed successfully
2. Check `packages/extension/dist` directory exists
3. Look for errors in browser console
4. Try reloading the extension

### Issue: Backend can't connect to databases

**Solution:**
```bash
# Check service health
docker-compose ps

# View logs
docker-compose logs postgres
docker-compose logs mongodb
docker-compose logs redis

# Restart services
docker-compose restart
```

## Environment Variables

### Required Backend Variables

```bash
# Database connections
DATABASE_URL=postgresql://kavalan_user:kavalan_dev_password@localhost:5432/kavalan
MONGODB_URL=mongodb://kavalan_user:kavalan_dev_password@localhost:27017/kavalan
REDIS_URL=redis://localhost:6379/0

# API Keys (get from respective providers)
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Security
JWT_SECRET=your_secure_random_string_here

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Next Steps

After setup is complete:

1. **Review the architecture**: See `README.md` for system architecture
2. **Check the spec**: Review `.kiro/specs/production-ready-browser-extension/`
3. **Start implementing tasks**: Follow `tasks.md` for implementation order
4. **Test on video platforms**: Try the extension on Google Meet, Zoom, or Teams

## Useful Commands

```bash
# Start all services
make start

# Stop all services
make stop

# View logs
make logs

# Run tests
make test

# Run linters
make lint

# Clean up everything
make clean
```

## Support

For issues or questions:
1. Check the logs: `docker-compose logs -f`
2. Review the spec documentation in `.kiro/specs/`
3. Check the README.md for architecture details
