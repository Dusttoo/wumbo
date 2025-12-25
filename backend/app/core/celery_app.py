"""Celery application configuration"""

from app.core.config import settings
from celery import Celery
from celery.schedules import crontab

# Create Celery app
celery_app = Celery(
    "wumbo",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.plaid_tasks",
        "app.tasks.notification_tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Sync Plaid transactions daily at 2 AM
    "sync-plaid-transactions": {
        "task": "app.tasks.plaid_tasks.sync_all_accounts",
        "schedule": crontab(hour=2, minute=0),
    },
    # Send bill reminders every day at 9 AM
    "send-bill-reminders": {
        "task": "app.tasks.notification_tasks.send_bill_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    # Check budget alerts every 6 hours
    "check-budget-alerts": {
        "task": "app.tasks.notification_tasks.check_budget_alerts",
        "schedule": crontab(minute=0, hour="*/6"),
    },
}
