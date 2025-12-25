"""Transaction schemas"""

from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class TransactionBase(BaseModel):
    """Base transaction schema"""

    amount: Decimal
    date: date
    name: str
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction"""

    account_id: UUID
    category_id: Optional[UUID] = None
    merchant_name: Optional[str] = None
    is_manual: bool = True


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction"""

    category_id: Optional[UUID] = None
    notes: Optional[str] = None


class Transaction(TransactionBase):
    """Schema for transaction response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    household_id: UUID
    plaid_transaction_id: Optional[str]
    merchant_name: Optional[str]
    category_id: Optional[UUID]
    plaid_category: Optional[str]
    payment_channel: Optional[str]
    pending: bool
    is_manual: bool
    created_at: datetime
    updated_at: datetime
