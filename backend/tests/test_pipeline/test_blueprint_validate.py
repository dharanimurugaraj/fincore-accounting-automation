import pytest

from app.pipeline.bank_schema import BankSchema
from app.pipeline.pipeline_exceptions import BankConfigMappingError
from app.pipeline.working_sheet import (
    _last_row_index_by_date,
    _positive_bal_num_days_cc,
)


def test_validate_raises_when_balance_col_blank():
    s = BankSchema(balance_col_name=" ", column_layout="debit_credit_balance")
    with pytest.raises(BankConfigMappingError) as e:
        s.validate_blueprint_for_extraction()
    assert e.value.field == "balance_col_name"


def test_positive_bal_zero_when_marker_says_od_even_if_cb_positive():
    """Explicit OD side from balance cell → Positive Bal 0 (sheet logic)."""
    pos, days, cc = _positive_bal_num_days_cc(1180.0, "marker_inline", False)
    assert pos == 0.0
    assert days == 0
    assert cc == 1180.0


def test_positive_bal_from_cr_marker():
    pos, days, cc = _positive_bal_num_days_cc(94_029_531.30, "marker_inline", True)
    assert pos == pytest.approx(94_029_531.30)
    assert days == 1
    assert cc == 0.0


def test_last_row_index_per_date():
    rows = [
        {"date": "2026-02-02"},
        {"date": "2026-02-02"},
        {"date": "2026-02-02"},
        {"date": "2026-02-03"},
    ]
    m = _last_row_index_by_date(rows)
    assert m["2026-02-02"] == 2
    assert m["2026-02-03"] == 3


def test_signed_style_uses_numeric_sign():
    pos, days, _ = _positive_bal_num_days_cc(-100.0, "signed", None)
    assert pos == 0.0
    assert days == 0
    pos2, days2, _ = _positive_bal_num_days_cc(50.0, "signed", True)
    assert pos2 == 50.0
    assert days2 == 1
