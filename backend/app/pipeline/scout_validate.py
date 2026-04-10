"""
Validate Phase-2 scout column names against page-1 extracted text (anti-hallucination).

Layout-aware: no bank names; uses BankSchema.column_layout only.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from .bank_schema import BankSchema


def _normalize_page_text(page_text: str) -> str:
    if not page_text:
        return ""
    s = page_text.lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _header_tokens(header: str) -> List[str]:
    if not header or not str(header).strip():
        return []
    raw = str(header).strip().lower()
    return [t for t in re.split(r"[^\w]+", raw) if len(t) >= 2]


def header_appears_in_page(header: str, page_norm: str) -> bool:
    """True if full header substring matches or all significant tokens appear in page text."""
    if not header or not str(header).strip():
        return True
    h = " ".join(str(header).strip().lower().split())
    if h in page_norm:
        return True
    tokens = _header_tokens(header)
    if not tokens:
        return True
    return all(t in page_norm for t in tokens)


def validate_scout_headers_against_page(
    schema: BankSchema, page1_text: str
) -> Tuple[bool, List[str]]:
    """
    Returns (ok, reasons). When ok is False, reasons list explains missing strings.
    """
    page_norm = _normalize_page_text(page1_text)
    if len(page_norm) < 20:
        return False, ["page_1_text_too_short_for_header_check"]

    reasons: List[str] = []

    if not header_appears_in_page(schema.narration_col_name, page_norm):
        reasons.append(f"narration_col_name_not_in_page:{schema.narration_col_name!r}")

    if not header_appears_in_page(schema.balance_col_name, page_norm):
        reasons.append(f"balance_col_name_not_in_page:{schema.balance_col_name!r}")

    layout = schema.column_layout
    if layout == "debit_credit_balance":
        if not header_appears_in_page(schema.withdrawal_col_name, page_norm):
            reasons.append(
                f"withdrawal_col_name_not_in_page:{schema.withdrawal_col_name!r}"
            )
        if not header_appears_in_page(schema.deposit_col_name, page_norm):
            reasons.append(
                f"deposit_col_name_not_in_page:{schema.deposit_col_name!r}"
            )

    return (len(reasons) == 0, reasons)
