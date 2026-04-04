"""
Actual ROI = (Interest Charged / Principal) / Tenure_Days × 365

VERIFIED:
    WCDL-1: (1191781 / 300000000) / 20 × 365 = 7.25% MATCH
"""

from decimal import Decimal, ROUND_HALF_UP


def actual_roi(
    interest_charged: float,
    principal: float,
    tenure_days: int,
) -> Decimal:
    """Actual ROI = (Interest Charged / Principal) / Tenure_Days × 365"""
    i = Decimal(str(interest_charged))
    p = Decimal(str(principal))
    t = Decimal(str(tenure_days))
    if p == 0 or t == 0:
        return Decimal("0")
    return ((i / p) / t * Decimal("365")).quantize(
        Decimal("0.0001"), ROUND_HALF_UP
    )


def is_roi_overcharged(
    actual: Decimal,
    sanctioned: Decimal,
    tolerance_bps: int = 5,
) -> bool:
    """Returns True if actual ROI exceeds sanctioned by more than tolerance."""
    tolerance = Decimal(str(tolerance_bps)) / Decimal("10000")
    return actual > (sanctioned + tolerance)
