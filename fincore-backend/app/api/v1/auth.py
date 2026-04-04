"""
POST /auth/verify-token
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/verify-token")
async def verify_token():
    """Verify Firebase auth token. Placeholder for now."""
    return {
        "uid": "dev-user",
        "email": "dev@fincore.local",
        "name": "Dev User",
        "role": "ADMIN",
    }
