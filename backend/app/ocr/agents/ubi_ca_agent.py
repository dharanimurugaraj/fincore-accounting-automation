"""
Specialized UBI CA OCR Agent.
Tuned for Union Bank of India (UBI) Current Account (CA) statements.
"""

import json
from app.ocr.base_agent import SYSTEM_PROMPT, _get_schema

def get_ubi_ca_prompt(text: str, account_id: str) -> str:
    schema = _get_schema("UBI_CURRENT")
    
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Extract all transactions from this Union Bank of India (UBI) Current Account statement.\n"
        f"Account ID: {account_id}\n\n"
        f"SPECIFIC INSTRUCTIONS FOR UBI CURRENT:\n"
        f"1. UBI statements often have a narrow table or split narration. Ensure narration is fully captured.\n"
        f"2. Union Bank balance convention: DB for positive balance, CR for overdraft (this can vary, keep extracted logic but check sign).\n"
        f"3. IMPORTANT: Represent the 'balance' as a POSITIVE number for a healthy current account balance.\n"
        f"4. If 'overdrawn' or 'limit', show as NEGATIVE.\n"
        f"5. Categorise standard bank fees as 'Charges'.\n\n"
        f"REQUIRED OUTPUT SCHEMA:\n{json.dumps(schema, indent=2)}\n\n"
        f"BANK STATEMENT TEXT:\n{text}\n\n"
        f"Return ONLY valid JSON."
    )
    return prompt

def parse_ubi_ca_result(parsed_json: dict) -> dict:
    return parsed_json
