"""Household schemas"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from app.models.household import HouseholdRole


class HouseholdBase(BaseModel):
    """Base household schema"""

    name: str = Field(..., min_length=1, max_length=255)


class HouseholdCreate(HouseholdBase):
    """Schema for creating a household"""

    pass


class HouseholdUpdate(BaseModel):
    """Schema for updating a household"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    settings: Optional[Dict[str, Any]] = None


class HouseholdMemberBase(BaseModel):
    """Base household member schema"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    user_id: UUID
    role: HouseholdRole
    invited_at: datetime
    joined_at: Optional[datetime]


class HouseholdMember(HouseholdMemberBase):
    """Schema for household member response"""

    permissions: Dict[str, Any]


class Household(HouseholdBase):
    """Schema for household response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    members: Optional[List[HouseholdMember]] = None
