#!/bin/bash
# Manual deploy script for EC2
# Usage: ./scripts/deploy.sh

set -e

DOCKER_IMAGE="your-dockerhub-username/lgir-parser"
CONTAINER_NAME="lgir-parser"

echo "🚀 Starting deployment..."

# Pull latest image
echo "📥 Pulling latest image..."
docker pull ${DOCKER_IMAGE}:latest

# Stop old container
echo "🛑 Stopping old container..."
docker stop ${CONTAINER_NAME} 2>/dev/null || true
docker rm ${CONTAINER_NAME} 2>/dev/null || true

# Run new container
echo "🐳 Starting new container..."
docker run -d \
  --name ${CONTAINER_NAME} \
  --restart unless-stopped \
  -p 9000:8000 \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e PORT=8000 \
  ${DOCKER_IMAGE}:latest

# Wait and health check
echo "⏳ Waiting for container to start..."
sleep 5

if curl -sf http://localhost:9000/health > /dev/null; then
  echo "✅ Health check passed!"
else
  echo "❌ Health check failed!"
  docker logs ${CONTAINER_NAME}
  exit 1
fi

# Cleanup
echo "🧹 Cleaning up old images..."
docker image prune -f

echo ""
echo "=========================================="
echo "✅ Deployment completed successfully!"
echo "🌐 Service running at: http://localhost:9000"
echo "📚 API Docs: http://localhost:9000/docs"
echo "=========================================="

