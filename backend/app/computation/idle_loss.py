"""
Notional Interest Loss = Avg Positive Balance × CC ROI × No. of Days / 365

VERIFIED:
    UBI Feb 2026: 1,068,662.63 × 0.0760 × 28 / 365 = Rs.6,199.21
"""

from decimal import Decimal, ROUND_HALF_UP


def notional_interest_loss(
    avg_positive_balance: float,
    days_with_balance: int,
    cc_roi: float,
) -> Decimal:
    """Interest Loss = Avg Positive Balance × CC ROI × No. of Days / 365"""
    bal = Decimal(str(avg_positive_balance))
    days = Decimal(str(days_with_balance))
    roi = Decimal(str(cc_roi))
    return (bal * roi * days / Decimal("365")).quantize(Decimal("0.01"), ROUND_HALF_UP)
