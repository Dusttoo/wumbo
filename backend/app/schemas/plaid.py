"""Plaid-specific schemas"""

from typing import Optional, List
from pydantic import BaseModel


class PlaidLinkTokenRequest(BaseModel):
    """Request to create a Plaid Link token"""

    products: Optional[List[str]] = None
    webhook: Optional[str] = None


class PlaidLinkTokenResponse(BaseModel):
    """Response with Plaid Link token"""

    link_token: str
    expiration: str


class PlaidPublicTokenExchangeRequest(BaseModel):
    """Request to exchange public token"""

    public_token: str
    household_id: str


class PlaidPublicTokenExchangeResponse(BaseModel):
    """Response after exchanging public token"""

    accounts_added: int
    item_id: str


class PlaidWebhookRequest(BaseModel):
    """Plaid webhook payload"""

    webhook_type: str
    webhook_code: str
    item_id: str
    error: Optional[dict] = None


class PlaidAccountSyncRequest(BaseModel):
    """Request to sync a specific account"""

    account_id: str


class PlaidAccountSyncResponse(BaseModel):
    """Response after syncing account"""

    transactions_added: int
    transactions_modified: int
    transactions_removed: int
    last_synced_at: str
