from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    org_id: str
    user_id: str
    session_id: str
    message: str
    statement_month: Optional[str] = None
    model: Optional[str] = "gemini"


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    model: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    created_at: datetime


class ChatResponse(BaseModel):
    message: ChatMessageResponse
    session_id: str
    total_session_cost_usd: float


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageResponse]
    total_cost_usd: float
