"""
Abstract base OCR agent + the main extract_pdf entry point.
Dispatches to text-based (pdfplumber → Gemini text) or image-based (Gemini Vision) extraction.
"""

import json
import time
import re as _re
from typing import Optional

import pdfplumber

from app.core.config import settings

# ── Initialize Gemini if available ────────────────────────────────────────────

GEMINI_AVAILABLE = settings.gemini_available
model = None

if GEMINI_AVAILABLE:
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")

SYSTEM_PROMPT = (
    "You are a precise financial data extraction engine for Indian bank statements. "
    "Extract EVERY transaction exactly as it appears. Do not summarise, skip, or combine rows. "
    "Return ONLY valid JSON matching the exact schema provided. No commentary, no markdown fences."
)

# ── Hardcoded charge classification rules ─────────────────────────────────────

CHARGE_RULES: list[tuple[str, str]] = [
    ("COMM ON GUARANTEE AMENDMENT", "Recurring"),
    ("BULK TXN CHGS INCL GST", "Recurring"),
    ("NEFT CHGS BRN INCL GST", "Recurring"),
    ("COMM ON DIRECT PAYMENT OF IMP BILL", "Recurring"),
    ("DD CHARGES INCL GST", "Recurring"),
    ("DD/MC CANCELLATION CHARGE", "Recurring"),
    ("EDC ANNUAL RENTAL", "Non-Recurring"),
    ("HDFC_ROCFEE", "Non-Recurring"),
    ("ROC FEE", "Non-Recurring"),
    ("PENAL", "Penal"),
]


def classify_charge(narration: str) -> Optional[str]:
    """Classify a bank charge narration using hardcoded rules."""
    upper = narration.upper()
    for keyword, category in CHARGE_RULES:
        if keyword.upper() in upper:
            return category
    return None


# ── Main extraction entry point ───────────────────────────────────────────────

def extract_pdf(pdf_path: str, account_meta: dict) -> dict:
    """Extract structured transaction data from a bank statement PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    is_text_pdf = len(full_text.strip()) > 500

    if is_text_pdf:
        result = _extract_from_text(full_text, account_meta)
    else:
        result = _extract_from_images(pdf_path, account_meta)

    result = _post_process(result, account_meta)
    return result


def _extract_from_text(text: str, account_meta: dict) -> dict:
    schema = _get_schema(account_meta["account_type"])
    if not model:
        return _build_empty_result(account_meta)

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Extract all transactions from this Indian bank statement.\n"
        f"Account Type: {account_meta['account_type']}\n"
        f"Account ID: {account_meta['account_id']}\n\n"
        f"REQUIRED OUTPUT SCHEMA:\n{json.dumps(schema, indent=2)}\n\n"
        f"BANK STATEMENT TEXT:\n{text}\n\n"
        f"Rules:\n"
        f"1. Extract EVERY row — do not skip any transaction\n"
        f"2. Dates must be ISO format: YYYY-MM-DD\n"
        f"3. Debit amounts are positive numbers (money going out)\n"
        f"4. Credit amounts are positive numbers (money coming in)\n"
        f"5. CC balance is NEGATIVE when money is borrowed (CC drawn)\n"
        f"6. Assign confidence 0.0-1.0 per field\n"
        f"7. Classify charges using the hardcoded rules\n"
        f"8. Return ONLY the JSON object, no other text"
    )

    response = _call_gemini_with_retry(prompt)
    if response is None:
        return _build_empty_result(account_meta)

    raw_text = _strip_markdown_fences(response.text.strip())
    try:
        parsed = json.loads(raw_text)
        return _normalize_result(parsed, account_meta)
    except json.JSONDecodeError:
        return _build_empty_result(account_meta)


def _extract_from_images(pdf_path: str, account_meta: dict) -> dict:
    if not model:
        return _build_empty_result(account_meta)

    images = []
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path, dpi=200)
    except ImportError:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                img = page.to_image(resolution=200)
                images.append(img.original)

    schema = _get_schema(account_meta["account_type"])
    prompt_text = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Extract all transactions from these bank statement pages.\n"
        f"Account Type: {account_meta['account_type']}\n"
        f"Return JSON matching this schema:\n{json.dumps(schema)}\n"
        f"Return ONLY JSON."
    )

    content_parts = list(images) + [prompt_text]
    response = _call_gemini_with_retry(content_parts)
    if response is None:
        return _build_empty_result(account_meta)

    raw_text = _strip_markdown_fences(response.text.strip())
    try:
        parsed = json.loads(raw_text)
        return _normalize_result(parsed, account_meta)
    except json.JSONDecodeError:
        return _build_empty_result(account_meta)


def _call_gemini_with_retry(content, max_retries: int = 4):
    for attempt in range(max_retries):
        try:
            return model.generate_content(content)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "ResourceExhausted" in err_str:
                wait_match = _re.search(r"retry in (\d+)", err_str)
                wait_secs = int(wait_match.group(1)) + 2 if wait_match else (30 * (attempt + 1))
                print(f"[ocr_agent] Rate limited (attempt {attempt+1}/{max_retries}), waiting {wait_secs}s...")
                time.sleep(wait_secs)
            else:
                print(f"[ocr_agent] Gemini call failed: {e}")
                return None
    return None


def _strip_markdown_fences(text: str) -> str:
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:]) if len(lines) > 1 else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _normalize_result(parsed, account_meta: dict) -> dict:
    acct_type = account_meta["account_type"]
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        if acct_type in ("WCDL", "WCDL_ADVICE"):
            return {"loans": parsed, "overall_confidence": 0.85}
        if acct_type in ("FOREX", "FOREX_ADVICE"):
            return {"transactions": parsed, "overall_confidence": 0.85}
        return {
            "account_id": account_meta.get("account_id", ""),
            "account_type": acct_type,
            "statement_period": {"from": "", "to": ""},
            "opening_balance": 0, "closing_balance": 0,
            "transactions": parsed, "charges_summary": [],
            "overall_confidence": 0.85,
        }
    return _build_empty_result(account_meta)


def _post_process(result: dict, account_meta: dict) -> dict:
    acct_type = account_meta["account_type"]

    if acct_type in ("CC", "CURRENT", "SAVINGS", "OD", "HDFC_CC", "HDFC_CURRENT", "UBI_CURRENT"):
        transactions = result.get("transactions", [])
        charges_summary = []
        field_confidences = []

        for txn in transactions:
            conf = txn.get("confidence", 0.95)
            field_confidences.append(conf)
            narration = txn.get("narration", "")
            charge_cat = classify_charge(narration)
            if charge_cat:
                txn["category"] = "Charges"
                charges_summary.append({
                    "date": txn.get("date"), "description": narration,
                    "amount": txn.get("debit") or txn.get("credit") or 0,
                    "dr_cr": "Dr" if txn.get("debit") else "Cr",
                    "category": charge_cat, "confidence": conf,
                })

        result["charges_summary"] = charges_summary
        result["overall_confidence"] = min(field_confidences) if field_confidences else 0.50

    elif acct_type in ("WCDL", "WCDL_ADVICE"):
        loans = result.get("loans", [])
        confs = [loan.get("confidence", 0.95) for loan in loans]
        result["overall_confidence"] = min(confs) if confs else 0.50

    elif acct_type in ("FOREX", "FOREX_ADVICE"):
        txns = result.get("transactions", [])
        confs = [txn.get("confidence", 0.95) for txn in txns]
        result["overall_confidence"] = min(confs) if confs else 0.50

    return result


def _get_schema(account_type: str) -> dict:
    base_schema = {
        "account_id": "string", "account_type": "string",
        "statement_period": {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"},
        "opening_balance": "float", "closing_balance": "float",
        "transactions": [{"date": "YYYY-MM-DD", "narration": "string",
                          "reference": "string or null", "debit": "float or null",
                          "credit": "float or null", "balance": "float",
                          "category": "Credit|Debit|Charges|Interest|EMI|Balance",
                          "confidence": "float 0.0-1.0"}],
        "overall_confidence": "float 0.0-1.0",
    }
    if account_type in ("WCDL", "WCDL_ADVICE"):
        return {"loans": [{"loan_number": "string", "start_date": "YYYY-MM-DD",
                           "maturity_date": "YYYY-MM-DD", "prepayment_date": "YYYY-MM-DD or null",
                           "principal": "float", "roi": "float", "confidence": "float"}],
                "overall_confidence": "float"}
    if account_type in ("FOREX", "FOREX_ADVICE"):
        return {"transactions": [{"boe_date": "YYYY-MM-DD", "value_date": "YYYY-MM-DD",
                                  "drawer_name": "string", "bill_reference": "string",
                                  "currency": "EUR|USD|GBP|AUD", "fc_amount": "float",
                                  "bank_rate": "float", "bill_commission": "float",
                                  "swift_charges": "float", "confidence": "float"}],
                "overall_confidence": "float"}
    return base_schema


def _build_empty_result(account_meta: dict) -> dict:
    acct_type = account_meta["account_type"]
    if acct_type in ("WCDL", "WCDL_ADVICE"):
        return {"loans": [], "overall_confidence": 0.0}
    if acct_type in ("FOREX", "FOREX_ADVICE"):
        return {"transactions": [], "overall_confidence": 0.0}
    return {
        "account_id": account_meta.get("account_id", ""),
        "account_type": acct_type,
        "statement_period": {"from": "", "to": ""},
        "opening_balance": 0, "closing_balance": 0,
        "transactions": [], "charges_summary": [],
        "overall_confidence": 0.0,
    }
