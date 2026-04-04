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

from app.computation.cc_interest import (
    cc_daily_interest, cc_monthly_interest, get_repo_rate, get_cc_roi,
)
from app.computation.wcdl_interest import wcdl_interest, get_wcdl_roi
from app.computation.idle_loss import notional_interest_loss
from app.computation.finance_cost import finance_cost_pct
from app.computation.roi_verification import actual_roi, is_roi_overcharged
from app.computation.forex_excess import forex_excess_vs_avg, forex_excess_vs_high


class TestRepoRates:
    def test_before_any_cut(self):
        assert get_repo_rate(date(2025, 1, 1)) == Decimal("0.0650")

    def test_after_feb2025_cut(self):
        assert get_repo_rate(date(2025, 3, 1)) == Decimal("0.0625")

    def test_after_dec2025_cut(self):
        assert get_repo_rate(date(2026, 2, 1)) == Decimal("0.0525")

    def test_cc_roi_feb2026(self):
        assert get_cc_roi(date(2026, 2, 1)) == Decimal("0.0760")

    def test_wcdl_roi_feb2026(self):
        assert get_wcdl_roi(date(2026, 2, 1)) == Decimal("0.0725")


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
        assert abs(result - Decimal("0.0743")) <= Decimal("0.0001")

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
