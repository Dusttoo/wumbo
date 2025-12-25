#!/bin/bash
# Start Celery beat scheduler

set -e

echo "Starting Celery beat..."

# Wait for Redis to be available
echo "Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-localhost} ${REDIS_PORT:-6379}; do
  sleep 1
done
echo "Redis is ready!"

# Remove old beat schedule database
rm -f celerybeat-schedule.db

# Start Celery beat
celery -A app.core.celery_app beat \
  --loglevel=info \
  --schedule=/tmp/celerybeat-schedule
