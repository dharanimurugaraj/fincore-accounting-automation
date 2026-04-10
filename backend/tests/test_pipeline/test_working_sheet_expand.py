"""Calendar expansion for working sheet — bank-agnostic."""

from app.pipeline.working_sheet import _expand_to_full_month


def test_expand_no_duplicate_opening_row_early_gaps_are_green_flags():
    txns = [
        {
            "date": "2026-02-03",
            "narration": "NEFT",
            "ref_number": "",
            "withdrawal": 100.0,
            "deposit": 0.0,
            "closing_balance": 900.0,
        }
    ]
    out = _expand_to_full_month(txns, "2026-02-01", "2026-02-05", 1000.0)
    assert len(out) == 5
    assert out[0]["date"] == "2026-02-01"
    assert out[0]["is_gap"] is True
    assert out[0]["narration"] == "NO TRANSACTION FOR THE DAY"
    assert out[0]["closing_balance"] == 1000.0
    assert out[1]["is_gap"] is True
    assert out[2]["real"] is True
    assert out[2]["is_gap"] is False
    assert out[2]["closing_balance"] == 900.0
    assert "OPENING BALANCE" not in str(out)


def test_expand_prefers_parsed_closing_balance_per_row():
    txns = [
        {
            "date": "2026-02-01",
            "narration": "A",
            "withdrawal": 0.0,
            "deposit": 50.0,
            "closing_balance": 1050.0,
        },
        {
            "date": "2026-02-01",
            "narration": "B",
            "withdrawal": 10.0,
            "deposit": 0.0,
            "closing_balance": 1040.0,
        },
    ]
    out = _expand_to_full_month(txns, "2026-02-01", "2026-02-01", 1000.0)
    assert len(out) == 2
    assert out[0]["closing_balance"] == 1050.0
    assert out[1]["closing_balance"] == 1040.0
