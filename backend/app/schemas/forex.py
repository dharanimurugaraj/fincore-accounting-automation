from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class ForexTransactionResponse(BaseModel):
    id: str
    org_id: str
    run_id: Optional[str] = None
    statement_month: str
    sr_no: Optional[int] = None
    boe_date: Optional[date] = None
    value_date: Optional[date] = None
    drawer_name: Optional[str] = None
    bill_reference: Optional[str] = None
    currency: Optional[str] = None
    fc_amount: Optional[float] = None
    bank_rate: Optional[float] = None
    market_avg_rate: Optional[float] = None
    day_high_rate: Optional[float] = None
    excess_vs_avg: Optional[float] = None
    excess_vs_high: Optional[float] = None
    bill_amt_inr: Optional[float] = None
    bill_commission: Optional[float] = None
    swift_charges: Optional[float] = None
    total_amt_inr: Optional[float] = None
    created_at: datetime


class ForexCurrencySummary(BaseModel):
    currency: str
    transaction_count: int
    total_fc_amount: float
    total_inr: float
    total_excess_vs_avg: float
    avg_bank_rate: float
    avg_market_rate: float


class ForexMonthlySummary(BaseModel):
    statement_month: str
    total_transactions: int
    total_inr_value: float
    total_excess_charges: float
    by_currency: list[ForexCurrencySummary]


class ForexListResponse(BaseModel):
    transactions: list[ForexTransactionResponse]
    monthly_summary: ForexMonthlySummary
    ytd_excess_charges: float
    total: int
