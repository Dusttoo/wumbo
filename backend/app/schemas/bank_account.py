"""Bank account schemas"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class BankAccountBase(BaseModel):
    """Base bank account schema"""

    name: str
    include_in_budget: bool = True


class BankAccountCreate(BaseModel):
    """Schema for creating a bank account (internal use)"""

    household_id: UUID
    user_id: UUID
    plaid_account_id: str
    plaid_item_id: str
    plaid_access_token: str
    name: str
    official_name: Optional[str] = None
    mask: Optional[str] = None
    account_type: Optional[str] = None
    account_subtype: Optional[str] = None
    current_balance: Optional[Decimal] = None
    available_balance: Optional[Decimal] = None


class BankAccountUpdate(BaseModel):
    """Schema for updating a bank account"""

    name: Optional[str] = None
    include_in_budget: Optional[bool] = None


class BankAccount(BaseModel):
    """Schema for bank account response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    user_id: UUID
    plaid_account_id: str
    name: str
    official_name: Optional[str]
    mask: Optional[str]
    account_type: Optional[str]
    account_subtype: Optional[str]
    current_balance: Optional[Decimal]
    available_balance: Optional[Decimal]
    currency_code: str
    include_in_budget: bool
    is_active: bool
    last_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
