from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AuditLogEntry(BaseModel):
    id: str
    org_id: str
    user_id: str
    user_email: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    metadata: Optional[dict] = None
    created_at: datetime


class AuditLogResponse(BaseModel):
    entries: list[AuditLogEntry]
    total: int


class AIUsageEntry(BaseModel):
    id: str
    org_id: str
    user_id: str
    user_email: Optional[str] = None
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    action: Optional[str] = None
    session_id: Optional[str] = None
    created_at: datetime


class AIUsageSummary(BaseModel):
    total_queries: int
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: float
    by_model: dict
    by_user: list[dict]


class AIUsageResponse(BaseModel):
    entries: list[AIUsageEntry]
    summary: AIUsageSummary
    total: int


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    photo_url: Optional[str] = None
    role: str
    org_id: str
    last_login: Optional[datetime] = None
    created_at: datetime


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


class UserRoleUpdateRequest(BaseModel):
    role: str


class UserInviteRequest(BaseModel):
    email: str
    role: str = "ANALYST"
    name: Optional[str] = None
