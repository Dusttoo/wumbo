#!/bin/bash
# Start Celery worker

set -e

echo "Starting Celery worker..."

# Wait for Redis to be available
echo "Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-localhost} ${REDIS_PORT:-6379}; do
  sleep 1
done
echo "Redis is ready!"

# Start Celery worker
celery -A app.core.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=1000 \
  --time-limit=1800 \
  --soft-time-limit=1500
