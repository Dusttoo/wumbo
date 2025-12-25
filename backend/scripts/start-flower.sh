#!/bin/bash
# Start Celery Flower monitoring tool

set -e

echo "Starting Celery Flower..."

# Wait for Redis to be available
echo "Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-localhost} ${REDIS_PORT:-6379}; do
  sleep 1
done
echo "Redis is ready!"

# Start Flower
celery -A app.core.celery_app flower \
  --port=5555 \
  --basic_auth=${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin}
