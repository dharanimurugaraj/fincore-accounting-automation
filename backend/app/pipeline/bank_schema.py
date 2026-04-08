"""
BankSchema — One-time extracted format descriptor for a bank statement PDF.

Produced by Phase 2 (LLM pattern scout, page 1 text only).
Drives Phase 3 (dynamic regex engine, all remaining pages, zero AI).
Persisted to DB per ParsedAccount for full auditability.

column_layout options:
    "amount_then_balance"   → One transaction amount col + closing balance
                              e.g. HDFC CC: Rs.50,000.00  Rs.4,50,000.00 OD
    "debit_credit_balance"  → Separate Debit / Credit cols + closing balance
                              e.g. SBI, Axis, ICICI Savings
    "amount_flag_balance"   → One amount + Dr/Cr flag col + closing balance
                              e.g. ICICI CC, some Kotak formats

balance_style options:
    "marker_inline"   → balance has OD/Cr/DR marker on same token  (HDFC CC)
    "dr_cr_suffix"    → balance followed by standalone Dr/Cr word   (Axis)
    "signed"          → balance is a plain negative/positive float   (some exports)
    "plain_positive"  → balance always positive; sign from debit/credit columns

amount_style options:
    "rs_prefix"     → amounts formatted as Rs.1,23,456.78 or Rs 12,345.67
    "plain_number"  → amounts formatted as 1,23,456.78
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class BankSchema:
    # ── Account metadata ─────────────────────────────────────────────────────
    bank_name: str = "UNKNOWN"
    account_number: str = "UNKNOWN"
    account_type: str = "CC"          # CC | CA | SA
    period_from: Optional[str] = None  # YYYY-MM-DD
    period_to: Optional[str] = None    # YYYY-MM-DD
    opening_balance: Optional[float] = None
    cc_roi_percent: Optional[float] = None
    cc_limit: Optional[float] = None  # CC/OD Limit (Extracted from header)

    # ── Date parsing ─────────────────────────────────────────────────────────
    date_format: str = "DD-Mon-YYYY"
    # Supported: DD-Mon-YYYY | DD/MM/YYYY | DD-MM-YYYY | YYYY-MM-DD | DD Mon YYYY | DD MMM YYYY

    # ── Amount formatting ────────────────────────────────────────────────────
    amount_style: str = "rs_prefix"   # rs_prefix | plain_number

    # ── Balance sign convention ──────────────────────────────────────────────
    balance_style: str = "marker_inline"
    # marker_inline | dr_cr_suffix | signed | plain_positive

    # ── Column layout ────────────────────────────────────────────────────────
    column_layout: str = "amount_then_balance"
    # amount_then_balance | debit_credit_balance | amount_flag_balance

    # ── Sign markers ─────────────────────────────────────────────────────────
    positive_markers: List[str] = field(default_factory=lambda: ["Cr", "CR"])
    negative_markers: List[str] = field(default_factory=lambda: ["OD", "DR", "Dr"])

    # ── Parsing hints ────────────────────────────────────────────────────────
    has_narration_continuation: bool = False
    # If true, narration can span lines before amount line

    # ── Semantic Column Names ────────────────────────────────────────────────
    narration_col_name: str = "Narration"
    ref_col_name: str = "Chq/Ref No."
    withdrawal_col_name: str = "Withdrawal (Dr)"
    deposit_col_name: str = "Deposit (Cr)"
    balance_col_name: str = "Balance"

    header_keywords: List[str] = field(default_factory=list)
    # Column header words (used to skip header rows during page parsing)

    skip_footer_markers: List[str] = field(default_factory=list)
    # Strings that mark the end of the transaction table on a page (e.g. "Total", "Page")

    # ── Internal tracking ────────────────────────────────────────────────────
    extraction_model: str = ""   # Which AI model produced this schema
    confidence: str = "high"     # high | medium | low (set by extractor)

    # ─────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BankSchema":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})

    def is_valid(self) -> bool:
        """Minimal sanity check before handing to parser."""
        return (
            self.date_format in DATE_FORMAT_OPTIONS
            and self.column_layout in COLUMN_LAYOUT_OPTIONS
            and self.balance_style in BALANCE_STYLE_OPTIONS
            and self.amount_style in AMOUNT_STYLE_OPTIONS
        )


DATE_FORMAT_OPTIONS = {
    "DD-Mon-YYYY", "DD/MM/YYYY", "DD-MM-YYYY",
    "YYYY-MM-DD", "DD Mon YYYY", "DD MMM YYYY",
}

COLUMN_LAYOUT_OPTIONS = {
    "amount_then_balance",
    "debit_credit_balance",
    "amount_flag_balance",
}

BALANCE_STYLE_OPTIONS = {
    "marker_inline",
    "dr_cr_suffix",
    "signed",
    "plain_positive",
}

AMOUNT_STYLE_OPTIONS = {
    "rs_prefix",
    "plain_number",
}
