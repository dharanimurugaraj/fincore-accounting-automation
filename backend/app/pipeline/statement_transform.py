"""
Bank-statement row normalisation (transformation only).

Maps parsed transactions to stable semantics:
  withdrawal_dr, deposit_cr, positive_balance, no_of_days

Uses dynamically supplied marker lists (from BankSchema / account payload).
Does not perform column detection or PDF extraction.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


def _float_or_zero(v: Any) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _upper_set(markers: Optional[List[str]]) -> Set[str]:
    if not markers:
        return set()
    return {m.strip().upper() for m in markers if m and str(m).strip()}


def parse_balance_raw_text(
    text: str,
    positive_markers: Set[str],
    negative_markers: Set[str],
) -> Tuple[Optional[float], Optional[bool]]:
    """
    Parse a balance cell string: marker + Rs-style amount (commas allowed).

    Returns:
        (magnitude, is_credit)
        - is_credit True  → Cr (positive balance semantics)
        - is_credit False → OD / DR
        - is_credit None  → no marker matched → caller treats as not credit (positive_balance = 0)
        - magnitude None if no amount parsed
    """
    if not text or not str(text).strip():
        return None, None
    s = str(text).strip()
    if not positive_markers and not negative_markers:
        return None, None

    ordered = sorted(positive_markers | negative_markers, key=len, reverse=True)
    marker_alt = "|".join(re.escape(m) for m in ordered)
    if not marker_alt:
        return None, None

    def _parse_amt(tok: str) -> Optional[float]:
        try:
            return abs(float(tok.replace(",", "")))
        except (TypeError, ValueError):
            return None

    # Marker then optional Rs then amount (e.g. "OD Rs.13,84,26,376.92", "Cr Rs.1,32,77,163.08")
    p1 = re.compile(
        rf"\b({marker_alt})\b\s*(?:Rs\.?\s*)?([\d,]+\.?\d*)",
        re.IGNORECASE,
    )
    m = p1.search(s)
    if m:
        mk = m.group(1).strip().upper()
        amt = _parse_amt(m.group(2))
        if mk in positive_markers:
            return amt, True
        if mk in negative_markers:
            return amt, False
        return amt, None

    # Amount then marker (e.g. "Rs.1,23,456.78 Cr")
    p2 = re.compile(
        rf"(?:Rs\.?\s*)?([\d,]+\.?\d*)\s*\b({marker_alt})\b",
        re.IGNORECASE,
    )
    m = p2.search(s)
    if m:
        amt = _parse_amt(m.group(1))
        mk = m.group(2).strip().upper()
        if mk in positive_markers:
            return amt, True
        if mk in negative_markers:
            return amt, False
        return amt, None

    return None, None


def _positive_balance_and_days(
    txn: Dict[str, Any],
    balance_style: str,
    positive_markers: Set[str],
    negative_markers: Set[str],
) -> Tuple[float, int]:
    """
    positive_balance: amount only when credit marker (Cr) applies; else 0.
    no_of_days: 1 iff positive_balance > 0.
    """
    side = txn.get("balance_credit_side")
    cb = _float_or_zero(txn.get("closing_balance"))

    # Priority 1: Use the marker identified by SchemaParser (closest to amount)
    if side is True:
        return round(abs(cb), 2), 1 if abs(cb) > 0 else 0
    if side is False:
        return 0.0, 0

    # Priority 2: Fallback to raw text parsing (limited to the line tail to avoid narration noise)
    raw = txn.get("balance_raw")
    if isinstance(raw, str) and raw.strip():
        tail = raw.strip()[-64:] # Only look at the tail where balance markers live
        mag, is_credit = parse_balance_raw_text(tail, positive_markers, negative_markers)
        if is_credit is True:
            amt = float(mag) if mag is not None else abs(cb)
            amt = round(abs(amt), 2)
            return amt, 1 if amt > 0 else 0
        if is_credit is False:
            return 0.0, 0

    if balance_style in ("marker_inline", "dr_cr_suffix"):
        # Unknown marker in marker modes → do not infer Cr from numeric sign alone
        return 0.0, 0

    # signed / plain_positive / default: numeric credit
    if cb > 0:
        return round(cb, 2), 1
    return 0.0, 0


def transform_transaction(
    txn: Dict[str, Any],
    balance_style: str = "signed",
    positive_markers: Optional[List[str]] = None,
    negative_markers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Mutates txn in place and returns it.
    Sets: withdrawal_dr, deposit_cr, positive_balance, no_of_days.
    """
    pos_u = _upper_set(positive_markers)
    neg_u = _upper_set(negative_markers)

    txn["withdrawal_dr"] = round(_float_or_zero(txn.get("withdrawal")), 2)
    txn["deposit_cr"] = round(_float_or_zero(txn.get("deposit")), 2)

    pb, nd = _positive_balance_and_days(txn, balance_style or "signed", pos_u, neg_u)
    txn["positive_balance"] = pb
    txn["no_of_days"] = nd
    return txn


def _default_markers_if_empty(
    positive_markers: Optional[List[str]],
    negative_markers: Optional[List[str]],
) -> Tuple[List[str], List[str]]:
    pm, nm = positive_markers, negative_markers
    if (not pm) and (not nm):
        return ["Cr", "CR"], ["OD", "DR", "Dr"]
    return list(pm or []), list(nm or [])


def apply_transforms_to_transactions(
    transactions: List[Dict[str, Any]],
    balance_style: str = "signed",
    positive_markers: Optional[List[str]] = None,
    negative_markers: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    pm, nm = _default_markers_if_empty(positive_markers, negative_markers)
    for t in transactions:
        transform_transaction(t, balance_style, pm, nm)
    return transactions


def apply_transforms_to_account(account: Dict[str, Any]) -> Dict[str, Any]:
    """Transform account['transactions'] using account balance_style and schema markers."""
    txns = account.get("transactions") or []
    if not txns:
        return account
    style = account.get("balance_style") or "signed"
    pm, nm = _default_markers_if_empty(
        account.get("positive_markers"),
        account.get("negative_markers"),
    )
    apply_transforms_to_transactions(txns, style, pm, nm)
    return account
