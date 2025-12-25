"""User schemas"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID


class UserBase(BaseModel):
    """Base user schema"""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a user"""

    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema for updating a user"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    notification_preferences: Optional[Dict[str, Any]] = None


class UserInDB(UserBase):
    """Schema for user in database (includes hashed password)"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    password_hash: str
    is_active: bool
    is_verified: bool
    notification_preferences: Dict[str, Any]
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class User(UserBase):
    """Schema for user response (public data)"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    is_verified: bool
    notification_preferences: Dict[str, Any]
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime
