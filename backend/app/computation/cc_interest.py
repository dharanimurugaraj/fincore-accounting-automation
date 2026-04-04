"""
CC Daily Interest = abs(Closing Balance) × ROI / 365

VERIFIED: HDFC-521, 01-Feb-2026
    balance = 138,425,196.92, roi = 0.0760
    result = 138425196.92 × 0.0760 / 365 = Rs.28,822.78
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date

# ── REPO RATE HISTORY ─────────────────────────────────────────────────────────

REPO_RATES = [
    (date(2025, 2, 7),  Decimal("0.0625")),   # 6.25%
    (date(2025, 4, 9),  Decimal("0.0600")),   # 6.00%
    (date(2025, 6, 6),  Decimal("0.0550")),   # 5.50%
    (date(2025, 12, 5), Decimal("0.0525")),   # 5.25% — current
]

CC_SPREAD = Decimal("0.0235")   # CC ROI = Repo + 2.35%


def get_repo_rate(as_of: date) -> Decimal:
    """Return the applicable Repo rate for a given date."""
    rate = Decimal("0.0650")  # default before first cut
    for effective_date, r in REPO_RATES:
        if as_of >= effective_date:
            rate = r
    return rate


def get_cc_roi(as_of: date) -> Decimal:
    """CC ROI = Repo Rate + 2.35% spread."""
    return get_repo_rate(as_of) + CC_SPREAD


def cc_daily_interest(closing_balance: float, roi: float, date_: date) -> Decimal:
    """CC Daily Interest = abs(Closing Balance) × ROI / 365"""
    bal = Decimal(str(abs(closing_balance)))
    r = Decimal(str(roi))
    return (bal * r / Decimal("365")).quantize(Decimal("0.01"), ROUND_HALF_UP)


def cc_monthly_interest(daily_balances: list[dict], roi: float) -> Decimal:
    """Sum of daily interests for all days in the month.

    VERIFIED: HDFC-521 Feb 2026 = Rs.5,07,432 (within Rs.1 of bank statement)
    """
    total = Decimal("0")
    for row in daily_balances:
        total += cc_daily_interest(row["balance"], roi, row["date"])
    return total.quantize(Decimal("0.01"), ROUND_HALF_UP)
