"""Tests for statement_transform normalisation."""

from app.pipeline.statement_transform import (
    parse_balance_raw_text,
    transform_transaction,
    apply_transforms_to_transactions,
)


def test_parse_cr_rs_amount():
    mag, side = parse_balance_raw_text(
        "Cr Rs.1,32,77,163.08",
        {"CR"},
        {"OD", "DR"},
    )
    assert side is True
    assert mag == 13277163.08


def test_parse_od_rs_amount():
    mag, side = parse_balance_raw_text(
        "OD Rs.13,84,26,376.92",
        {"CR"},
        {"OD", "DR"},
    )
    assert side is False
    assert mag == 138426376.92


def test_parse_amount_then_marker():
    mag, side = parse_balance_raw_text(
        "Rs.500.00 cr",
        {"CR"},
        {"OD", "DR"},
    )
    assert side is True
    assert mag == 500.0


def test_parse_no_marker():
    mag, side = parse_balance_raw_text(
        "Rs.1,000.00",
        {"CR"},
        {"OD", "DR"},
    )
    assert side is None
    assert mag is None


def test_transform_withdrawal_deposit_zero():
    t = transform_transaction(
        {"withdrawal": None, "deposit": "", "closing_balance": -100.0, "balance_credit_side": False},
        balance_style="marker_inline",
        positive_markers=["Cr", "CR"],
        negative_markers=["OD", "DR"],
    )
    assert t["withdrawal_dr"] == 0.0
    assert t["deposit_cr"] == 0.0
    assert t["positive_balance"] == 0.0
    assert t["no_of_days"] == 0


def test_transform_credit_side():
    t = transform_transaction(
        {"withdrawal": 10, "deposit": None, "closing_balance": 5000.0, "balance_credit_side": True},
        balance_style="marker_inline",
        positive_markers=["Cr"],
        negative_markers=["OD"],
    )
    assert t["withdrawal_dr"] == 10.0
    assert t["deposit_cr"] == 0.0
    assert t["positive_balance"] == 5000.0
    assert t["no_of_days"] == 1


def test_transform_balance_raw_cr():
    t = transform_transaction(
        {
            "withdrawal": 0,
            "deposit": 0,
            "closing_balance": 100.0,
            "balance_raw": "Cr Rs.99.50",
        },
        balance_style="marker_inline",
        positive_markers=["Cr", "CR"],
        negative_markers=["OD", "DR"],
    )
    assert t["positive_balance"] == 99.5
    assert t["no_of_days"] == 1


def test_transform_signed_style_numeric():
    t = transform_transaction(
        {"withdrawal": 0, "deposit": 0, "closing_balance": 250.0},
        balance_style="signed",
        positive_markers=["Cr"],
        negative_markers=["OD"],
    )
    assert t["positive_balance"] == 250.0
    assert t["no_of_days"] == 1


def test_apply_list_mutates():
    rows = [{"withdrawal": 1, "deposit": 2, "closing_balance": -50, "balance_credit_side": False}]
    apply_transforms_to_transactions(rows, "marker_inline", ["Cr"], ["OD"])
    assert rows[0]["withdrawal_dr"] == 1.0
    assert rows[0]["positive_balance"] == 0.0
