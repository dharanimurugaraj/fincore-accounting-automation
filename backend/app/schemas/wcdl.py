from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class WCDLLoanCreate(BaseModel):
    loan_number: str
    start_date: date
    maturity_date: date
    prepayment_date: Optional[date] = None
    principal: float
    roi: float
    tenure_days: Optional[int] = None
    computed_interest: Optional[float] = None
    bank_stated_interest: Optional[float] = None
    actual_roi: Optional[float] = None
    status: str = "ACTIVE"


class WCDLLoanResponse(BaseModel):
    id: str
    org_id: str
    run_id: Optional[str] = None
    statement_month: str
    loan_number: str
    start_date: date
    maturity_date: date
    prepayment_date: Optional[date] = None
    principal: float
    roi: float
    tenure_days: Optional[int] = None
    computed_interest: Optional[float] = None
    bank_stated_interest: Optional[float] = None
    actual_roi: Optional[float] = None
    status: str
    days_to_maturity: Optional[int] = None
    created_at: datetime


class WCDLSummary(BaseModel):
    total_loans: int
    active_loans: int
    closed_loans: int
    total_principal: float
    total_computed_interest: float
    total_bank_stated_interest: float
    maturing_within_15_days: list[WCDLLoanResponse]


class WCDLListResponse(BaseModel):
    loans: list[WCDLLoanResponse]
    summary: WCDLSummary
    total: int
