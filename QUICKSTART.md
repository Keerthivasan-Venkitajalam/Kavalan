# Kavalan Quick Start Guide

Get Kavalan up and running in 10 minutes!

## Prerequisites

Before you begin, ensure you have:

- ✅ **Docker Desktop** installed ([Download](https://www.docker.com/products/docker-desktop))
- ✅ **Node.js 18+** installed ([Download](https://nodejs.org/))
- ✅ **Google Gemini API Key** ([Get one free](https://makersuite.google.com/app/apikey))
- ✅ **Chrome or Firefox** browser

## Step 1: Clone the Repository

```bash
git clone https://github.com/Keerthivasan-Venkitajalam/Kavalan.git
cd Kavalan
```

## Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Open .env in your favorite editor
nano .env  # or vim, code, etc.
```

Add your Gemini API key:

```env
GEMINI_API_KEY=your_actual_api_key_here
```

Save and close the file.

## Step 3: Start Backend Services

```bash
# Start PostgreSQL, MongoDB, Redis, and FastAPI
docker compose up -d --build

# Wait for services to be healthy (30-60 seconds)
docker compose ps
```

You should see all services with status "Up (healthy)".

## Step 4: Initialize Databases

```bash
# Run database initialization script
docker exec kavalan-api python -m scripts.init_db

# Verify database health
curl http://localhost:8000/health/dependencies | jq
```

Expected output:
```json
{
  "status": "healthy",
  "checks": {
    "database": { "status": "healthy" },
    "redis": { "status": "healthy" },
    "mongodb": { "status": "healthy" }
  }
}
```

## Step 5: Build Browser Extension

```bash
# Navigate to extension directory
cd packages/extension

# Install dependencies
npm install

# Build extension
npm run build
```

The built extension will be in `packages/extension/dist/`.

## Step 6: Load Extension in Browser

### For Chrome:

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right corner)
3. Click "Load unpacked"
4. Select the `packages/extension/dist` folder
5. The Kavalan extension icon should appear in your toolbar

### For Firefox:

1. Open Firefox and navigate to `about:debugging`
2. Click "This Firefox" in the left sidebar
3. Click "Load Temporary Add-on"
4. Navigate to `packages/extension/dist` and select `manifest.json`
5. The Kavalan extension icon should appear in your toolbar

## Step 7: Test the Extension

1. **Join a test video call**:
   - Go to [Google Meet](https://meet.google.com/)
   - Start a new meeting or join an existing one

2. **Verify monitoring is active**:
   - Click the Kavalan extension icon
   - You should see "Monitoring Active" status
   - The threat gauge should show "Safe" (green)

3. **Test threat detection** (optional):
   - Speak some test keywords: "police", "arrest", "payment required"
   - The threat gauge should increase
   - Check the transcript panel for detected keywords

## Step 8: View Backend Logs

```bash
# View API logs
docker logs -f kavalan-api

# View Celery worker logs
docker logs -f kavalan-celery-worker

# View all logs
docker compose logs -f
```

## Step 9: Access Monitoring Dashboards

### API Documentation
- URL: http://localhost:8000/docs
- Interactive Swagger UI for testing API endpoints

### Prometheus Metrics
- URL: http://localhost:9090
- View raw metrics and query data

### Grafana Dashboards
- URL: http://localhost:3000
- Default credentials: admin / admin
- Pre-built dashboards for threat detection and system health

## Troubleshooting

### Issue: "Cannot connect to backend"

**Solution**:
```bash
# Check if backend is running
docker compose ps

# Restart backend services
docker compose restart kavalan-api

# Check logs for errors
docker logs kavalan-api
```

### Issue: "Gemini API error"

**Solution**:
- Verify your API key is correct in `.env`
- Check API quota at [Google AI Studio](https://makersuite.google.com/)
- Ensure you have billing enabled (if required)

### Issue: "Extension not detecting video calls"

**Solution**:
- Refresh the video call page
- Check browser console for errors (F12 → Console)
- Verify extension permissions are granted
- Try reloading the extension

### Issue: "Database connection failed"

**Solution**:
```bash
# Check database containers
docker compose ps

# Restart databases
docker compose restart kavalan-db kavalan-mongodb

# Reinitialize databases
docker exec kavalan-api python -m scripts.init_db
```

## Next Steps

### Explore Features

1. **Multi-language support**: Change language in extension preferences
2. **Threat history**: View past threat detections in popup UI
3. **Digital FIR**: Trigger high-threat scenarios to generate evidence packages
4. **Accessibility**: Test keyboard navigation and screen reader support

### Development

1. **Run tests**:
   ```bash
   # Backend tests
   cd packages/backend
   pytest tests/ -v

   # Frontend tests
   cd packages/extension
   npm test
   ```

2. **Enable hot reload**:
   ```bash
   # Backend (in packages/backend)
   uvicorn app.main:app --reload

   # Frontend (in packages/extension)
   npm run dev
   ```

3. **View architecture**:
   - Read [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design
   - Check [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines

### Production Deployment

For production deployment instructions, see:
- [Docker Production Setup](README.md#docker-production)
- [Kubernetes Deployment](README.md#kubernetes)
- [CI/CD Pipeline](README.md#cicd-pipeline)

## Getting Help

- 📖 **Documentation**: [README.md](README.md)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/Keerthivasan-Venkitajalam/Kavalan/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/Keerthivasan-Venkitajalam/Kavalan/discussions)
- 📧 **Email**: keerthivasan.sv@example.com

## Success! 🎉

You now have Kavalan running locally. The system is:
- ✅ Monitoring video calls in real-time
- ✅ Analyzing audio, visual, and liveness data
- ✅ Generating threat scores and alerts
- ✅ Collecting evidence for Digital FIR

**Stay safe from Digital Arrest scams!**

---

Built with ❤️ by Team Thudakkam
