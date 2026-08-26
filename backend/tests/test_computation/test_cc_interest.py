"""
Unit tests for the FinCore computation engine.
All values verified against client's Feb-2026 Excel files.
"""

import pytest
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date

# Ensure app package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipeline.engine import FinCoreComputationEngine

engine = FinCoreComputationEngine()

def get_repo_rate(d: date) -> Decimal:
    if d < date(2025, 2, 1):
        return Decimal("0.0650")
    elif d < date(2025, 12, 1):
        return Decimal("0.0625")
    return Decimal("0.0525")

def get_cc_roi(d: date) -> Decimal:
    return Decimal("0.0760")

def get_wcdl_roi(d: date) -> Decimal:
    return Decimal("0.0725")

def cc_daily_interest(balance: float, roi_percent: float, date_obj: date = None) -> Decimal:
    roi = roi_percent * 100 if roi_percent < 1 else roi_percent
    val = engine.compute_cc_daily_interest(-abs(balance) if balance > 0 else balance, roi)
    return Decimal(str(round(val, 2)))

def wcdl_interest(principal: float, roi_percent: float, tenure_days: int) -> Decimal:
    roi = roi_percent * 100 if roi_percent < 1 else roi_percent
    val = engine.compute_wcdl_interest(principal, roi, tenure_days)
    return Decimal(str(round(val, 2)))

def notional_interest_loss(avg_positive_balance: float, days: int, roi_percent: float) -> Decimal:
    roi = roi_percent * 100 if roi_percent < 1 else roi_percent
    daily_balances = [avg_positive_balance] * days
    val = engine.compute_notional_interest_loss(daily_balances, roi)
    return Decimal(str(round(val, 2)))

def finance_cost_pct(total_interest: float, avg_utilisation: float) -> Decimal:
    val = engine.compute_finance_cost_percent(total_interest, avg_utilisation, 30)
    return Decimal(str(round(val / 100, 4)))

def actual_roi(interest_charged: float, principal: float, tenure_days: int) -> Decimal:
    val = engine.verify_actual_roi(interest_charged, principal, tenure_days)
    return Decimal(str(round(val / 100, 4)))

def is_roi_overcharged(actual: Decimal, sanctioned: Decimal) -> bool:
    return actual > sanctioned

def forex_excess_vs_avg(qty: float, actual_rate: float, avg_rate: float) -> Decimal:
    diff = max(0.0, actual_rate - avg_rate)
    return Decimal(str(round(qty * diff, 2)))

def forex_excess_vs_high(qty: float, actual_rate: float, high_rate: float) -> Decimal:
    diff = max(0.0, actual_rate - high_rate)
    return Decimal(str(round(qty * diff, 2)))


class TestCCDailyInterest:
    def test_hdfc521_01feb2026(self):
        result = cc_daily_interest(138425196.92, 0.0760, date(2026, 2, 1))
        assert result == Decimal("28822.78"), f"Got {result}"

    def test_zero_balance(self):
        assert cc_daily_interest(0, 0.0760, date(2026, 2, 1)) == Decimal("0.00")

    def test_small_balance(self):
        result = cc_daily_interest(100000, 0.0760, date(2026, 2, 1))
        assert result == Decimal("20.82"), f"Got {result}"


class TestWCDLInterest:
    def test_loan1_full_tenure(self):
        result = wcdl_interest(300000000, 0.0725, 60)
        assert result == Decimal("3575342.47"), f"Got {result}"

    def test_loan2_feb_portion(self):
        result = wcdl_interest(250000000, 0.0725, 28)
        assert abs(result - Decimal("1390411")) <= Decimal("1")

    def test_loan3_8_days(self):
        result = wcdl_interest(300000000, 0.0725, 8)
        assert abs(result - Decimal("476712")) <= Decimal("1")

    def test_zero_principal(self):
        assert wcdl_interest(0, 0.0725, 30) == Decimal("0.00")


class TestNotionalInterestLoss:
    def test_ubi_feb2026(self):
        result = notional_interest_loss(1068662.632857143, 28, 0.0760)
        assert abs(result - Decimal("6230.45")) <= Decimal("1")

    def test_zero_balance(self):
        assert notional_interest_loss(0, 28, 0.0760) == Decimal("0.00")


class TestFinanceCost:
    def test_feb2026(self):
        result = finance_cost_pct(3571109, 576526656.28)
        assert abs(result - Decimal("0.0754")) <= Decimal("0.0001")

    def test_zero_utilisation(self):
        assert finance_cost_pct(100000, 0) == Decimal("0")


class TestActualROI:
    def test_wcdl1_matches_sanctioned(self):
        result = actual_roi(1191781, 300000000, 20)
        assert abs(result - Decimal("0.0725")) <= Decimal("0.0001")
        assert not is_roi_overcharged(result, Decimal("0.0725"))

    def test_ecl_flagged(self):
        result = actual_roi(106122, 13188092, 28)
        assert result > Decimal("0.0830")
        assert is_roi_overcharged(result, Decimal("0.0830"))


class TestForexExcess:
    def test_known_transaction(self):
        result = forex_excess_vs_avg(6267, 101.75, 101.20)
        assert result == Decimal("3446.85")

    def test_vs_high_overcharge(self):
        result = forex_excess_vs_high(10000, 91.50, 91.00)
        assert result == Decimal("5000.00")

    def test_vs_high_no_overcharge(self):
        result = forex_excess_vs_high(10000, 90.80, 91.00)
        assert result == Decimal("0.00")
