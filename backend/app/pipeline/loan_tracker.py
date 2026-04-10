"""
loan_tracker.py — Loan Tracker Schema & Utilisation Engine

Gap 2 Fix: Proper LoanTracker dataclass with all required fields.
Gap 3 Fix: Separate pure functions for WCDL, BC, and PQL utilisation.

All functions are pure — no side effects, fully testable.
"""

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Dict, List, Optional


# ── Custom Exceptions ─────────────────────────────────────────────────────────

class BankConfigMappingError(Exception):
    """
    Raised when a bank statement column expected by bank_config
    is not found in the extracted data.

    Example:
        raise BankConfigMappingError(
            "col_date 'Txn Date' not found in Axis Bank statement."
        )
    """
    pass


# ── Loan Tracker Dataclass ─────────────────────────────────────────────────────

@dataclass
class LoanTracker:
    """
    One row = one drawdown of a WCDL / BC / PQL facility.

    Fields tagged [stmt]   → fetched from bank statement (interest_as_per_bank)
    Fields tagged [manual] → entered once from sanction letter / loan advice
    Fields tagged [computed] → derived by the engine
    """

    # Identity
    loan_ref: str                          # e.g. "WCDL-001", "BC-2026-03-01"
    loan_type: str                         # "WCDL" | "BC" | "PQL"
    bank_name: str                         # "HDFC BANK", "UBI", etc.
    account_number: str                    # bank account this loan sits in

    # Tenor
    drawdown_date: date                    # [manual] date loan was disbursed
    maturity_date: date                    # [manual] original maturity date
    prepayment_date: Optional[date] = None # [manual] if prepaid early, overrides maturity

    # Financials
    principal_inr: float = 0.0            # [manual] principal in INR (BC uses INR equivalent at drawdown)
    loan_roi: float = 0.0                 # [manual] annual decimal (e.g. 0.0725)

    # Verification (filled after bank charges arrive)
    interest_as_per_bank: Optional[float] = None  # [stmt] actual interest debited by bank

    # BC-specific (Buyer's Credit from overseas bank)
    fc_amount: Optional[float] = None     # [manual] foreign currency amount
    fc_currency: Optional[str] = None     # [manual] "USD" | "EUR" | "GBP"
    exchange_rate_at_drawdown: Optional[float] = None  # [manual] rate locked at drawdown

    def effective_end_date(self) -> date:
        """
        The date the loan actually stopped accruing interest.
        If prepaid, use prepayment_date; otherwise maturity_date.
        """
        if self.prepayment_date:
            return min(self.maturity_date, self.prepayment_date)
        return self.maturity_date

    def actual_active_days_in_range(self, start: date, end: date) -> int:
        """
        Count days this loan was active within [start, end].
        Returns 0 if the loan period doesn't overlap the range.
        """
        effective_start = max(self.drawdown_date, start)
        effective_end   = min(self.effective_end_date(), end)
        delta = (effective_end - effective_start).days + 1
        return max(0, delta)

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert date objects to ISO strings for JSON serialisation
        for f in ("drawdown_date", "maturity_date", "prepayment_date"):
            if d[f] and not isinstance(d[f], str):
                d[f] = str(d[f])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "LoanTracker":
        def _to_date(v):
            if v is None:
                return None
            if isinstance(v, date):
                return v
            return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()

        return cls(
            loan_ref=d["loan_ref"],
            loan_type=d["loan_type"],
            bank_name=d["bank_name"],
            account_number=d["account_number"],
            drawdown_date=_to_date(d["drawdown_date"]),
            maturity_date=_to_date(d["maturity_date"]),
            prepayment_date=_to_date(d.get("prepayment_date")),
            principal_inr=float(d.get("principal_inr", 0)),
            loan_roi=float(d.get("loan_roi", 0)),
            interest_as_per_bank=d.get("interest_as_per_bank"),
            fc_amount=d.get("fc_amount"),
            fc_currency=d.get("fc_currency"),
            exchange_rate_at_drawdown=d.get("exchange_rate_at_drawdown"),
        )


# ── Pure Utilisation Functions ─────────────────────────────────────────────────

def get_wcdl_utilisation(
    loans: List[LoanTracker],
    date_range: List[date],
) -> Dict[date, float]:
    """
    For each calendar date in date_range, sum principal_inr of every
    WCDL loan that was active on that date.

    Active = drawdown_date ≤ date ≤ MIN(maturity_date, prepayment_date)

    Args:
        loans: list of LoanTracker (filter to loan_type == "WCDL" is done internally)
        date_range: list of date objects for the full statement period

    Returns:
        Dict[date, float] — daily WCDL utilisation in INR
    """
    wcdl_loans = [l for l in loans if l.loan_type == "WCDL"]
    daily: Dict[date, float] = {d: 0.0 for d in date_range}

    for loan in wcdl_loans:
        end = loan.effective_end_date()
        for d in date_range:
            if loan.drawdown_date <= d <= end:
                daily[d] += loan.principal_inr

    return daily


def get_bc_utilisation(
    loans: List[LoanTracker],
    date_range: List[date],
) -> Dict[date, float]:
    """
    Buyer's Credit (BC) utilisation per day.

    BC difference vs WCDL:
    - principal_inr = FC amount × exchange_rate AT DRAWDOWN (locked, does NOT reprice).
    - The INR equivalent is constant for the entire tenor.

    Args:
        loans: list of LoanTracker (filters to loan_type == "BC" internally)
        date_range: list of date objects

    Returns:
        Dict[date, float] — daily BC utilisation in INR (at drawdown rate)
    """
    bc_loans = [l for l in loans if l.loan_type == "BC"]
    daily: Dict[date, float] = {d: 0.0 for d in date_range}

    for loan in bc_loans:
        end = loan.effective_end_date()
        # Use principal_inr directly (already locked at drawdown exchange rate)
        inr_val = loan.principal_inr
        for d in date_range:
            if loan.drawdown_date <= d <= end:
                daily[d] += inr_val

    return daily


def get_pql_utilisation(
    loans: List[LoanTracker],
    date_range: List[date],
) -> Dict[date, float]:
    """
    Pre-Qualified Loan (PQL) utilisation per day.

    PQL is identical in calculation to WCDL (principal × active days / 365),
    with the only difference being it is a pre-approved sub-limit drawn faster.

    Args:
        loans: list of LoanTracker (filters to loan_type == "PQL" internally)
        date_range: list of date objects

    Returns:
        Dict[date, float] — daily PQL utilisation in INR
    """
    pql_loans = [l for l in loans if l.loan_type == "PQL"]
    daily: Dict[date, float] = {d: 0.0 for d in date_range}

    for loan in pql_loans:
        end = loan.effective_end_date()
        for d in date_range:
            if loan.drawdown_date <= d <= end:
                daily[d] += loan.principal_inr

    return daily


def calculate_loan_interest(loan: LoanTracker) -> Dict:
    """
    Calculate interest for a single loan (WCDL / BC / PQL).

    Formula: principal × roi × actual_days / 365
    Uses actual_days = drawdown_date to effective_end_date (inclusive).

    Args:
        loan: a LoanTracker instance

    Returns:
        dict with calculated_interest, effective_roi_annualised, diff_vs_bank
    """
    start = loan.drawdown_date
    end   = loan.effective_end_date()
    actual_days = (end - start).days + 1

    if actual_days <= 0 or loan.principal_inr <= 0:
        return {
            "loan_ref": loan.loan_ref,
            "loan_type": loan.loan_type,
            "principal_inr": loan.principal_inr,
            "actual_days": 0,
            "calculated_interest": 0.0,
            "effective_roi_annualised": 0.0,
            "diff_vs_bank": None,
        }

    # Interest = P × R × T / 365
    calculated_interest = (loan.principal_inr * loan.loan_roi * actual_days) / 365

    # Effective back-calculated ROI
    effective_roi = (
        (calculated_interest / loan.principal_inr) / actual_days * 365
        if loan.principal_inr > 0
        else 0.0
    )

    diff_vs_bank = None
    if loan.interest_as_per_bank is not None:
        diff_vs_bank = round(calculated_interest - loan.interest_as_per_bank, 2)

    return {
        "loan_ref": loan.loan_ref,
        "loan_type": loan.loan_type,
        "bank_name": loan.bank_name,
        "principal_inr": loan.principal_inr,
        "loan_roi": loan.loan_roi,
        "drawdown_date": str(loan.drawdown_date),
        "maturity_date": str(loan.maturity_date),
        "prepayment_date": str(loan.prepayment_date) if loan.prepayment_date else None,
        "actual_days": actual_days,
        "calculated_interest": round(calculated_interest, 2),
        "interest_as_per_bank": loan.interest_as_per_bank,
        "diff_vs_bank": diff_vs_bank,
        "diff_status": (
            "✓ MATCH" if diff_vs_bank is not None and abs(diff_vs_bank) <= 1
            else ("⚠ FLAG" if diff_vs_bank is not None else "PENDING")
        ),
        "effective_roi_annualised": round(effective_roi * 100, 4),
    }


def loans_from_wcdl_rows(rows: List[dict]) -> List[LoanTracker]:
    """
    Convert a list of raw dicts (from DB WCDLLoan table or pipeline input)
    to LoanTracker instances.

    Mapping from WCDLLoan DB schema:
        loanNumber    → loan_ref
        loan_type     → loan_type (defaults to "WCDL")
        bankName      → bank_name
        principalAmount → principal_inr
        roi           → loan_roi
        startDate     → drawdown_date
        maturityDate  → maturity_date
        prepaymentDate → prepayment_date
        interest_as_per_bank → interest_as_per_bank
    """

    def _to_date(v):
        if v is None:
            return None
        if isinstance(v, date):
            return v
        s = str(v)[:10]
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    trackers = []
    for row in rows:
        dd = _to_date(row.get("startDate") or row.get("drawdown_date"))
        md = _to_date(row.get("maturityDate") or row.get("maturity_date"))
        if not dd or not md:
            continue  # skip malformed rows

        trackers.append(LoanTracker(
            loan_ref=str(row.get("loanNumber") or row.get("loan_ref") or "LOAN-?"),
            loan_type=str(row.get("loan_type") or row.get("loanType") or "WCDL"),
            bank_name=str(row.get("bankName") or row.get("bank_name") or "UNKNOWN"),
            account_number=str(row.get("account_number") or ""),
            drawdown_date=dd,
            maturity_date=md,
            prepayment_date=_to_date(row.get("prepaymentDate") or row.get("prepayment_date")),
            principal_inr=float(row.get("principalAmount") or row.get("principal_inr") or 0),
            loan_roi=float(row.get("roi") or row.get("loan_roi") or 0),
            interest_as_per_bank=row.get("interest_as_per_bank"),
        ))

    return trackers
