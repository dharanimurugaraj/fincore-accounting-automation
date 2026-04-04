"""
Finance Cost % = (Total Monthly Interest / Avg Utilisation) × 12

VERIFIED (Feb 2026): 7.43% p.a.
"""

from decimal import Decimal, ROUND_HALF_UP


def finance_cost_pct(
    total_monthly_interest: float,
    avg_utilisation: float,
) -> Decimal:
    """Finance Cost % = (Total Monthly Interest / Avg Utilisation) × 12"""
    if avg_utilisation == 0:
        return Decimal("0")
    interest = Decimal(str(total_monthly_interest))
    util = Decimal(str(avg_utilisation))
    return ((interest / util) * Decimal("12")).quantize(
        Decimal("0.0001"), ROUND_HALF_UP
    )
