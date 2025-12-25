"""Plaid integration endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.bank_account import BankAccount
from app.api.deps.auth import get_current_active_user
from app.core.webhook_verification import verify_plaid_webhook_signature
from app.schemas.plaid import (
    PlaidLinkTokenRequest,
    PlaidLinkTokenResponse,
    PlaidPublicTokenExchangeRequest,
    PlaidPublicTokenExchangeResponse,
    PlaidWebhookRequest,
    PlaidAccountSyncRequest,
    PlaidAccountSyncResponse,
)
from app.schemas.bank_account import BankAccount as BankAccountSchema
from app.services.plaid_service import PlaidService
from app.tasks.plaid_tasks import sync_account_transactions as sync_account_task
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


@router.post("/link/token", response_model=PlaidLinkTokenResponse)
def create_link_token(
    request: PlaidLinkTokenRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PlaidLinkTokenResponse:
    """
    Create a Plaid Link token for connecting bank accounts

    Args:
        request: Link token request parameters
        current_user: Current authenticated user
        db: Database session

    Returns:
        Link token and expiration
    """
    # Build webhook URL if configured
    webhook = None
    if settings.API_V1_PREFIX and request.webhook:
        webhook = f"{settings.API_V1_PREFIX}/plaid/webhook"

    result = PlaidService.create_link_token(db, current_user, webhook)
    return PlaidLinkTokenResponse(**result)


@router.post("/link/exchange", response_model=PlaidPublicTokenExchangeResponse)
def exchange_public_token(
    request: PlaidPublicTokenExchangeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PlaidPublicTokenExchangeResponse:
    """
    Exchange public token for access token and save accounts

    Args:
        request: Public token exchange request
        background_tasks: Background task manager
        current_user: Current authenticated user
        db: Database session

    Returns:
        Exchange result with accounts added
    """
    try:
        accounts_added = PlaidService.exchange_public_token_and_save_accounts(
            db=db,
            user=current_user,
            household_id=request.household_id,
            public_token=request.public_token,
        )

        # Queue initial transaction sync for all new accounts
        accounts = (
            db.query(BankAccount)
            .filter(
                BankAccount.household_id == request.household_id,
                BankAccount.user_id == current_user.id,
            )
            .order_by(BankAccount.created_at.desc())
            .limit(accounts_added)
            .all()
        )

        for account in accounts:
            background_tasks.add_task(sync_account_task.delay, str(account.id))

        return PlaidPublicTokenExchangeResponse(
            accounts_added=accounts_added,
            item_id=accounts[0].plaid_item_id if accounts else "",
        )

    except Exception as e:
        logger.error(f"Failed to exchange public token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect bank account: {str(e)}",
        )


@router.post("/accounts/{account_id}/sync", response_model=PlaidAccountSyncResponse)
def sync_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PlaidAccountSyncResponse:
    """
    Manually trigger transaction sync for an account

    Args:
        account_id: Bank account ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Sync result
    """
    # Verify user has access to this account
    account = (
        db.query(BankAccount)
        .filter(BankAccount.id == account_id, BankAccount.user_id == current_user.id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    try:
        result = PlaidService.sync_account_transactions(db, account_id)

        return PlaidAccountSyncResponse(
            transactions_added=result["added"],
            transactions_modified=result["modified"],
            transactions_removed=result["removed"],
            last_synced_at=account.last_synced_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to sync account {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to sync transactions: {str(e)}",
        )


@router.get("/accounts", response_model=List[BankAccountSchema])
def list_bank_accounts(
    household_id: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[BankAccountSchema]:
    """
    List bank accounts for current user

    Args:
        household_id: Optional household ID filter
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of bank accounts
    """
    query = db.query(BankAccount).filter(BankAccount.user_id == current_user.id)

    if household_id:
        query = query.filter(BankAccount.household_id == household_id)

    accounts = query.order_by(BankAccount.created_at.desc()).all()
    return accounts


@router.delete("/accounts/{account_id}")
def remove_bank_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Remove a bank account

    Args:
        account_id: Bank account ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message
    """
    # Verify user has access
    account = (
        db.query(BankAccount)
        .filter(BankAccount.id == account_id, BankAccount.user_id == current_user.id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    try:
        PlaidService.remove_account(db, account_id)
        return {"message": "Account removed successfully"}

    except Exception as e:
        logger.error(f"Failed to remove account {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to remove account: {str(e)}",
        )


@router.post("/webhook", dependencies=[Depends(verify_plaid_webhook_signature)])
async def plaid_webhook(
    webhook_data: PlaidWebhookRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Handle Plaid webhook events with signature verification

    Webhooks are verified using the Plaid-Verification header which contains
    a JWT with the request body hash. This prevents unauthorized webhook calls.

    Args:
        webhook_data: Webhook payload from Plaid
        db: Database session

    Returns:
        Acknowledgment

    Raises:
        HTTPException: If webhook signature verification fails
    """
    logger.info(
        f"Received verified Plaid webhook: {webhook_data.webhook_type}.{webhook_data.webhook_code}"
    )

    # Queue webhook processing
    from app.tasks.plaid_tasks import handle_plaid_webhook

    handle_plaid_webhook.delay(
        webhook_type=webhook_data.webhook_type,
        webhook_code=webhook_data.webhook_code,
        item_id=webhook_data.item_id,
    )

    return {"status": "received"}
