"""
POST /auth/verify-token, GET /auth/me
"""

from fastapi import APIRouter
from app.api.deps import CurrentUser

router = APIRouter()

@router.get("/me")
async def get_me(user: CurrentUser):
    """Return the current user's DB profile including role."""
    return user

@router.post("/verify-token")
async def verify_token(user: CurrentUser):
    """Verify Firebase auth token and return internal profile."""
    return user
