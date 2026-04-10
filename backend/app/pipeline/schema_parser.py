"""
SchemaParser — Phase 3 Dynamic Regex Engine.

Receives a BankSchema produced by Phase 2 (LLM pattern scout) and uses it to
extract all transactions from every page of a bank statement PDF using pure
regex — no AI calls, no hardcoded bank logic.

Design principles:
  • All pages are parsed in parallel via asyncio (caller's responsibility).
  • Each parse_page() call is CPU-bound and stateless — safe to run in threads.
  • After merging pages, _infer_dr_cr() reconciles withdrawal/deposit labels
    by comparing consecutive closing balances (prev→current direction).
  • The BankSchema drives all branching — no bank-name conditionals in here.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .bank_schema import BankSchema
from .classifier import classify_transaction


# ── Date pattern maps ────────────────────────────────────────────────────────

_DATE_RE_MAP: Dict[str, str] = {
    "DD-Mon-YYYY":  r"(\d{2}-[A-Za-z]{3}-\d{4})",
    "DD/MM/YYYY":   r"(\d{2}/\d{2}/\d{4})",
    "DD-MM-YYYY":   r"(\d{2}-\d{2}-\d{4})",
    "YYYY-MM-DD":   r"(\d{4}-\d{2}-\d{2})",
    "DD Mon YYYY":  r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
    "DD MMM YYYY":  r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
}

_DATE_FMT_MAP: Dict[str, str] = {
    "DD-Mon-YYYY":  "%d-%b-%Y",
    "DD/MM/YYYY":   "%d/%m/%Y",
    "DD-MM-YYYY":   "%d-%m-%Y",
    "YYYY-MM-DD":   "%Y-%m-%d",
    "DD Mon YYYY":  "%d %b %Y",
    "DD MMM YYYY":  "%d %b %Y",
}

# Common ref-number-like patterns (alphanumeric 8-20 chars, not pure digits)
_REF_RE = re.compile(r"\b([A-Z0-9]{8,20})\b")


# ── SchemaParser ─────────────────────────────────────────────────────────────

class SchemaParser:
    """
    Regex engine parameterised by a BankSchema.
    Usage:
        parser = SchemaParser(schema)
        page_result = parser.parse_page(page_text)
        # page_result = {"transactions": [...], "closing_balance": float|None}

    After gathering all pages:
        all_txns = _infer_dr_cr(merged_transactions, opening_balance)
    """

    def __init__(self, schema: BankSchema) -> None:
        self.schema = schema

        # ── Date ──────────────────────────────────────────────────────────────
        date_re_str = _DATE_RE_MAP.get(schema.date_format, _DATE_RE_MAP["DD-Mon-YYYY"])
        # Anchor at line start for primary detection
        self.date_re_start = re.compile(r"^" + date_re_str)
        # Loose version for lines where date may follow a whitespace
        self.date_re_loose = re.compile(date_re_str)
        self.date_fmt = _DATE_FMT_MAP.get(schema.date_format, "%d-%b-%Y")

        # ── Amount ────────────────────────────────────────────────────────────
        if schema.amount_style == "rs_prefix":
            # Matches: Rs.1,23,456.78  Rs 12345.67  RS.500
            self.amount_re = re.compile(
                r"Rs\.?\s*([\d,]+\.?\d*)", re.IGNORECASE
            )
        else:
            # Matches: 1,23,456.78  12345.67  (word-boundary guarded)
            self.amount_re = re.compile(
                r"(?<!\w)([\d,]+\.\d{2})(?!\d)"
            )

        # Also a plain-number finder (used when separating debit/credit/balance)
        self._plain_num_re = re.compile(r"(?<!\w)([\d,]+\.\d{2})(?!\d)")

        # ── Balance sign markers ──────────────────────────────────────────────
        pos_esc = [re.escape(m) for m in schema.positive_markers]
        neg_esc = [re.escape(m) for m in schema.negative_markers]
        self.marker_re = re.compile(
            r"\b(" + "|".join(pos_esc + neg_esc) + r")\b"
        )
        self._pos_upper = {m.upper() for m in schema.positive_markers}
        self._neg_upper = {m.upper() for m in schema.negative_markers}

        # ── Header skip set ───────────────────────────────────────────────────
        self._header_kws = [kw.upper() for kw in schema.header_keywords]
        self._footer_markers = [m.upper() for m in schema.skip_footer_markers]

    # ── Public API ────────────────────────────────────────────────────────────

    def parse_page(self, page_text: str) -> Dict[str, Any]:
        """
        Parse all transactions from one page of text.
        Returns:
            {
              "transactions": [
                {
                  "date": "YYYY-MM-DD",
                  "narration": str,
                  "ref_number": str,
                  "withdrawal": float | None,   # to be finalised by _infer_dr_cr
                  "deposit":    float | None,   # to be finalised by _infer_dr_cr
                  "closing_balance": float,
                  "_txn_amount": float | None,  # raw single-amount (pre-dr-cr)
                }
              ],
              "closing_balance": float | None   # last balance seen on this page
            }
        """
        transactions: List[Dict] = []
        lines = [l.rstrip() for l in page_text.split("\n")]

        page_closing_balance: Optional[float] = None
        current_date: Optional[str] = None
        narration_buf: List[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if self._is_header_line(stripped):
                continue
            if self._is_footer_line(stripped):
                break # Stop parsing this page once footer is reached

            # 1. Primary: Check if line starts with a date
            date_match = self.date_re_start.match(stripped)
            is_new_txn = False

            if date_match:
                is_new_txn = True
                date_str = date_match.group(1)
                remainder = stripped[date_match.end():].strip()
            else:
                # 2. Secondary: Check if line CONTAINS a date (e.g. "1 01-Feb-2024 ...")
                date_search = self.date_re_loose.search(stripped)
                if date_search:
                    # Is this a new transaction or just part of narration?
                    # Rule: If we already have a current_date and haven't found amounts, 
                    # it might be a continuation. But usually, a second date means a new txn.
                    is_new_txn = True
                    date_str = date_search.group(1)
                    remainder = stripped[date_search.end():].strip()
                    # Also keep text BEFORE the date as prefix for next txn or append to current?
                    # Usually text before date is just noise like index numbers.

            if is_new_txn:
                # ── New transaction boundary ──────────────────────────────
                current_date = self._normalize_date(date_str)
                narration_buf = []

                amounts = self._extract_amounts(remainder)
                if amounts and amounts.get("closing_balance") is not None:
                    txn = self._build_txn(current_date, [], amounts, remainder)
                    if txn:
                        transactions.append(txn)
                        page_closing_balance = txn["closing_balance"]
                    current_date = None
                    narration_buf = []
                elif remainder:
                    narration_buf.append(remainder)

            elif current_date is not None:
                # ── Continuation / amount line ────────────────────────────
                amounts = self._extract_amounts(stripped)
                if amounts and amounts.get("closing_balance") is not None:
                    txn = self._build_txn(
                        current_date, narration_buf, amounts, stripped
                    )
                    if txn:
                        transactions.append(txn)
                        page_closing_balance = txn["closing_balance"]
                    current_date = None
                    narration_buf = []
                else:
                    narration_buf.append(stripped)

        return {"transactions": transactions, "closing_balance": page_closing_balance}

    # ── Amount extraction (dispatches by column_layout + balance_style) ───────

    def _extract_amounts(self, text: str) -> Optional[Dict]:
        layout = self.schema.column_layout
        if layout == "amount_then_balance":
            return self._parse_amount_then_balance(text)
        elif layout == "debit_credit_balance":
            return self._parse_debit_credit_balance(text)
        elif layout == "amount_flag_balance":
            return self._parse_amount_flag_balance(text)
        return None

    def _parse_amount_then_balance(self, text: str) -> Optional[Dict]:
        """
        HDFC CC / Union Bank style.
        Expected: [narration] [ref] Rs.X OD Rs.Y Cr   (or inline markers)
        Closing balance = last amount + its marker.
        Transaction amount = second-to-last amount.
        """
        amounts = self.amount_re.findall(text)
        markers = self.marker_re.findall(text)

        if not amounts:
            return None

        vals = [float(a.replace(",", "")) for a in amounts]

        if self.schema.balance_style in ("marker_inline", "dr_cr_suffix"):
            if not markers:
                return None

            bal_marker = markers[-1]
            bal_val = self._sign(vals[-1], bal_marker)

            txn_amt: Optional[float] = None
            if len(vals) >= 2:
                txn_amt = vals[-2]

            return {
                "closing_balance": bal_val,
                "_txn_amount": txn_amt,
                "_bal_marker": bal_marker,
                "_narration_cutoff": self._first_amount_pos(text),
                "withdrawal": None,  # resolved by _infer_dr_cr
                "deposit": None,
            }

        elif self.schema.balance_style == "signed":
            # Amounts may already be negative — just take the last one
            signed_amounts = re.findall(r"([+-]?[\d,]+\.\d{2})", text)
            if not signed_amounts:
                return None
            bal_val = float(signed_amounts[-1].replace(",", ""))
            txn_amt = float(signed_amounts[-2].replace(",", "")) if len(signed_amounts) >= 2 else None
            return {
                "closing_balance": bal_val,
                "_txn_amount": abs(txn_amt) if txn_amt else None,
                "_narration_cutoff": self._first_amount_pos(text),
                "withdrawal": None,
                "deposit": None,
            }

        else:
            # plain_positive — take last amount as balance
            if not vals:
                return None
            txn_amt = vals[-2] if len(vals) >= 2 else None
            return {
                "closing_balance": vals[-1],
                "_txn_amount": txn_amt,
                "_narration_cutoff": self._first_amount_pos(text),
                "withdrawal": None,
                "deposit": None,
            }

    def _parse_debit_credit_balance(self, text: str) -> Optional[Dict]:
        """
        SBI / Axis / ICICI Savings style.
        Three numeric columns: debit (or blank), credit (or blank), balance.
        Balance may have a Dr/Cr suffix.
        """
        plain = self._plain_num_re.findall(text)
        markers = self.marker_re.findall(text)

        if not plain:
            return None

        vals = [float(v.replace(",", "")) for v in plain]
        bal_marker = markers[-1] if markers else None
        cutoff = self._first_amount_pos(text)

        if len(vals) >= 3:
            # debit, credit, balance — take last three
            debit  = vals[-3]
            credit = vals[-2]
            bal    = self._sign(vals[-1], bal_marker)
            # Exactly one of debit/credit is the actual transaction;
            # the other column is blank (0 in plain-number extraction).
            if debit > 0 and credit > 0:
                # Both non-zero — the extra number likely came from narration/ref.
                # Fall back to treating last 2 numbers as (txn_amount, balance).
                txn_amt = credit  # second-to-last is more likely the transaction col
                return {
                    "closing_balance": bal,
                    "_txn_amount": txn_amt,
                    "withdrawal": None,  # resolved by infer_dr_cr
                    "deposit":    None,
                    "_narration_cutoff": cutoff,
                }
            return {
                "closing_balance": bal,
                "withdrawal": debit if debit > 0 else None,
                "deposit":    credit if credit > 0 else None,
                "_txn_amount": debit or credit or None,
                "_narration_cutoff": cutoff,
            }

        elif len(vals) == 2:
            txn, bal = vals[0], vals[1]
            bal = self._sign(bal, bal_marker)
            # Can't know debit/credit without prev balance — defer to _infer_dr_cr
            return {
                "closing_balance": bal,
                "_txn_amount": txn,
                "withdrawal": None,
                "deposit": None,
                "_narration_cutoff": cutoff,
            }

        elif len(vals) == 1:
            bal = self._sign(vals[0], bal_marker)
            return {
                "closing_balance": bal,
                "_txn_amount": None,
                "withdrawal": None,
                "deposit": None,
                "_narration_cutoff": cutoff,
            }

        return None

    def _parse_amount_flag_balance(self, text: str) -> Optional[Dict]:
        """
        ICICI CC / some Kotak formats.
        Pattern: [narration] [ref] amount Dr/Cr balance [marker?]
        """
        plain = self._plain_num_re.findall(text)
        markers = self.marker_re.findall(text)
        cutoff = self._first_amount_pos(text)

        if len(plain) < 2 or not markers:
            return None

        vals = [float(v.replace(",", "")) for v in plain]
        txn_val = vals[-2]
        bal_val = vals[-1]

        # First marker in text is for the transaction
        txn_marker = markers[0]
        bal_marker  = markers[-1] if len(markers) > 1 else None
        signed_bal  = self._sign(bal_val, bal_marker or txn_marker)

        is_withdrawal = txn_marker.upper() in self._neg_upper
        return {
            "closing_balance": signed_bal,
            "_txn_amount": txn_val,
            "withdrawal": txn_val if is_withdrawal else None,
            "deposit":    None     if is_withdrawal else txn_val,
            "_narration_cutoff": cutoff,
        }

    # ── Transaction builder ───────────────────────────────────────────────────

    def _build_txn(
        self,
        date: str,
        narration_parts: List[str],
        amounts: Dict,
        last_line: str,
    ) -> Optional[Dict]:
        """Assemble a transaction dict from parsed pieces."""
        cutoff = amounts.get("_narration_cutoff", len(last_line))
        prefix = last_line[:cutoff].strip() if cutoff > 0 else ""
        parts = narration_parts + ([prefix] if prefix else [])
        narration = " ".join(parts).strip()

        # Extract reference number (alphanumeric 8-20, not purely numeric)
        ref = ""
        for m in _REF_RE.finditer(narration):
            candidate = m.group(1)
            if not candidate.isdigit():
                ref = candidate
                break

        cb = amounts.get("closing_balance")
        if cb is None:
            return None

        return {
            "date":            date,
            "narration":       narration,
            "ref_number":      ref,
            "withdrawal":      _round_or_none(amounts.get("withdrawal")),
            "deposit":         _round_or_none(amounts.get("deposit")),
            "closing_balance": round(float(cb), 2),
            "_txn_amount":     _round_or_none(amounts.get("_txn_amount")),
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _normalize_date(self, date_str: str) -> str:
        try:
            return datetime.strptime(date_str.strip(), self.date_fmt).strftime("%Y-%m-%d")
        except ValueError:
            return date_str.strip()

    def _sign(self, amount: float, marker: Optional[str]) -> float:
        if marker is None:
            return amount
        if marker.upper() in self._neg_upper:
            return -abs(amount)
        return abs(amount)

    def _is_header_line(self, line: str) -> bool:
        if not self._header_kws:
            return False
        upper = line.upper()
        hits = sum(1 for kw in self._header_kws if kw in upper)
        # Require at least 2 keywords or ≥50% match to call it a header
        return hits >= max(2, len(self._header_kws) // 2)

    def _is_footer_line(self, line: str) -> bool:
        if not self._footer_markers:
            return False
        upper = line.upper()
        return any(m in upper for m in self._footer_markers)

    def _first_amount_pos(self, text: str) -> int:
        """Position of the first amount token — used as narration cutoff."""
        if self.schema.amount_style == "rs_prefix":
            m = re.search(r"Rs\.?\s*[\d,]", text, re.IGNORECASE)
        else:
            m = self._plain_num_re.search(text)
        return m.start() if m else len(text)


# ── Post-processing: dr/cr inference ─────────────────────────────────────────

def infer_dr_cr(
    transactions: List[Dict],
    opening_balance: float = 0.0,
) -> List[Dict]:
    """
    Walk through sorted transactions and infer withdrawal/deposit from the
    direction of balance change (prev → current).

    Primary:  use _txn_amount + delta direction when available.
    Fallback: when _txn_amount is None but the balance changed, compute the
              amount directly from abs(delta).  This handles cases where the
              regex found the closing balance but missed the transaction column
              (e.g. HDFC CC debit_credit_balance mis-classification).
    """
    prev_bal = opening_balance

    for txn in transactions:
        cb = txn.get("closing_balance", 0)
        txn_amt = txn.get("_txn_amount")

        # Only infer when withdrawal/deposit are still unresolved
        if txn.get("withdrawal") is None and txn.get("deposit") is None:
            delta = round(cb - prev_bal, 2)

            # If regex didn't find an explicit amount, derive it from balance delta
            if txn_amt is None and abs(delta) > 0.01:
                txn_amt = abs(delta)

            if txn_amt:
                if delta < 0:
                    txn["withdrawal"] = round(txn_amt, 2)
                    txn["deposit"]    = None
                elif delta > 0:
                    txn["withdrawal"] = None
                    txn["deposit"]    = round(txn_amt, 2)
                # delta == 0 and txn_amt provided: leave as None (can't determine direction)

        # Clean internal field
        txn.pop("_txn_amount", None)
        prev_bal = cb

    return transactions


def classify_transactions(transactions: List[Dict]) -> List[Dict]:
    """Run narration-based classifier over the final merged list."""
    for txn in transactions:
        txn["category"] = classify_transaction(txn.get("narration", ""))
    return transactions


# ── Utility ───────────────────────────────────────────────────────────────────

def _round_or_none(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return round(float(val), 2)
    except (TypeError, ValueError):
        return None
