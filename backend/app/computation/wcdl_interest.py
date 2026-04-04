"""
WCDL Interest = Principal × ROI × Tenure_Days / 365

VERIFIED:
    Loan 240LN01253580014: 300000000 × 0.0725 × 60 / 365 = Rs.35,75,342.47
    Loan 240LN01260280020: 250000000 × 0.0725 × 28 / 365 = Rs.13,90,411
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from app.computation.cc_interest import get_repo_rate

WCDL_SPREAD = Decimal("0.0200")   # WCDL ROI = Repo + 2.00%


def get_wcdl_roi(as_of: date) -> Decimal:
    """WCDL ROI = Repo Rate + 2.00% spread."""
    return get_repo_rate(as_of) + WCDL_SPREAD


def wcdl_interest(principal: float, roi: float, tenure_days: int) -> Decimal:
    """WCDL Interest = Principal × ROI × Tenure_Days / 365"""
    p = Decimal(str(principal))
    r = Decimal(str(roi))
    t = Decimal(str(tenure_days))
    return (p * r * t / Decimal("365")).quantize(Decimal("0.01"), ROUND_HALF_UP)
