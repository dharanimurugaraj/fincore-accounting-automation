"""Schema coercion from scouted headers (no bank names in logic)."""

from app.pipeline.bank_schema import BankSchema


def test_coerce_amount_then_balance_to_debit_credit_when_separate_columns_named():
    s = BankSchema(
        column_layout="amount_then_balance",
        withdrawal_col_name="Withdrawal (Dr)",
        deposit_col_name="Deposit (Cr)",
    )
    s.coerce_column_layout_if_separate_dr_cr_columns()
    assert s.column_layout == "debit_credit_balance"


def test_coerce_unchanged_when_single_column_layout_and_generic_names():
    s = BankSchema(
        column_layout="amount_then_balance",
        withdrawal_col_name="Amount",
        deposit_col_name="Amount",
    )
    s.coerce_column_layout_if_separate_dr_cr_columns()
    assert s.column_layout == "amount_then_balance"


def test_hdfc_style_line_populates_deposit_not_only_balance():
    """Separate Dr/Cr columns: commission row must carry Deposit from PDF, not infer."""
    from app.pipeline.schema_parser import SchemaParser, infer_dr_cr

    schema = BankSchema(
        column_layout="debit_credit_balance",
        amount_style="rs_prefix",
        balance_style="marker_inline",
        opening_balance=-138_425_196.92,
    )
    parser = SchemaParser(schema)
    tail = (
        "COMM ON GUARANTEE AMENDMENT BG2026002 GUARANTEE "
        "Rs.0.00 Rs.1,180.00 Rs.1,180.00 Cr"
    )
    amounts = parser._parse_debit_credit_balance(tail)
    assert amounts is not None
    assert amounts["withdrawal"] == 0.0
    assert amounts["deposit"] == 1180.0
    assert amounts["closing_balance"] == 1180.0
    assert amounts.get("_explicit_wd_dep") is True

    txn = parser._build_txn("2026-02-02", [], amounts, tail)
    assert txn is not None
    out = infer_dr_cr(
        [txn],
        opening_balance=-138_425_196.92,
        strict_column_amounts=False,
    )
    assert out[0]["deposit"] == 1180.0
    assert out[0]["withdrawal"] == 0.0
    assert "_explicit_wd_dep" not in out[0]
