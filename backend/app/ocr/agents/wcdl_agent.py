"""
Specialized WCDL Advice Letter OCR Agent.
Tuned for HDFC/UBI WCDL (Working Capital Demand Loan) Advice Letters.
"""

import json
from app.ocr.base_agent import SYSTEM_PROMPT, _get_schema

def get_wcdl_prompt(text: str) -> str:
    schema = _get_schema("WCDL_ADVICE")
    
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Extract all loan details from this WCDL (Working Capital Demand Loan) Advice Letter.\n\n"
        f"SPECIFIC INSTRUCTIONS FOR WCDL ADVICE:\n"
        f"1. Extract the unique Loan Number (e.g., 240LN...).\n"
        f"2. Extract Principal Amount (the loan amount disbursed).\n"
        f"3. Extract ROI (Rate of Interest) — usually around 7-10%.\n"
        f"4. Extract 'Start Date' (Disbursement Date).\n"
        f"5. Extract 'Maturity Date' (Due Date).\n"
        f"6. Check for 'Prepayment' mentions (though usually on advice letter it is N/A).\n"
        f"7. ROI verify: Sometimes expressed as 'Repo + 2.0%'. If so, calculate the final number if possible, or extract the expression.\n\n"
        f"REQUIRED OUTPUT SCHEMA:\n{json.dumps(schema, indent=2)}\n\n"
        f"ADVICE LETTER TEXT:\n{text}\n\n"
        f"Return ONLY valid JSON."
    )
    return prompt

def parse_wcdl_result(parsed_json: dict) -> dict:
    return parsed_json
