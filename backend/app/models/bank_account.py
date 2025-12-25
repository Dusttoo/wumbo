"""Bank account models"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Numeric, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base
from app.core.encryption import EncryptionService


class EncryptedString(TypeDecorator):
    """SQLAlchemy column type for encrypted strings using Fernet"""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt value before storing in database"""
        if value is not None:
            return EncryptionService.encrypt(value)
        return value

    def process_result_value(self, value, dialect):
        """Decrypt value when loading from database"""
        if value is not None:
            return EncryptionService.decrypt(value)
        return value


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id = Column(UUID(as_uuid=True), ForeignKey("households.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Plaid identifiers
    plaid_account_id = Column(String(255), unique=True, nullable=False, index=True)
    plaid_item_id = Column(String(255), nullable=False, index=True)
    plaid_access_token = Column(EncryptedString(500), nullable=False)  # Automatically encrypted with Fernet
    plaid_cursor = Column(String(500), nullable=True)  # For transaction sync

    # Account details
    name = Column(String(255), nullable=False)
    official_name = Column(String(255), nullable=True)
    mask = Column(String(10), nullable=True)  # Last 4 digits
    account_type = Column(String(50), nullable=True)  # depository, credit, loan, etc.
    account_subtype = Column(String(50), nullable=True)  # checking, savings, credit card, etc.

    # Balances
    current_balance = Column(Numeric(precision=15, scale=2), nullable=True)
    available_balance = Column(Numeric(precision=15, scale=2), nullable=True)
    currency_code = Column(String(3), default="USD", nullable=False)

    # Settings
    include_in_budget = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Sync tracking
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_error = Column(String(500), nullable=True)

    # Additional data
    additional_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    household = relationship("Household", back_populates="bank_accounts")
    user = relationship("User", back_populates="bank_accounts")
    transactions = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<BankAccount {self.name} ({self.mask})>"
