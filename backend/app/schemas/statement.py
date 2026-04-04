from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class RunStatusEnum(str, Enum):
    PENDING = "PENDING"
    STAGE1_RUNNING = "STAGE1_RUNNING"
    STAGE1_REVIEW = "STAGE1_REVIEW"
    STAGE2_RUNNING = "STAGE2_RUNNING"
    STAGE3_RUNNING = "STAGE3_RUNNING"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    FAILED = "FAILED"


class PipelineRunRequest(BaseModel):
    org_id: str
    statement_month: str = Field(..., pattern=r"^\d{4}-\d{2}$", examples=["2026-02"])
    upload_ids: Optional[list[str]] = None
    pdf_s3_keys: Optional[list[str]] = None


class PipelineConfirmReviewRequest(BaseModel):
    run_id: str
    confirmed_fields: Optional[dict] = None


class PipelineApprovalRequest(BaseModel):
    run_id: str
    user_id: str


class PipelineRunResponse(BaseModel):
    run_id: str
    status: RunStatusEnum
    message: str


class PipelineStatusResponse(BaseModel):
    run_id: str
    status: RunStatusEnum
    stage: int
    statement_month: str
    statement_excel_key: Optional[str] = None
    working_sheet_key: Optional[str] = None
    banking_report_key: Optional[str] = None
    validation_result: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    review_fields: Optional[list[dict]] = None


class PipelineRunListItem(BaseModel):
    run_id: str
    statement_month: str
    status: RunStatusEnum
    stage: int
    upload_count: int
    statement_excel_key: Optional[str] = None
    working_sheet_key: Optional[str] = None
    banking_report_key: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class DownloadURLResponse(BaseModel):
    url: str
    expires_in_seconds: int = 900
