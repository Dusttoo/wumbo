"""Transaction models"""

from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Numeric, Date, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=False)
    household_id = Column(UUID(as_uuid=True), ForeignKey("households.id"), nullable=False)

    # Plaid identifier
    plaid_transaction_id = Column(String(255), unique=True, nullable=True, index=True)

    # Transaction details
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    date = Column(Date, nullable=False)
    authorized_date = Column(Date, nullable=True)
    name = Column(String(500), nullable=False)
    merchant_name = Column(String(255), nullable=True)

    # Categorization
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    plaid_category = Column(String(255), nullable=True)  # Plaid's category
    plaid_category_id = Column(String(50), nullable=True)

    # Payment details
    payment_channel = Column(String(50), nullable=True)  # online, in store, etc.
    payment_meta = Column(Text, nullable=True)  # JSON stored as text

    # Status
    pending = Column(Boolean, default=False, nullable=False)
    is_manual = Column(Boolean, default=False, nullable=False)  # Manual vs Plaid

    # User notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    account = relationship("BankAccount", back_populates="transactions")
    household = relationship("Household", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_transaction_household_date", "household_id", "date"),
        Index("idx_transaction_account_date", "account_id", "date"),
        Index("idx_transaction_category", "category_id"),
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.name} ${self.amount} on {self.date}>"
