# Kavalan Quick Reference

Quick commands and references for Kavalan development.

## Quick Start

```bash
# 1. Setup (first time only)
./setup.sh

# 2. Start all services
docker-compose up -d

# 3. Check status
docker-compose ps

# 4. View logs
docker-compose logs -f
```

## Common Commands

### Docker Services

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose stop

# Restart services
docker-compose restart

# Stop and remove containers
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# View logs
docker-compose logs -f [service-name]

# Check service status
docker-compose ps
```

### Backend Development

```bash
cd packages/backend

# Run API locally
uvicorn app.main:app --reload --port 8000

# Run Celery worker
celery -A app.celery_app worker --loglevel=info --concurrency=4

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Format code
black .

# Lint code
flake8 .

# Type check
mypy .

# All linting
black . && flake8 . && mypy .
```

### Extension Development

```bash
cd packages/extension

# Install dependencies
npm install

# Development mode (hot reload)
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint
```

### Database Access

```bash
# PostgreSQL
docker exec -it kavalan-postgres psql -U kavalan_user -d kavalan

# MongoDB
docker exec -it kavalan-mongodb mongosh -u kavalan_user -p kavalan_dev_password --authenticationDatabase admin kavalan

# Redis
docker exec -it kavalan-redis redis-cli
```

## Service Endpoints

- **Backend API**: http://localhost:8000
- **API Health**: http://localhost:8000/health
- **PostgreSQL**: localhost:5432
- **MongoDB**: localhost:27017
- **Redis**: localhost:6379

## Environment Variables

Edit `packages/backend/.env`:

```bash
# Required
DATABASE_URL=postgresql://kavalan_user:kavalan_dev_password@localhost:5432/kavalan
MONGODB_URL=mongodb://kavalan_user:kavalan_dev_password@localhost:27017/kavalan
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
JWT_SECRET=your_secret_here

# Optional
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Project Structure

```
packages/
├── backend/          # Python backend
│   ├── app/         # Application code
│   ├── db/          # Database schemas
│   └── tests/       # Tests
└── extension/       # TypeScript extension
    └── src/         # Source code
```

## Useful SQL Queries

```sql
-- List all users
SELECT * FROM users;

-- List active sessions
SELECT * FROM sessions WHERE end_time IS NULL;

-- Recent threat events
SELECT * FROM threat_events ORDER BY timestamp DESC LIMIT 10;

-- Audit logs
SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 20;
```

## Useful MongoDB Queries

```javascript
// List evidence
db.evidence.find().limit(10)

// Find high-threat evidence
db.evidence.find({ "audio.score": { $gt: 7 } })

// List digital FIRs
db.digital_fir.find().sort({ generated_at: -1 }).limit(10)
```

## Troubleshooting

### Services won't start
```bash
docker-compose down -v
docker-compose up -d
```

### Port already in use
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Database connection errors
```bash
# Check service health
docker-compose ps

# Restart database
docker-compose restart postgres
docker-compose restart mongodb
```

### Extension not loading
```bash
# Rebuild extension
cd packages/extension
rm -rf dist
npm run build
```

## Testing

```bash
# Backend tests
cd packages/backend
pytest

# With coverage
pytest --cov=app

# Specific test file
pytest tests/test_api.py

# Specific test
pytest tests/test_api.py::test_root_endpoint
```

## Makefile Commands

```bash
make setup    # Initial setup
make start    # Start services
make stop     # Stop services
make clean    # Clean up
make test     # Run tests
make lint     # Run linters
make logs     # View logs
```

## Load Extension in Browser

### Chrome
1. Open `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `packages/extension/dist`

### Firefox
1. Open `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `packages/extension/dist/manifest.json`

## Documentation

- **Setup Guide**: `SETUP_GUIDE.md`
- **Project Structure**: `PROJECT_STRUCTURE.md`
- **Main README**: `README.md`
- **Spec Document**: `.kiro/specs/production-ready-browser-extension/`

## Support

Check logs for errors:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend-api
docker-compose logs -f celery-worker
docker-compose logs -f postgres
```
