"""Test Celery tasks"""

import pytest
from app.tasks.email_tasks import send_email
from app.tasks.plaid_tasks import sync_account_transactions, sync_all_accounts
from app.tasks.notification_tasks import send_notification


def test_send_email_task():
    """Test email sending task"""
    # This will be skipped in tests since SES is not configured
    result = send_email.apply(
        args=[
            ["test@example.com"],
            "Test Subject",
            "Test body text",
            "<html><body>Test HTML</body></html>",
        ]
    ).get()

    assert result["status"] == "skipped"
    assert result["reason"] == "SES not configured"


def test_sync_account_transactions():
    """Test Plaid account sync task"""
    result = sync_account_transactions.apply(args=["test-account-id"]).get()

    assert result["status"] == "success"
    assert result["account_id"] == "test-account-id"


def test_sync_all_accounts():
    """Test sync all accounts task"""
    result = sync_all_accounts.apply().get()

    assert result["status"] == "completed"
    assert "synced" in result
    assert "failed" in result


def test_send_notification():
    """Test notification sending task"""
    result = send_notification.apply(
        args=[
            "test-user-id",
            "test_notification",
            "Test Title",
            "Test Message",
            ["in-app"],
        ]
    ).get()

    assert result["status"] == "sent"
    assert result["user_id"] == "test-user-id"
