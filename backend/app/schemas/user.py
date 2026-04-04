from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class UserCreate(BaseModel):
    email: str
    name: Optional[str] = None
    role: RoleEnum = RoleEnum.ANALYST
    org_id: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    role: RoleEnum
    org_id: str
    created_at: datetime
