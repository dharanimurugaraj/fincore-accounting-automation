"""
Routes PDF to correct OCR agent based on bank + account type.
Dynamically classifies bank statements by extracting metadata from PDF text.

Uses: pdfplumber first-page text → regex heuristics → filename fallback → Gemini Vision.
"""

import re
import os
from dataclasses import dataclass, asdict
from typing import Optional

import pdfplumber

from app.core.config import settings


@dataclass
class AccountMeta:
    bank: str              # "HDFC", "UBI", "SBI", etc.
    account_type: str      # "CC", "CURRENT", "WCDL", "FOREX", etc.
    account_id: str        # Actual account number from the PDF
    account_label: str     # Human-readable short label
    sheet_name: str        # Excel sheet name (max 31 chars)
    confidence: float      # 0.0 to 1.0

    def to_dict(self) -> dict:
        return asdict(self)


def _make_label(bank: str, account_id: str, account_type: str) -> str:
    short_id = account_id[-6:] if len(account_id) > 6 else account_id
    return f"{bank}-{short_id} {account_type}"


def _make_sheet_name(bank: str, account_id: str, account_type: str) -> str:
    short_id = account_id[-6:] if len(account_id) > 6 else account_id
    type_labels = {
        "CC": "CC AC", "CURRENT": "Current AC", "SAVINGS": "Savings AC",
        "WCDL": "WCDL Loan AC", "FOREX": "Forex Remittance",
    }
    suffix = type_labels.get(account_type, f"{account_type} AC")
    return f"{bank}-{short_id} {suffix}"[:31]


# ── Bank & Account Type Patterns ──────────────────────────────────────────────

BANK_PATTERNS = [
    (re.compile(r"hdfc\s*bank|hdfc\s*ltd", re.I), "HDFC"),
    (re.compile(r"union\s*bank\s*of\s*india|ubi\b", re.I), "UBI"),
    (re.compile(r"state\s*bank\s*of\s*india|sbi\b", re.I), "SBI"),
    (re.compile(r"icici\s*bank", re.I), "ICICI"),
    (re.compile(r"axis\s*bank", re.I), "AXIS"),
    (re.compile(r"kotak\s*mahindra", re.I), "KOTAK"),
    (re.compile(r"canara\s*bank", re.I), "CANARA"),
    (re.compile(r"bank\s*of\s*baroda|bob\b", re.I), "BOB"),
    (re.compile(r"punjab\s*national\s*bank|pnb\b", re.I), "PNB"),
    (re.compile(r"yes\s*bank", re.I), "YES"),
    (re.compile(r"indusind\s*bank", re.I), "INDUSIND"),
    (re.compile(r"federal\s*bank", re.I), "FEDERAL"),
]

TYPE_PATTERNS = [
    (re.compile(r"cash\s*credit|cc\s*a/c|cc\s*account", re.I), "CC"),
    (re.compile(r"current\s*account|current\s*a/c", re.I), "CURRENT"),
    (re.compile(r"savings?\s*account|savings?\s*a/c|sb\s*a/c", re.I), "SAVINGS"),
    (re.compile(r"working\s*capital\s*demand\s*loan|wcdl|demand\s*loan\s*advice", re.I), "WCDL"),
    (re.compile(r"outward\s*remittance|forex|import\s*bill|remittance\s*advice", re.I), "FOREX"),
    (re.compile(r"over\s*draft|od\s*a/c|od\s*account", re.I), "OD"),
    (re.compile(r"term\s*loan|tl\s*a/c", re.I), "TERM_LOAN"),
    (re.compile(r"fixed\s*deposit|fd\s*a/c", re.I), "FD"),
]

ACCOUNT_NUMBER_RE = re.compile(r"\b(\d{9,18})\b")
LOAN_NUMBER_RE = re.compile(r"\b(\d{3}[A-Z]{2}\d{11,})\b")

FILENAME_BANK_PATTERNS = [
    (re.compile(r"hdfc", re.I), "HDFC"),
    (re.compile(r"ubi|union", re.I), "UBI"),
    (re.compile(r"sbi|state\s*bank", re.I), "SBI"),
    (re.compile(r"icici", re.I), "ICICI"),
    (re.compile(r"axis", re.I), "AXIS"),
    (re.compile(r"kotak", re.I), "KOTAK"),
    (re.compile(r"canara", re.I), "CANARA"),
]

FILENAME_TYPE_PATTERNS = [
    (re.compile(r"cc|cash.?credit", re.I), "CC"),
    (re.compile(r"current|ca\b", re.I), "CURRENT"),
    (re.compile(r"wcdl|demand.?loan", re.I), "WCDL"),
    (re.compile(r"forex|remittance|import", re.I), "FOREX"),
    (re.compile(r"od|over.?draft", re.I), "OD"),
    (re.compile(r"savings|sb\b", re.I), "SAVINGS"),
]


def classify_pdf(pdf_path: str, filename: str) -> AccountMeta:
    """Classify a bank statement PDF and extract account metadata dynamically."""
    first_page_text = _extract_first_page_text(pdf_path)

    if first_page_text:
        result = _classify_from_text_dynamic(first_page_text)
        if result and result.confidence >= 0.80:
            return result

    result = _classify_from_filename(filename)
    if result and result.confidence >= 0.70:
        return result

    if first_page_text and settings.gemini_available:
        vision_result = _classify_with_gemini(pdf_path)
        if vision_result:
            return vision_result

    if result:
        result.confidence = 0.50
        return result

    return AccountMeta(
        bank="UNKNOWN", account_type="UNKNOWN", account_id="UNKNOWN",
        account_label="Unknown Account", sheet_name="Unknown Account", confidence=0.20,
    )


def _classify_from_text_dynamic(text: str) -> Optional[AccountMeta]:
    text_lower = text.lower()
    raw_text = text

    bank = None
    for pattern, bank_name in BANK_PATTERNS:
        if pattern.search(text_lower):
            bank = bank_name
            break
    if not bank:
        bank = "UNKNOWN"

    acct_type = None
    for pattern, type_name in TYPE_PATTERNS:
        if pattern.search(text_lower):
            acct_type = type_name
            break
    if not acct_type:
        acct_type = "CURRENT"

    acct_id = _extract_account_number(raw_text, acct_type)

    confidence = 0.60
    if bank != "UNKNOWN":
        confidence += 0.15
    if acct_type != "CURRENT" or "current" in text_lower:
        confidence += 0.10
    if acct_id != "UNKNOWN":
        confidence += 0.10

    label = _make_label(bank, acct_id, acct_type)
    sheet = _make_sheet_name(bank, acct_id, acct_type)

    return AccountMeta(bank=bank, account_type=acct_type, account_id=acct_id,
                       account_label=label, sheet_name=sheet, confidence=min(confidence, 0.99))


def _extract_account_number(text: str, acct_type: str) -> str:
    if acct_type == "WCDL":
        loan_matches = LOAN_NUMBER_RE.findall(text)
        if loan_matches:
            return loan_matches[0]
    if acct_type == "FOREX":
        return "FOREX"

    labeled = re.search(
        r"(?:account\s*(?:no|number|#)|a/c\s*(?:no|number|#))\s*[:\-]?\s*(\d{6,18})",
        text, re.I
    )
    if labeled:
        return labeled.group(1)

    candidates = ACCOUNT_NUMBER_RE.findall(text)
    valid = [c for c in candidates if len(c) >= 9 and not c.startswith(("19", "20"))]
    if valid:
        return valid[0]

    short = re.findall(r"\b(\d{3,8})\b", text)
    if short:
        return short[0]

    return "UNKNOWN"


def _classify_from_filename(filename: str) -> Optional[AccountMeta]:
    name = os.path.splitext(filename)[0]
    bank = "UNKNOWN"
    for pattern, bank_name in FILENAME_BANK_PATTERNS:
        if pattern.search(name):
            bank = bank_name
            break

    acct_type = "CURRENT"
    for pattern, type_name in FILENAME_TYPE_PATTERNS:
        if pattern.search(name):
            acct_type = type_name
            break

    numbers = re.findall(r"\d{3,}", name)
    acct_id = numbers[0] if numbers else "UNKNOWN"

    if bank == "UNKNOWN" and acct_type == "CURRENT" and acct_id == "UNKNOWN":
        return None

    confidence = 0.55
    if bank != "UNKNOWN":
        confidence += 0.10
    if acct_id != "UNKNOWN":
        confidence += 0.10

    label = _make_label(bank, acct_id, acct_type)
    sheet = _make_sheet_name(bank, acct_id, acct_type)
    return AccountMeta(bank=bank, account_type=acct_type, account_id=acct_id,
                       account_label=label, sheet_name=sheet, confidence=confidence)


def _extract_first_page_text(pdf_path: str) -> str:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                return pdf.pages[0].extract_text() or ""
    except Exception:
        pass
    return ""


def _classify_with_gemini(pdf_path: str) -> Optional[AccountMeta]:
    """Last-resort: ask Gemini Vision to classify the PDF."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-2.5-flash-lite")

        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return None
            page = pdf.pages[0]
            img = page.to_image(resolution=150)
            pil_image = img.original

        prompt = (
            "This is a page from an Indian bank document. "
            "Extract: BANK_NAME|ACCOUNT_TYPE|ACCOUNT_NUMBER\n"
            "Reply with ONLY the pipe-separated line."
        )

        response = gemini_model.generate_content([pil_image, prompt])
        parts = response.text.strip().split("|")
        if len(parts) >= 3:
            bank = parts[0].strip().upper()
            acct_type = parts[1].strip().upper()
            acct_id = parts[2].strip()
            valid_types = {"CC", "CURRENT", "SAVINGS", "WCDL", "FOREX", "OD", "TERM_LOAN", "FD"}
            if acct_type not in valid_types:
                acct_type = "CURRENT"
            label = _make_label(bank, acct_id, acct_type)
            sheet = _make_sheet_name(bank, acct_id, acct_type)
            return AccountMeta(bank=bank, account_type=acct_type, account_id=acct_id,
                               account_label=label, sheet_name=sheet, confidence=0.88)
    except Exception:
        pass
    return None
