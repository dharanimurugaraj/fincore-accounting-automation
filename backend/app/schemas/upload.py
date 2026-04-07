from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UploadStatusEnum(str, Enum):
    UPLOADED = "UPLOADED"
    OCR_RUNNING = "OCR_RUNNING"
    OCR_COMPLETE = "OCR_COMPLETE"
    OCR_FAILED = "OCR_FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    LOCKED = "LOCKED"


class UploadCompleteRequest(BaseModel):
    org_id: str
    uploaded_by_id: str
    filename: str
    s3_key: str
    bank_name: str
    account_type: str
    account_id: str
    statement_month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    file_size_bytes: int


class UploadResponse(BaseModel):
    id: str
    filename: str
    s3_key: str
    bank_name: str
    account_type: str
    account_id: str
    statement_month: str
    status: UploadStatusEnum
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[UploadResponse]
    total: int
