"""Email-related Celery tasks"""

from typing import List, Optional

import boto3
from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logging import logger
from botocore.exceptions import ClientError


@celery_app.task(name="app.tasks.email_tasks.send_email", bind=True, max_retries=3)
def send_email(
    self,
    to_addresses: List[str],
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> dict:
    """
    Send email via AWS SES

    Args:
        to_addresses: List of recipient email addresses
        subject: Email subject
        body_text: Plain text email body
        body_html: Optional HTML email body

    Returns:
        dict with status and message_id

    Raises:
        Exception: If email sending fails after retries
    """
    if not settings.SES_SENDER_EMAIL:
        logger.warning("SES not configured, skipping email send")
        return {"status": "skipped", "reason": "SES not configured"}

    # Skip if AWS credentials not properly configured
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        logger.warning("AWS credentials not configured, skipping email send")
        return {"status": "skipped", "reason": "AWS credentials not configured"}

    try:
        ses_client = boto3.client(
            "ses",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        # Build message
        message = {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}},
        }

        if body_html:
            message["Body"]["Html"] = {"Data": body_html, "Charset": "UTF-8"}

        # Send email
        response = ses_client.send_email(
            Source=f"{settings.SES_SENDER_NAME} <{settings.SES_SENDER_EMAIL}>",
            Destination={"ToAddresses": to_addresses},
            Message=message,
        )

        logger.info(f"Email sent successfully to {to_addresses}, MessageId: {response['MessageId']}")
        return {"status": "sent", "message_id": response["MessageId"]}

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"SES error ({error_code}): {error_message}")

        # Retry on temporary errors
        if error_code in ["Throttling", "ServiceUnavailable"]:
            raise self.retry(exc=e, countdown=60)

        raise e
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(name="app.tasks.email_tasks.send_welcome_email")
def send_welcome_email(user_email: str, user_name: str) -> dict:
    """
    Send welcome email to new user

    Args:
        user_email: User's email address
        user_name: User's name

    Returns:
        dict with status
    """
    subject = "Welcome to Wumbo!"
    body_text = f"""
Hello {user_name},

Welcome to Wumbo! We're excited to have you on board.

Get started by:
1. Connecting your bank accounts
2. Setting up your first budget
3. Adding household members

If you have any questions, feel free to reach out to our support team.

Best regards,
The Wumbo Team
"""

    body_html = f"""
<html>
<head></head>
<body>
    <h2>Hello {user_name},</h2>
    <p>Welcome to Wumbo! We're excited to have you on board.</p>

    <h3>Get started by:</h3>
    <ol>
        <li>Connecting your bank accounts</li>
        <li>Setting up your first budget</li>
        <li>Adding household members</li>
    </ol>

    <p>If you have any questions, feel free to reach out to our support team.</p>

    <p>Best regards,<br>The Wumbo Team</p>
</body>
</html>
"""

    return send_email.delay([user_email], subject, body_text, body_html).get()
