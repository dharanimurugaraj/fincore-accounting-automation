"""
Specialized HDFC CC OCR Agent.
Tuned for HDFC Cash Credit account statements.
"""

import json
from app.ocr.base_agent import SYSTEM_PROMPT, _get_schema

def get_hdfc_cc_prompt(text: str, account_id: str) -> str:
    schema = _get_schema("HDFC_CC")
    
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Extract all transactions from this HDFC CC (Cash Credit) bank statement.\n"
        f"Account ID: {account_id}\n\n"
        f"SPECIFIC INSTRUCTIONS FOR HDFC CC:\n"
        f"1. HDFC CC statements often have a 'Value Date' and 'Post Date'. Use 'Post Date' for the 'date' field.\n"
        f"2. Balance in HDFC CC statements is often shown as 'Dr' or 'Cr'.\n"
        f"3. IMPORTANT: Represent the 'balance' as a NEGATIVE number if it is 'Dr' (money owed to bank).\n"
        f"4. Represent the 'balance' as a POSITIVE number if it is 'Cr' (rare for CC, but possible).\n"
        f"5. Identify 'Interest' debits specifically. They usually have 'INTEREST' in narration.\n"
        f"6. Assign a confidence score 0.0-1.0 to each extracted field.\n\n"
        f"REQUIRED OUTPUT SCHEMA:\n{json.dumps(schema, indent=2)}\n\n"
        f"BANK STATEMENT TEXT:\n{text}\n\n"
        f"Return ONLY valid JSON."
    )
    return prompt

def parse_hdfc_cc_result(parsed_json: dict) -> dict:
    # Any HDFC CC specific normalization
    return parsed_json
