"""
Shared API dependencies.
"""

from typing import Annotated, Dict
from fastapi import Path, Query, Depends

from app.core.security import get_current_user

# Current User Dependency
CurrentUser = Annotated[Dict, Depends(get_current_user)]

# Common Pagination
class Pagination:
    def __init__(self, limit: int = 20, offset: int = 0):
        self.limit = limit
        self.offset = offset
