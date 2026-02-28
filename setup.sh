#!/bin/bash

# Kavalan Project Setup Script

set -e

echo "🚀 Setting up Kavalan project..."

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.11+ first."
    exit 1
fi

echo "✅ All prerequisites found"

# Setup backend
echo ""
echo "📦 Setting up backend..."
cd packages/backend

if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file (please edit with your API keys)"
else
    echo "⚠️  .env file already exists, skipping"
fi

cd ../..

# Setup extension
echo ""
echo "📦 Setting up extension..."
cd packages/extension

if [ ! -d node_modules ]; then
    npm install
    echo "✅ Installed extension dependencies"
else
    echo "⚠️  node_modules already exists, skipping npm install"
fi

cd ../..

# Start Docker services
echo ""
echo "🐳 Starting Docker services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "🔍 Checking service health..."
docker-compose ps

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit packages/backend/.env with your API keys (GEMINI_API_KEY, OPENAI_API_KEY)"
echo "2. Build the extension: cd packages/extension && npm run build"
echo "3. Load the extension in Chrome from packages/extension/dist"
echo "4. Check service logs: docker-compose logs -f"
echo ""
echo "For more information, see README.md"
