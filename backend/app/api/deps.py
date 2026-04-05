"""
Shared API dependencies.
"""

from typing import Annotated, Dict
from fastapi import Path, Query, Depends, HTTPException

from app.core.security import get_current_user

# Current User Dependency
CurrentUser = Annotated[Dict, Depends(get_current_user)]

def ensure_admin(user: CurrentUser):
    """Allow Admin (1) or Super Admin (0)."""
    if user.get("role_id") not in [0, 1]:
        raise HTTPException(status_code=403, detail="Admin permissions required")
    return user

def ensure_super_admin(user: CurrentUser):
    """Allow only Super Admin (0)."""
    if user.get("role_id") != 0:
        raise HTTPException(status_code=403, detail="Super Admin permissions required")
    return user

AdminUser = Annotated[Dict, Depends(ensure_admin)]
SuperAdminUser = Annotated[Dict, Depends(ensure_super_admin)]

# Common Pagination
class Pagination:
    def __init__(self, limit: int = 20, offset: int = 0):
        self.limit = limit
        self.offset = offset
