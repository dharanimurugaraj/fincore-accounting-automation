from typing import List

# Classify each transaction automatically
# based on narration patterns

NARRATION_PATTERNS = {
    "WCDL_DRAWDOWN": [
        "WCDL", "DEMAND LOAN", "DRAWDOWN",
        "WCDL CREDIT"
    ],
    "WCDL_PREPAYMENT": [
        "WCDL REPAY", "DEMAND LOAN REPAY",
        "PREPAYMENT"
    ],
    "CC_INTEREST": [
        "INT COLL", "INTEREST COLLECTED",
        "CC INTEREST", "INTEREST DEBIT",
        "INT COLLECTED-CC ACCOUNT", "INTEREST CHARGED"
    ],
    "BANK_CHARGE": [
        "NEFT CHGS", "RTGS CHGS", "DD CHARGES",
        "BULK TXN CHGS", "COMM ON GUARANTEE",
        "DD/MC CANCELLATION", "ROCFEE",
        "HDFC_ROCFEE", "SERVICE CHARGES",
        "PROCESSING FEE", "ROC FEE",
        "ANNUAL MTC", "CARD FEE", "GST ON SERVICE CHARGES"
    ],
    "EMI_DEBIT": [
        "EMI", "LOAN REPAY", "ECS",
        "NACH DEBIT", "EMI -", "LOAN REPAYMENT"
    ],
    "FOREX_REMITTANCE": [
        "FOREX", "OUTWARD REMITTANCE",
        "IMPORT", "BOE", "FCY"
    ],
    "UPI_PAYMENT": ["UPI-", "UPI/", "MOBILE PAY"],
    "NEFT_TRANSFER": ["NEFT-", "NEFT/"],
    "IMPS_TRANSFER": ["IMPS-", "IMPS/"],
    "SALARY_CREDIT": ["SALARY", "LOAN SETTLEMENT", "REIMBURSEMENT"],
    "ATM_WITHDRAWAL": ["ATM-", "CASH WITHDRAWAL"],
    "INTEREST_CREDIT": ["INTEREST CREDIT", "INT.CREDIT"],
}

def classify_transaction(narration: str) -> str:
    """Classifies a transaction based on narration patterns."""
    if not narration:
        return "OTHER"
    
    narration_upper = narration.upper()
    for category, patterns in NARRATION_PATTERNS.items():
        if any(p in narration_upper for p in patterns):
            return category
    return "OTHER"
