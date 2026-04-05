"""
Specialized HDFC CA OCR Agent.
Tuned for HDFC Current Account (CA) statements.
"""

import json
from app.ocr.base_agent import SYSTEM_PROMPT, _get_schema

def get_hdfc_ca_prompt(text: str, account_id: str) -> str:
    schema = _get_schema("HDFC_CURRENT")
    
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Extract all transactions from this HDFC Current Account statement.\n"
        f"Account ID: {account_id}\n"
        f"Bank: HDFC Bank\n\n"
        f"SPECIFIC INSTRUCTIONS FOR HDFC CURRENT:\n"
        f"1. Dates in HDFC CA are generally DD-MM-YYYY format in the text. Convert them to YYYY-MM-DD.\n"
        f"2. Current accounts usually have a positive balance (Cr). This should be represented as a POSITIVE balance.\n"
        f"3. Any overdraft on the CA (Dr balance) must be shown as NEGATIVE.\n"
        f"4. Identify EMI debits, RTGS/NEFT charges, and 'BULK TXN' as specific categories.\n\n"
        f"REQUIRED OUTPUT SCHEMA:\n{json.dumps(schema, indent=2)}\n\n"
        f"BANK STATEMENT TEXT:\n{text}\n\n"
        f"Return ONLY valid JSON."
    )
    return prompt

def parse_hdfc_ca_result(parsed_json: dict) -> dict:
    return parsed_json
