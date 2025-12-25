"""Main API router"""

from fastapi import APIRouter
from app.api.endpoints import auth, users, plaid

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(plaid.router, prefix="/plaid", tags=["plaid"])
