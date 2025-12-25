"""Plaid-related Celery tasks"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.logging import logger
from app.db.session import SessionLocal
from app.services.plaid_service import PlaidService


@celery_app.task(name="app.tasks.plaid_tasks.sync_account_transactions", bind=True, max_retries=3)
def sync_account_transactions(self, account_id: str) -> dict:
    """
    Sync transactions for a specific bank account via Plaid

    Args:
        account_id: Bank account ID to sync

    Returns:
        dict with sync status and transaction count

    Raises:
        Exception: If sync fails after retries
    """
    db: Session = SessionLocal()
    try:
        logger.info(f"Starting transaction sync for account {account_id}")

        # Use PlaidService to sync transactions
        result = PlaidService.sync_account_transactions(db, account_id)

        logger.info(f"Transaction sync completed for account {account_id}")
        return {
            "status": "success",
            "account_id": account_id,
            "transactions_added": result["added"],
            "transactions_modified": result["modified"],
            "transactions_removed": result["removed"],
        }

    except Exception as e:
        logger.error(f"Failed to sync account {account_id}: {str(e)}")
        db.rollback()
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes
    finally:
        db.close()


@celery_app.task(name="app.tasks.plaid_tasks.sync_all_accounts")
def sync_all_accounts() -> dict:
    """
    Sync transactions for all active bank accounts

    Returns:
        dict with overall sync status
    """
    from app.models.bank_account import BankAccount

    db: Session = SessionLocal()
    try:
        logger.info("Starting daily Plaid sync for all accounts")

        # Get all active bank accounts
        accounts = db.query(BankAccount).filter(BankAccount.is_active == True).all()

        logger.info(f"Found {len(accounts)} active accounts to sync")

        # Queue sync task for each account
        accounts_synced = 0
        accounts_failed = 0

        for account in accounts:
            try:
                # Queue sync task
                sync_account_transactions.delay(str(account.id))
                accounts_synced += 1
            except Exception as e:
                logger.error(f"Failed to queue sync for account {account.id}: {str(e)}")
                accounts_failed += 1

        logger.info(
            f"Daily Plaid sync completed. Queued: {accounts_synced}, Failed: {accounts_failed}"
        )
        return {
            "status": "completed",
            "queued": accounts_synced,
            "failed": accounts_failed,
        }

    except Exception as e:
        logger.error(f"Failed to sync all accounts: {str(e)}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.plaid_tasks.handle_plaid_webhook")
def handle_plaid_webhook(webhook_type: str, webhook_code: str, item_id: str) -> dict:
    """
    Handle Plaid webhook events

    Args:
        webhook_type: Type of webhook (e.g., 'TRANSACTIONS', 'ITEM')
        webhook_code: Specific webhook code
        item_id: Plaid item ID

    Returns:
        dict with processing status
    """
    from app.models.bank_account import BankAccount

    db: Session = SessionLocal()
    try:
        logger.info(f"Processing Plaid webhook: {webhook_type}.{webhook_code} for item {item_id}")

        # Handle different webhook types
        if webhook_type == "TRANSACTIONS":
            if webhook_code in ["DEFAULT_UPDATE", "HISTORICAL_UPDATE", "INITIAL_UPDATE"]:
                # New transactions available - sync all accounts for this item
                logger.info(f"New transactions available for item {item_id}")

                accounts = (
                    db.query(BankAccount)
                    .filter(BankAccount.plaid_item_id == item_id, BankAccount.is_active == True)
                    .all()
                )

                for account in accounts:
                    sync_account_transactions.delay(str(account.id))

                return {
                    "status": "processed",
                    "accounts_queued": len(accounts),
                }

        elif webhook_type == "ITEM":
            if webhook_code == "ERROR":
                # Mark accounts as having errors
                logger.warning(f"Item error for {item_id}")

                accounts = db.query(BankAccount).filter(BankAccount.plaid_item_id == item_id).all()

                for account in accounts:
                    account.sync_error = "Plaid item error - re-authentication required"
                    account.is_active = False

                db.commit()

                return {
                    "status": "processed",
                    "accounts_marked_error": len(accounts),
                }

        return {"status": "processed", "webhook_type": webhook_type, "webhook_code": webhook_code}

    except Exception as e:
        logger.error(f"Failed to process webhook: {str(e)}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
