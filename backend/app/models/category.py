"""Category models"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from app.db.base import Base


class CategoryType(str, enum.Enum):
    """Category types"""

    INCOME = "income"
    EXPENSE = "expense"


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id = Column(UUID(as_uuid=True), ForeignKey("households.id"), nullable=True)

    # Category details
    name = Column(String(255), nullable=False)
    type = Column(Enum(CategoryType), default=CategoryType.EXPENSE, nullable=False)
    color = Column(String(7), nullable=True)  # Hex color code
    icon = Column(String(50), nullable=True)  # Icon identifier

    # Hierarchy
    parent_category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)

    # System categories vs user-created
    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    household = relationship("Household", back_populates="categories")
    parent_category = relationship("Category", remote_side=[id], backref="subcategories")
    transactions = relationship("Transaction", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.name} ({self.type})>"
