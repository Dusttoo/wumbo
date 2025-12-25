"""Celery worker entry point"""

from app.core.celery_app import celery_app
from app.core.logging import setup_logging

# Setup logging
setup_logging()

if __name__ == "__main__":
    celery_app.start()
