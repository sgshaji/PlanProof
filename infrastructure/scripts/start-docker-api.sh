#!/bin/bash
# Start the PlanProof FastAPI Backend with Docker

set -e

echo "🐳 Starting PlanProof FastAPI Backend with Docker..."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .env file created. Please update it with your configuration."
    else
        echo "⚠️  No .env.example found. Using default configuration."
    fi
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.api.yml down 2>/dev/null || true

# Build and start the services
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.api.yml build

echo "🚀 Starting services..."
docker-compose -f docker-compose.api.yml up -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if API is responding
echo "🔍 Checking API health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo ""
        echo "✅ PlanProof API is running!"
        echo ""
        echo "📍 API URL: http://localhost:8000"
        echo "📖 API Docs: http://localhost:8000/api/docs"
        echo "📊 Health Check: http://localhost:8000/api/health"
        echo ""
        echo "To view logs: docker-compose -f docker-compose.api.yml logs -f api"
        echo "To stop: docker-compose -f docker-compose.api.yml down"
        exit 0
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "⚠️  API did not respond within expected time. Checking logs..."
echo ""
docker-compose -f docker-compose.api.yml logs api | tail -20
echo ""
echo "Run 'docker-compose -f docker-compose.api.yml logs -f api' to see full logs"
exit 1
