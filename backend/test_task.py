"""Quick script to test Celery tasks"""

from app.tasks.email_tasks import send_email
from app.tasks.plaid_tasks import sync_all_accounts
from app.tasks.notification_tasks import send_notification

print("Testing Celery tasks...")

# Test 1: Send email (will be skipped since SES not configured)
print("\n1. Testing send_email task...")
result = send_email.delay(
    ["test@example.com"],
    "Test Subject",
    "Test body text",
).get(timeout=10)
print(f"   Result: {result}")

# Test 2: Sync all accounts
print("\n2. Testing sync_all_accounts task...")
result = sync_all_accounts.delay().get(timeout=10)
print(f"   Result: {result}")

# Test 3: Send notification
print("\n3. Testing send_notification task...")
result = send_notification.delay(
    "test-user-id",
    "test_notification",
    "Test Title",
    "Test Message",
    ["in-app"],
).get(timeout=10)
print(f"   Result: {result}")

print("\n✅ All tasks completed successfully!")
