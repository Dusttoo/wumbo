"""Simple script to test Celery tasks without waiting for results"""

from app.tasks.email_tasks import send_email
from app.tasks.plaid_tasks import sync_all_accounts
from app.tasks.notification_tasks import send_notification

print("Testing Celery task queueing...")

# Test 1: Queue email task
print("\n1. Queueing send_email task...")
task1 = send_email.delay(
    ["test@example.com"],
    "Test Subject",
    "Test body text",
)
print(f"   ✓ Task queued with ID: {task1.id}")
print(f"   Status: {task1.status}")

# Test 2: Queue sync task
print("\n2. Queueing sync_all_accounts task...")
task2 = sync_all_accounts.delay()
print(f"   ✓ Task queued with ID: {task2.id}")
print(f"   Status: {task2.status}")

# Test 3: Queue notification task
print("\n3. Queueing send_notification task...")
task3 = send_notification.delay(
    "test-user-id",
    "test_notification",
    "Test Title",
    "Test Message",
    ["in-app"],
)
print(f"   ✓ Task queued with ID: {task3.id}")
print(f"   Status: {task3.status}")

print("\n✅ All tasks queued successfully!")
print("   Check the worker logs to see task execution.")
print("   Run: docker-compose logs -f worker")
