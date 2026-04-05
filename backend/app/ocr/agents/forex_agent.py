"""
Specialized Forex Remittance Advice OCR Agent.
Tuned for HDFC/UBI Forex (Import/Export) Remittance Advice Letters.
"""

import json
from app.ocr.base_agent import SYSTEM_PROMPT, _get_schema

def get_forex_prompt(text: str) -> str:
    schema = _get_schema("FOREX_ADVICE")
    
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Extract all import transaction details from this Forex Remittance Advice.\n\n"
        f"SPECIFIC INSTRUCTIONS FOR FOREX ADVICE:\n"
        f"1. Extract 'BOE Date' (Bill of Entry).\n"
        f"2. Extract 'Value Date' (the date the transaction hit the bank).\n"
        f"3. Extract 'Bill Reference' or 'BOE No'.\n"
        f"4. Identify 'Currency' (usually EUR, USD, GBP, AUD).\n"
        f"5. Extract 'FC Amount' (Foreign Currency Amount).\n"
        f"6. Extract 'Bank Rate' (the rate the bank charged for the conversion).\n"
        f"7. Identify 'Bill Commission' and 'SWIFT Charges' if present as separate fields.\n"
        f"8. 'Drawer Name' (The overseas supplier/party).\n\n"
        f"REQUIRED OUTPUT SCHEMA:\n{json.dumps(schema, indent=2)}\n\n"
        f"FOREX ADVICE TEXT:\n{text}\n\n"
        f"Return ONLY valid JSON."
    )
    return prompt

def parse_forex_result(parsed_json: dict) -> dict:
    return parsed_json
