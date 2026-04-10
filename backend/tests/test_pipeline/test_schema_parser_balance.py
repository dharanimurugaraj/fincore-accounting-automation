"""Balance marker attachment and opening-balance echo filtering (bank-agnostic)."""

from app.pipeline.bank_schema import BankSchema
from app.pipeline.schema_parser import SchemaParser, infer_dr_cr


def test_amount_then_balance_uses_marker_after_last_rs_amount():
    schema = BankSchema(
        column_layout="amount_then_balance",
        amount_style="rs_prefix",
        balance_style="marker_inline",
    )
    parser = SchemaParser(schema)
    line = "COMM Rs.1,00,000.00 OD Rs.23,668,500.00 Cr"
    out = parser._parse_amount_then_balance(line)
    assert out is not None
    assert out["closing_balance"] == 23668500.0
    assert out["_txn_amount"] == 100000.0


def test_amount_then_balance_last_segment_od_is_negative():
    schema = BankSchema(
        column_layout="amount_then_balance",
        amount_style="rs_prefix",
        balance_style="marker_inline",
    )
    parser = SchemaParser(schema)
    line = "X Rs.500.00 OD Rs.1,000.00 OD"
    out = parser._parse_amount_then_balance(line)
    assert out is not None
    assert out["closing_balance"] == -1000.0


def test_skip_opening_balance_echo_when_matches_schema_opening():
    schema = BankSchema(
        column_layout="debit_credit_balance",
        amount_style="plain_number",
        opening_balance=-138425196.92,
    )
    parser = SchemaParser(schema)
    amounts = {
        "closing_balance": -138425196.92,
        "withdrawal": None,
        "deposit": None,
        "_txn_amount": None,
    }
    assert parser._should_skip_opening_balance_echo(amounts, [], ": OD 13,84,25,196.92")
    # Same signed balance as header opening, no Dr/Cr — skip even without OD in text
    assert parser._should_skip_opening_balance_echo(
        amounts, [], "narration noise without marker keywords"
    )


def test_debit_credit_balance_hdfc_od_before_balance_rs():
    """
    HDFC Cash Credit: ``Rs.1,180.00 OD Rs.13,84,26,376.92`` — OD applies to the
    balance figure, not after it. Must sign balance negative so infer_dr_cr does
    not attribute the OD amount to Deposit (Cr).
    """
    schema = BankSchema(
        column_layout="debit_credit_balance",
        amount_style="rs_prefix",
        balance_style="marker_inline",
        opening_balance=-138425196.92,
    )
    parser = SchemaParser(schema)
    line = "COMM ON GUARANTEE AMENDMENT BG2026002 Rs.1,180.00 OD Rs.13,84,26,376.92"
    amounts = parser._extract_amounts(line)
    assert amounts is not None
    assert amounts["_bal_marker"] == "OD"
    assert amounts["closing_balance"] == -138426376.92
    txn = parser._build_txn("2026-02-02", [], amounts, line)
    assert txn is not None
    fixed = infer_dr_cr([txn], opening_balance=-138425196.92, strict_column_amounts=False)
    assert fixed[0]["withdrawal"] == 1180.0
    assert fixed[0]["deposit"] is None
    assert fixed[0]["closing_balance"] == -138426376.92


def test_infer_dr_cr_fills_dr_cr_from_balance_delta_with_txn_amount():
    opening = 1000.0
    txns = [
        {
            "date": "2026-02-02",
            "narration": "fee",
            "ref_number": "",
            "withdrawal": None,
            "deposit": None,
            "closing_balance": 900.0,
            "_txn_amount": 100.0,
        }
    ]
    out = infer_dr_cr(txns, opening_balance=opening, strict_column_amounts=False)
    assert out[0]["withdrawal"] == 100.0
    assert out[0]["deposit"] is None
    assert "_txn_amount" not in out[0]
