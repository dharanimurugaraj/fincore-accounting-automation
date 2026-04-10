"""Scout header validation vs page-1 text."""

from app.pipeline.bank_schema import BankSchema
from app.pipeline.scout_validate import (
    header_appears_in_page,
    validate_scout_headers_against_page,
)


def test_header_tokens_fuzzy_match():
    page = "some noise date debit credit balance amount"
    assert header_appears_in_page("Debit", page)
    assert header_appears_in_page("Credit", page)


def test_debit_credit_layout_requires_wd_and_dep():
    page = (
        "statement axis account\n"
        "date narration chq ref debit credit balance\n"
    )
    s = BankSchema(
        column_layout="debit_credit_balance",
        narration_col_name="Narration",
        withdrawal_col_name="Debit",
        deposit_col_name="Credit",
        balance_col_name="Balance",
    )
    ok, reasons = validate_scout_headers_against_page(s, page)
    assert ok
    assert reasons == []


def test_debit_credit_fails_if_deposit_missing():
    page = "date narration debit balance"
    s = BankSchema(
        column_layout="debit_credit_balance",
        narration_col_name="Narration",
        withdrawal_col_name="Debit",
        deposit_col_name="Credit",
        balance_col_name="Balance",
    )
    ok, reasons = validate_scout_headers_against_page(s, page)
    assert not ok
    assert any("deposit" in r for r in reasons)


def test_amount_then_balance_skips_wd_dep_requirement():
    page = "hdfc card statement date transaction remarks amount balance"
    s = BankSchema(
        column_layout="amount_then_balance",
        narration_col_name="Transaction Remarks",
        withdrawal_col_name="Withdrawal (Dr)",
        deposit_col_name="Deposit (Cr)",
        balance_col_name="Balance",
    )
    ok, _ = validate_scout_headers_against_page(s, page)
    assert ok
