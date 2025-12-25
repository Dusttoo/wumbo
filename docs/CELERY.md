# Celery Worker Setup

Background task processing using Celery with Redis as the message broker.

## Overview

The Wumbo application uses Celery for:
- **Email notifications** via AWS SES
- **Bank account syncing** with Plaid API
- **Budget alerts** and reminders
- **Scheduled tasks** via Celery Beat

## Architecture

```
┌─────────────┐
│   FastAPI   │──┐
│   Backend   │  │
└─────────────┘  │
                 │
                 ▼
            ┌────────┐      ┌──────────────┐
            │ Redis  │◄────►│ Celery Worker│
            │(Broker)│      │  (4 workers) │
            └────────┘      └──────────────┘
                 ▲
                 │
            ┌────┴─────┐
            │  Celery  │
            │   Beat   │
            │(Scheduler)│
            └──────────┘
```

## Components

### 1. Celery Worker
- Processes background tasks asynchronously
- Runs 4 concurrent workers by default
- Handles email, Plaid sync, and notifications

### 2. Celery Beat
- Scheduled task scheduler (cron-like)
- Triggers periodic tasks:
  - Daily Plaid sync at 2 AM
  - Bill reminders at 9 AM
  - Budget alerts every 6 hours

### 3. Flower (Monitoring)
- Web-based monitoring tool
- Access at http://localhost:5555
- Default credentials: admin/admin

## Task Types

### Email Tasks (`app/tasks/email_tasks.py`)

**send_email**
- Send email via AWS SES
- Supports plain text and HTML
- Automatic retry on temporary failures

**send_welcome_email**
- Welcome email for new users
- Called after user registration

### Plaid Tasks (`app/tasks/plaid_tasks.py`)

**sync_account_transactions**
- Sync transactions for a specific account
- Triggered by webhooks or scheduled sync

**sync_all_accounts**
- Sync all active bank accounts
- Runs daily at 2 AM via Celery Beat

**handle_plaid_webhook**
- Process Plaid webhook events
- Handles transaction updates and errors

### Notification Tasks (`app/tasks/notification_tasks.py`)

**send_bill_reminders**
- Send reminders for upcoming bills
- Runs daily at 9 AM

**check_budget_alerts**
- Check budgets and send alerts
- Runs every 6 hours

**send_notification**
- Multi-channel notification delivery
- Supports email, push, and in-app

## Running Locally

### Start all services with Docker Compose

```bash
# Start all services (backend, worker, beat, flower)
docker-compose up -d

# View worker logs
docker-compose logs -f worker

# View beat logs
docker-compose logs -f beat
```

### Start worker manually (without Docker)

```bash
# Terminal 1: Start worker
celery -A app.core.celery_app worker --loglevel=info --concurrency=4

# Terminal 2: Start beat scheduler
celery -A app.core.celery_app beat --loglevel=info

# Terminal 3: Start flower monitoring
celery -A app.core.celery_app flower --port=5555
```

## Testing Tasks

### Test task execution

```python
from app.tasks.email_tasks import send_email

# Run task synchronously (for testing)
result = send_email.apply(
    args=[
        ["user@example.com"],
        "Test Subject",
        "Test body",
        "<html>Test HTML</html>"
    ]
).get()

print(result)
```

### Queue a task asynchronously

```python
from app.tasks.email_tasks import send_welcome_email

# Queue task (returns immediately)
task = send_welcome_email.delay("user@example.com", "John Doe")

# Check task status
print(task.status)  # PENDING, STARTED, SUCCESS, FAILURE

# Get result (blocks until complete)
result = task.get(timeout=10)
print(result)
```

### Run scheduled tasks manually

```bash
# Trigger Plaid sync manually
celery -A app.core.celery_app call app.tasks.plaid_tasks.sync_all_accounts

# Trigger bill reminders manually
celery -A app.core.celery_app call app.tasks.notification_tasks.send_bill_reminders
```

## Monitoring

### Flower Dashboard

Access at: http://localhost:5555

Features:
- Real-time task monitoring
- Worker status and stats
- Task history and results
- Queue management
- Rate limiting controls

Default login:
- Username: `admin`
- Password: `admin`

### Command Line Tools

```bash
# Inspect active tasks
celery -A app.core.celery_app inspect active

# Inspect registered tasks
celery -A app.core.celery_app inspect registered

# Worker stats
celery -A app.core.celery_app inspect stats

# Scheduled tasks (from beat)
celery -A app.core.celery_app inspect scheduled
```

## Configuration

### Celery Settings (app/core/celery_app.py)

```python
# Task execution
task_time_limit = 30 * 60  # 30 minutes max
task_soft_time_limit = 25 * 60  # Soft limit before hard kill

# Worker settings
worker_prefetch_multiplier = 1  # Tasks per worker
worker_max_tasks_per_child = 1000  # Restart after N tasks

# Serialization
task_serializer = "json"
result_serializer = "json"
```

### Beat Schedule

Defined in `app/core/celery_app.py`:

```python
beat_schedule = {
    "sync-plaid-transactions": {
        "task": "app.tasks.plaid_tasks.sync_all_accounts",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
    "send-bill-reminders": {
        "task": "app.tasks.notification_tasks.send_bill_reminders",
        "schedule": crontab(hour=9, minute=0),  # 9 AM daily
    },
    "check-budget-alerts": {
        "task": "app.tasks.notification_tasks.check_budget_alerts",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
}
```

## Task Best Practices

### 1. Idempotency
Tasks should be idempotent (safe to retry):

```python
@celery_app.task(bind=True, max_retries=3)
def my_task(self, user_id):
    try:
        # Check if already processed
        if already_processed(user_id):
            return {"status": "already_processed"}

        # Do work
        process_user(user_id)

    except Exception as e:
        # Retry on failure
        raise self.retry(exc=e, countdown=60)
```

### 2. Error Handling
Use proper error handling and retries:

```python
@celery_app.task(bind=True, max_retries=3)
def risky_task(self):
    try:
        # Task logic
        pass
    except TemporaryError as e:
        # Retry on temporary errors
        raise self.retry(exc=e, countdown=60)
    except PermanentError:
        # Log and fail on permanent errors
        logger.error("Permanent failure")
        raise
```

### 3. Timeouts
Set appropriate timeouts:

```python
@celery_app.task(time_limit=300, soft_time_limit=270)
def long_task():
    # Task with 5 min hard limit, 4.5 min soft limit
    pass
```

## Troubleshooting

### Worker not processing tasks

```bash
# Check if worker is running
docker-compose ps worker

# View worker logs
docker-compose logs worker

# Restart worker
docker-compose restart worker
```

### Tasks stuck in queue

```bash
# Purge all tasks
celery -A app.core.celery_app purge

# Inspect active queues
celery -A app.core.celery_app inspect active_queues
```

### Beat schedule not running

```bash
# Check beat logs
docker-compose logs beat

# Verify schedule is registered
celery -A app.core.celery_app inspect scheduled

# Restart beat
docker-compose restart beat
```

## Production Considerations

1. **Scaling**: Increase worker concurrency based on load
2. **Monitoring**: Use Flower + CloudWatch for production monitoring
3. **Rate Limiting**: Configure rate limits for external APIs (Plaid, SES)
4. **Dead Letter Queue**: Configure for failed task handling
5. **Task Priority**: Use priority queues for critical tasks

## Resources

- [Celery Documentation](https://docs.celeryq.dev/)
- [Flower Documentation](https://flower.readthedocs.io/)
- [Redis Documentation](https://redis.io/docs/)
