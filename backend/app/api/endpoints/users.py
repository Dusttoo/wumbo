"""User endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import User as UserSchema, UserUpdate
from app.services.user_service import UserService
from app.api.deps.auth import get_current_active_user
from app.models.user import User

router = APIRouter()


@router.get("/me", response_model=UserSchema)
def get_current_user_info(current_user: User = Depends(get_current_active_user)) -> UserSchema:
    """
    Get current user information

    Args:
        current_user: Current authenticated user

    Returns:
        Current user data
    """
    return current_user


@router.put("/me", response_model=UserSchema)
def update_current_user(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UserSchema:
    """
    Update current user information

    Args:
        user_in: User update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user
    """
    user = UserService.update(db, current_user, user_in)
    return user


@router.get("/{user_id}", response_model=UserSchema)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserSchema:
    """
    Get user by ID

    Args:
        user_id: User ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        User data

    Raises:
        HTTPException: If user not found
    """
    user = UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
