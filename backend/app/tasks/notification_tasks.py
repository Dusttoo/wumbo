"""Notification-related Celery tasks"""

from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.logging import logger
from app.db.session import SessionLocal
from app.tasks.email_tasks import send_email


@celery_app.task(name="app.tasks.notification_tasks.send_bill_reminders")
def send_bill_reminders() -> dict:
    """
    Send reminders for upcoming bills

    Checks for bills due in the next 3 days and sends reminder emails

    Returns:
        dict with reminder count
    """
    db: Session = SessionLocal()
    try:
        logger.info("Checking for upcoming bills to send reminders")

        # TODO: Implement bill reminder logic
        # 1. Query bills due in next 3 days
        # 2. Check if reminder already sent
        # 3. Send email reminder to household members
        # 4. Mark reminder as sent

        reminders_sent = 0
        logger.info(f"Sent {reminders_sent} bill reminders")

        return {"status": "completed", "reminders_sent": reminders_sent}

    except Exception as e:
        logger.error(f"Failed to send bill reminders: {str(e)}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.notification_tasks.check_budget_alerts")
def check_budget_alerts() -> dict:
    """
    Check budgets and send alerts for those approaching or exceeding limits

    Returns:
        dict with alert count
    """
    db: Session = SessionLocal()
    try:
        logger.info("Checking budgets for alerts")

        # TODO: Implement budget alert logic
        # 1. Query all active budgets
        # 2. Calculate current spending for budget period
        # 3. Check if spending >= 80% or >= 100% of budget
        # 4. Send alert emails if thresholds crossed
        # 5. Track alerts sent to avoid duplicates

        alerts_sent = 0
        logger.info(f"Sent {alerts_sent} budget alerts")

        return {"status": "completed", "alerts_sent": alerts_sent}

    except Exception as e:
        logger.error(f"Failed to check budget alerts: {str(e)}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.notification_tasks.send_notification")
def send_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    channels: List[str] = None,
) -> dict:
    """
    Send notification to user via specified channels

    Args:
        user_id: User ID to send notification to
        notification_type: Type of notification (bill_reminder, budget_alert, etc.)
        title: Notification title
        message: Notification message
        channels: List of channels to send via (email, push, in-app)

    Returns:
        dict with delivery status
    """
    if channels is None:
        channels = ["email", "in-app"]

    db: Session = SessionLocal()
    try:
        logger.info(f"Sending {notification_type} notification to user {user_id}")

        # TODO: Implement multi-channel notification
        # 1. Get user from database
        # 2. Check user notification preferences
        # 3. Send via requested channels:
        #    - Email: via SES
        #    - Push: via SNS
        #    - In-app: save to notifications table
        # 4. Track delivery status

        sent_channels = []
        failed_channels = []

        # Placeholder: Save in-app notification
        if "in-app" in channels:
            sent_channels.append("in-app")

        logger.info(f"Notification sent via: {', '.join(sent_channels)}")

        return {
            "status": "sent",
            "user_id": user_id,
            "channels_sent": sent_channels,
            "channels_failed": failed_channels,
        }

    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
