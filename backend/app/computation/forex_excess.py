"""
Forex Excess Charge = FC Amount × (Bank Rate - Market Rate)
"""

from decimal import Decimal, ROUND_HALF_UP


def forex_excess_vs_avg(
    fc_amount: float,
    bank_rate: float,
    market_avg_rate: float,
) -> Decimal:
    """Excess (vs avg) = FC Amount × (Bank Rate - Market Avg Rate)"""
    fc = Decimal(str(fc_amount))
    br = Decimal(str(bank_rate))
    mkt = Decimal(str(market_avg_rate))
    return (fc * (br - mkt)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def forex_excess_vs_high(
    fc_amount: float,
    bank_rate: float,
    market_day_high: float,
) -> Decimal:
    """Excess (vs day high) = FC Amount × (Bank Rate - Day High)"""
    fc = Decimal(str(fc_amount))
    br = Decimal(str(bank_rate))
    high = Decimal(str(market_day_high))
    excess = fc * (br - high)
    return max(excess, Decimal("0")).quantize(Decimal("0.01"), ROUND_HALF_UP)
