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

import math
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

def _score_ref_candidate(token: str) -> float:
    """
    Bank-agnostic score: prefer compact alphanumeric ids that mix letters and digits
    (typical UTR / ref / cheque codes). Deprioritise long all-letter tokens.
    """
    if len(token) < 6 or token.isdigit():
        return float("-inf")
    n = len(token)
    nd = sum(1 for c in token if c.isdigit())
    sc = float(n) + 14.0 * nd
    if nd > 0:
        nl = sum(1 for c in token if c.isalpha())
        if nl > 0:
            sc += 8.0
    else:
        if n >= 8:
            sc -= float(n - 7) * 6.0
    return sc


def _pick_ref_number(narration: str, amount_line: str) -> str:
    """
    Choose Chq/Ref from narration + amount line using only structural heuristics
    (no bank names or fixed word lists). Scans A–Z/0–9 runs; highest score wins.
    """
    blob = f"{narration} {amount_line}".upper()
    best_s = ""
    best_sc = float("-inf")
    for m in re.finditer(r"\b([A-Z0-9]{6,24})\b", blob):
        t = m.group(1)
        sc = _score_ref_candidate(t)
        if sc > best_sc:
            best_sc = sc
            best_s = t
    return best_s


# ── SchemaParser ─────────────────────────────────────────────────────────────

class SchemaParser:
    """
    Regex engine parameterised by a BankSchema.
    Usage:
        parser = SchemaParser(schema)
        page_result = parser.parse_page(page_text, page_idx=0)
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
            # We use a slightly more restrictive version to avoid picking up 
            # reference numbers that don't look like money (require at least 2 digits after dot)
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

    def extract_header_metadata(self, page1_text: str) -> Dict[str, Any]:
        """
        Deterministically extract key metadata from the first page header text.

        Called by extractor.py (Phase 2 → Phase 3 handoff) to override any
        AI-hallucinated values with regex-confirmed values.

        Returns a dict with any subset of:
            opening_balance: float       (signed — negative if OD)
            cc_limit:        float
            wcdl_limit:      float
            total_wc_limit:  float
            account_number:  str
            wcdl_loans:      list[dict]  e.g. [{"ref": "WCDL-1", "amount": 3e8, "ac": "...", "maturity": "21-Feb-2026"}]
        """
        result: Dict[str, Any] = {}
        text = page1_text

        # ── Opening Balance ───────────────────────────────────────────────────
        # Patterns handled:
        #   "Opening Balance  Rs.1,23,456.78 Cr"           (marker after amount)
        #   "Opening Balance: OD 13,84,25,196.92"          (marker before amount — HDFC CC)
        #   "Opening Balance as on 01-Feb-2026: OD 13,84,25,196.92"
        #   "Balance Brought Forward  Rs.5,000.00 OD"
        ob_patterns = [
            # Marker BEFORE amount (HDFC CC style): "OD 13,84,25,196.92"
            r"(?:Opening\s+Balance|Opening\s+Bal(?:ance)?|Balance\s+B(?:/|rought)?\s*F(?:wd|orward)?)"
            r"(?:[^:]*?:\s*|\s+)"                     # optional "as on DD-Mon-YYYY:" or plain space
            r"(OD|DR|Dr|Cr|CR)\s+"                   # marker FIRST
            r"([\d,]+\.?\d*)",                        # then amount

            # Marker AFTER amount (standard style): "Rs.5,000.00 Cr"
            r"(?:Opening\s+Balance|Opening\s+Bal(?:ance)?|Balance\s+B(?:/|rought)?\s*F(?:wd|orward)?)"
            r"[\s:]*(?:Rs\.?\s*)?([\d,]+\.?\d*)\s+([A-Za-z]{0,3})",
        ]
        for i, pat in enumerate(ob_patterns):
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    if i == 0:
                        marker = m.group(1).strip().upper()
                        val    = float(m.group(2).replace(",", ""))
                    else:
                        val    = float(m.group(1).replace(",", ""))
                        marker = m.group(2).strip().upper() if m.lastindex >= 2 else ""

                    if marker in self._neg_upper or marker in {"OD", "DR"}:
                        val = -abs(val)
                    else:
                        val = abs(val)

                    result["opening_balance"] = val
                    break
                except (ValueError, IndexError):
                    pass

        # ── CC / Sanctioned Limit ─────────────────────────────────────────────
        # "CC Limit: Rs.25,00,00,000"  "OD Limit: Rs.5 Cr"  "Sanctioned Limit: 225000000"
        limit_patterns = [
            r"(?:CC\s+Limit|OD\s+Limit|Sanctioned\s+Limit|Credit\s+Limit|Drawing\s+Power)"
            r"[\s:]*(?:Rs\.?\s*)?([\d,]+\.?\d*)\s*([A-Za-z]{0,3})",
        ]
        for pat in limit_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1).replace(",", ""))
                    suffix = m.group(2).strip().upper() if m.lastindex >= 2 else ""
                    if suffix in ("CR", "C"):
                        val *= 10_000_000
                    result["cc_limit"] = val
                    break
                except (ValueError, IndexError):
                    pass

        # ── WCDL Limit ────────────────────────────────────────────────────────
        # "WCDL Limit: Rs.52,50,00,000"
        wcdl_limit_m = re.search(
            r"WCDL\s+Limit[\s:]*(?:Rs\.?\s*)?([\d,]+\.?\d*)", text, re.IGNORECASE
        )
        if wcdl_limit_m:
            try:
                result["wcdl_limit"] = float(wcdl_limit_m.group(1).replace(",", ""))
            except ValueError:
                pass

        # ── Total WC Limit ────────────────────────────────────────────────────
        # "Total WC: Rs.77,50,00,000"
        total_wc_m = re.search(
            r"Total\s+WC[\s:]*(?:Rs\.?\s*)?([\d,]+\.?\d*)", text, re.IGNORECASE
        )
        if total_wc_m:
            try:
                result["total_wc_limit"] = float(total_wc_m.group(1).replace(",", ""))
            except ValueError:
                pass

        # ── WCDL Drawdown Lines ───────────────────────────────────────────────
        # "WCDL-1: Rs.30,00,00,000 (A/c 240LN01253580014, Mat: 21-Feb-2026)"
        # "WCDL-2: Rs.25,00,00,000 (A/c 240LN01260280020, Mat: 29-Mar-2026)"
        wcdl_loans = []
        for m in re.finditer(
            r"(WCDL-?\d+)\s*:\s*(?:Rs\.?\s*)?([\d,]+\.?\d*)"
            r"(?:\s*\([^)]*A/?c\s*([\w]+)[^)]*Mat(?:urity)?[\s:]*([0-9A-Za-z\-]+))?",
            text,
            re.IGNORECASE,
        ):
            try:
                wcdl_loans.append({
                    "ref":      m.group(1),
                    "amount":   float(m.group(2).replace(",", "")),
                    "ac":       m.group(3) if m.group(3) else "",
                    "maturity": m.group(4) if m.group(4) else "",
                })
            except (ValueError, AttributeError):
                pass
        if wcdl_loans:
            result["wcdl_loans"] = wcdl_loans

        # ── Account Number ────────────────────────────────────────────────────
        # "Account No: XXXXXXXX521"  "A/c No. 12345678"  "Account: XXXXXXXX521"
        # Note: HDFC masks most digits → XXXXXXXX521 has only 3 visible digits.
        # We accept if the candidate ends with at least 3 digits (last 3 = branch suffix).
        acct_patterns = [
            r"(?:Account\s*(?:No\.?|Number|#)|A/?c\.?\s*(?:No\.?|Number)?)"
            r"[\s:]*([X0-9]{4,20}\d{3,})",   # masked or unmasked, ends in digits
            r"(?:Account\s*(?:No\.?|Number|#)|A/?c\.?\s*(?:No\.?|Number)?)"
            r"[\s:]*([X\dA-Za-z]{6,20})",
        ]
        for pat in acct_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                # Accept if tail has 3+ consecutive digits (handles XXXXXXXX521)
                if re.search(r"\d{3,}$", candidate):
                    result["account_number"] = candidate
                    break

        return result

    def _trailing_balance_marker(self, text: str) -> Optional[str]:
        """
        Marker for the *closing* balance on the line.

        Checks (1) immediately after the last amount token (e.g. Rs.500.00 Cr),
        then (2) immediately before it — HDFC Cash Credit often prints
        ``OD Rs.13,84,26,376.92`` with the marker before the balance figure.
        Missing this leaves the balance unsigned positive and breaks Dr/Cr inference.
        """
        def _first_marker_in(s: str) -> Optional[str]:
            m = self.marker_re.search(s)
            if m:
                return m.group(1)
            # Fallback: check for OD/CR/DR anywhere if it's near the end
            s_upper = s.upper()
            for mk in ["OD", "CR", "DR", "DR."]:
                 if mk in s_upper:
                     return mk
            return None

        if self.schema.amount_style == "rs_prefix":
            matches = list(
                re.finditer(r"Rs\.?\s*[\d,]+\.?\d*", text, re.IGNORECASE)
            )
            if not matches:
                return None
            last = matches[-1]
            after = _first_marker_in(text[last.end() : last.end() + 36])
            if after:
                return after
            before = text[max(0, last.start() - 24) : last.start()]
            return _first_marker_in(before)
        else:
            matches = list(self._plain_num_re.finditer(text))
            if not matches:
                return None
            last = matches[-1]
            after = _first_marker_in(text[last.end() : last.end() + 36])
            if after:
                return after
            before = text[max(0, last.start() - 24) : last.start()]
            return _first_marker_in(before)

    def _should_skip_opening_balance_echo(
        self,
        amounts: Dict[str, Any],
        narration_parts: List[str],
        raw_line_tail: str,
    ) -> bool:
        """
        Drop table rows that only repeat the header opening balance (same signed
        cb as schema.opening_balance, no transaction amount). These create a fake
        first row with empty Dr/Cr and break the user's expectation of the sheet.
        """
        ob = self.schema.opening_balance
        if ob is None:
            return False
        cb = amounts.get("closing_balance")
        if cb is None:
            return False
        try:
            fcb, fob = float(cb), float(ob)
        except (TypeError, ValueError):
            return False
        if amounts.get("_txn_amount") is not None:
            return False
        if amounts.get("withdrawal") is not None or amounts.get("deposit") is not None:
            return False

        # Balance-only row that matches header opening → never a real movement line
        if math.isclose(fcb, fob, rel_tol=0, abs_tol=1.0):
            return True

        blob = " ".join(narration_parts + ([raw_line_tail] if raw_line_tail else [])).strip()
        if re.search(
            r"(?i)\bopening\s+bal|balance\s+brought|balance\s+b/?f\b|balance\s+forward",
            blob,
        ):
            return True
        # e.g. ": OD 13,84,25,196.92" — header balance echoed as a pseudo-txn line
        if re.match(r"^[:;,\-\s]*(?:OD|DR|Dr|Cr|CR)\b", blob):
            return True
        return False

    def parse_page(self, page_text: str, page_idx: int = 0) -> Dict[str, Any]:
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
        parse_seq = 0

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
                    if self._should_skip_opening_balance_echo(
                        amounts, [], remainder
                    ):
                        current_date = None
                        narration_buf = []
                    else:
                        txn = self._build_txn(current_date, [], amounts, remainder)
                        if txn:
                            txn["_page_idx"] = page_idx
                            txn["_parse_seq"] = parse_seq
                            parse_seq += 1
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
                    if self._should_skip_opening_balance_echo(
                        amounts, narration_buf, stripped
                    ):
                        current_date = None
                        narration_buf = []
                    else:
                        txn = self._build_txn(
                            current_date, narration_buf, amounts, stripped
                        )
                        if txn:
                            txn["_page_idx"] = page_idx
                            txn["_parse_seq"] = parse_seq
                            parse_seq += 1
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
        Expected: [narration] [ref] Rs.X OD Rs.Y Cr
        """
        amounts = self.amount_re.findall(text)
        markers = self.marker_re.findall(text)

        if not amounts:
            return None

        # Clean "Rs." and commas
        vals = [float(re.sub(r"[^\d.]", "", a)) for a in amounts]

        # The last value is ALWAYS the balance in this layout
        bal_raw = vals[-1]
        bal_marker = self._trailing_balance_marker(text) or (
            markers[-1] if markers else None
        )
        bal_val = self._sign(bal_raw, bal_marker)

        txn_amt: Optional[float] = None
        if len(vals) >= 2:
            # The second-to-last value is the transaction amount
            txn_amt = vals[-2]
        
        return {
            "closing_balance": bal_val,
            "_txn_amount": txn_amt,
            "_bal_marker": bal_marker,
            "_narration_cutoff": self._first_amount_pos(text),
            "withdrawal": None,
            "deposit": None,
        }

    def _parse_debit_credit_balance(self, text: str) -> Optional[Dict]:
        """
        SBI / Axis / ICICI Savings style.
        """
        plain = self._plain_num_re.findall(text)
        markers = self.marker_re.findall(text)

        if not plain:
            return None

        vals = [float(v.replace(",", "")) for v in plain]
        bal_marker = self._trailing_balance_marker(text) or (
            markers[-1] if markers else None
        )
        cutoff = self._first_amount_pos(text)

        # If exactly 2 numbers, assume [txn_amount, closing_balance]
        # This is common in HDFC statements even if scouted as 3-column.
        if len(vals) == 2:
            txn_amt, bal_raw = vals[0], vals[1]
            bal = self._sign(bal_raw, bal_marker)
            return {
                "closing_balance": bal,
                "_txn_amount": txn_amt,
                "withdrawal": None,
                "deposit": None,
                "_bal_marker": bal_marker,
                "_narration_cutoff": cutoff,
            }

        # If 3 or more numbers, [..., withdrawal, deposit, balance]
        elif len(vals) >= 3:
            bal_raw = vals[-1]
            bal = self._sign(bal_raw, bal_marker)
            
            v_dep = vals[-2]
            v_wd  = vals[-3]

            if self.schema.dr_cr_order == "deposit_then_withdrawal":
                deposit, withdrawal = v_wd, v_dep
            else:
                withdrawal, deposit = v_wd, v_dep

            # Keep 0.0 for empty Dr/Cr columns so infer_dr_cr does not treat them as
            # "unparsed" and replace PDF amounts with the full balance delta.
            return {
                "closing_balance": bal,
                "withdrawal": round(float(withdrawal), 2),
                "deposit": round(float(deposit), 2),
                "_explicit_wd_dep": True,
                "_txn_amount": round(float(withdrawal), 2)
                if withdrawal > 0
                else (round(float(deposit), 2) if deposit > 0 else None),
                "_bal_marker": bal_marker,
                "_narration_cutoff": cutoff,
            }

        elif len(vals) == 1:
            bal = self._sign(vals[0], bal_marker)
            return {
                "closing_balance": bal,
                "withdrawal": None,
                "deposit": None,
                "_txn_amount": None,
                "_bal_marker": bal_marker,
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
        bal_marker = self._trailing_balance_marker(text) or (
            markers[-1] if len(markers) > 1 else None
        )
        signed_bal = self._sign(bal_val, bal_marker or txn_marker)

        is_withdrawal = txn_marker.upper() in self._neg_upper
        return {
            "closing_balance": signed_bal,
            "_txn_amount": txn_val,
            "withdrawal": txn_val if is_withdrawal else None,
            "deposit":    None     if is_withdrawal else txn_val,
            "_bal_marker": bal_marker or txn_marker,
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

        ref = _pick_ref_number(narration, last_line)

        cb = amounts.get("closing_balance")
        if cb is None:
            return None

        out: Dict[str, Any] = {
            "date":            date,
            "narration":       narration,
            "ref_number":      ref,
            "withdrawal":      _round_or_none(amounts.get("withdrawal")),
            "deposit":         _round_or_none(amounts.get("deposit")),
            "closing_balance": round(float(cb), 2),
            "_txn_amount":     _round_or_none(amounts.get("_txn_amount")),
        }
        if amounts.get("_explicit_wd_dep"):
            out["_explicit_wd_dep"] = True
        bm = amounts.get("_bal_marker")
        out["balance_credit_side"] = self._balance_credit_side_from_marker(bm)
        # Raw amount line for downstream statement_transform (balance markers + Rs amounts).
        out["balance_raw"] = last_line.strip()
        return out

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

    def _balance_credit_side_from_marker(self, bal_marker: Optional[str]) -> Optional[bool]:
        """
        For working-sheet Positive Bal: True = credit-side (Cr) per blueprint positive_markers,
        False = debit/OD side, None = use numeric closing_balance only (signed/plain_positive).
        """
        if self.schema.balance_style not in ("marker_inline", "dr_cr_suffix"):
            return None
        if not bal_marker:
            return None
        u = bal_marker.strip().upper()
        if u in self._pos_upper:
            return True
        if u in self._neg_upper:
            return False
        return None

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
    strict_column_amounts: bool = False,
) -> List[Dict]:
    """
    Walk through sorted transactions and infer withdrawal/deposit from the
    direction of balance change (prev → current).

    Primary:  use _txn_amount + delta direction when available.
    Fallback: when _txn_amount is None but the balance changed, compute the
              amount directly from abs(delta).  This handles cases where the
              regex found the closing balance but missed the transaction column
              (e.g. HDFC CC debit_credit_balance mis-classification).

    If strict_column_amounts is True, skip all balance-delta inference; amounts
    stay only as parsed from statement columns. Internal _txn_amount is still stripped.
    """
    prev_bal = opening_balance

    for txn in transactions:
        explicit_cols = txn.pop("_explicit_wd_dep", False)
        cb = txn.get("closing_balance", 0)
        txn_amt = txn.get("_txn_amount")

        if not strict_column_amounts and not explicit_cols:
            # Only infer when withdrawal/deposit are still unresolved
            if txn.get("withdrawal") is None and txn.get("deposit") is None:
                delta = round(cb - prev_bal, 2)

                # If regex didn't find an explicit amount, derive it from balance delta
                if txn_amt is None and abs(delta) > 0.01:
                    txn_amt = abs(delta)

                if txn_amt:
                    if delta < 0:
                        txn["withdrawal"] = round(txn_amt, 2)
                        txn["deposit"] = None
                    elif delta > 0:
                        txn["withdrawal"] = None
                        txn["deposit"] = round(txn_amt, 2)
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
