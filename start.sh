#!/bin/bash

# Treebo Chatbot Startup Script

echo "🚀 Starting Treebo Chatbot System"
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your API keys:"
    echo "   - GOOGLE_PLACES_API_KEY"
    echo "   - OPENAI_API_KEY (optional)"
    echo "   - FOURSQUARE_API_KEY (optional)"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services started successfully!"
    echo ""
    echo "🌐 Access points:"
    echo "   - Web Interface: http://localhost:5000"
    echo "   - API Health Check: http://localhost:5000/health"
    echo "   - API Documentation: See README.md"
    echo ""
    echo "📊 Service Status:"
    docker-compose ps
    echo ""
    echo "📝 To view logs: docker-compose logs -f"
    echo "🛑 To stop: docker-compose down"
else
    echo "❌ Failed to start services. Check logs:"
    docker-compose logs
fi
