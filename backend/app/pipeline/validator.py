import pdfplumber
import re
import os
from typing import Dict, Any

class PDFValidator:
    """ Checks if a PDF is a valid bank statement with supported formats. """

    def validate(self, path: str) -> Dict[str, Any]:
        """
        Check if PDF is a valid bank statement
        Max 60 pages per PDF enforced here
        """
        if not os.path.exists(path):
            return {"valid": False, "reason": f"File not found at {path}"}

        try:
            with pdfplumber.open(path) as pdf:
                page_count = len(pdf.pages)
                
                # Enforce 60 page limit per PDF
                if page_count > 60:
                    return {
                        "valid": False,
                        "reason": f"PDF has {page_count} pages. Max 60 allowed."
                    }
                
                # Extract first page text for validation
                first_page = pdf.pages[0].extract_text()
                if not first_page:
                    return {
                        "valid": False,
                        "reason": "Could not extract text from the first page. Is it a scanned image?"
                    }

            # Validation checks
            checks = {
                "has_hdfc": "HDFC" in first_page.upper(),
                "has_sbi": "STATE BANK" in first_page.upper(),
                "has_icici": "ICICI" in first_page.upper(),
                "has_statement": "STATEMENT" in first_page.upper(),
                "has_balance": any(x in first_page.upper() for x in ["BALANCE", "CLOSING"]),
                "has_account": any(x in first_page.upper() for x in ["ACCOUNT", "A/C"]),
            }
            
            is_bank = checks["has_statement"] and (checks["has_balance"] or checks["has_account"])
            
            if not is_bank:
                return {
                    "valid": False,
                    "reason": "Not a bank statement PDF (Missing identifiers)"
                }
            
            bank = "HDFC" if checks["has_hdfc"] else \
                   "SBI" if checks["has_sbi"] else \
                   "ICICI" if checks["has_icici"] else "UNIVERSAL" # Changed from UNKNOWN to UNIVERSAL
            
            # Extract account number
            acct_match = re.search(
                r'(?:Account\s*No|A/c\s*No|Account\s*Number)\s*[:\s-]+(\d{9,16})',
                first_page,
                re.IGNORECASE
            )
            account_number = acct_match.group(1) if acct_match else "UNKNOWN"
            
            return {
                "valid": True,
                "bank": bank,
                "account_number": account_number,
                "pages": page_count,
                "path": path
            }

        except Exception as e:
            return {
                "valid": False,
                "reason": f"Error opening PDF: {str(e)}"
            }
