import math
from typing import List, Dict, Any
from datetime import datetime

class FinCoreComputationEngine:
    
    def compute_cc_daily_interest(
        self,
        closing_balance: float,
        roi_percent: float,
        date: str = ""
    ) -> float:
        """
        CC Daily Interest = Closing Balance × ROI ÷ 365
        Only applies when balance is negative (CC drawn).
        """
        if closing_balance >= 0:
            return 0.0
        
        # Use absolute value for calculation
        balance = abs(closing_balance)
        daily_interest = (balance * roi_percent) / (100 * 365)
        return round(daily_interest, 2)
    
    def compute_wcdl_interest(
        self,
        principal: float,
        roi_percent: float,
        tenure_days: int
    ) -> float:
        """
        WCDL Interest = Principal × ROI × Tenure_Days ÷ 365
        """
        interest = (principal * roi_percent * tenure_days) / (100 * 365)
        return round(interest, 2)
    
    def compute_monthly_cc_interest(
        self,
        daily_balances: List[float],
        roi_percent: float
    ) -> float:
        """
        Sum of all daily CC interest for the month.
        """
        total = 0.0
        for balance in daily_balances:
            total += self.compute_cc_daily_interest(balance, roi_percent)
        return round(total, 2)
    
    def compute_finance_cost_percent(
        self,
        total_monthly_interest: float,
        average_utilisation: float
    ) -> float:
        """
        Finance Cost % = (Total Monthly Interest ÷ Avg Utilisation) × 12
        """
        if average_utilisation == 0:
            return 0.0
        finance_cost = (total_monthly_interest / average_utilisation) * 12
        return round(finance_cost * 100, 4)
    
    def compute_average_utilisation(
        self,
        daily_balances: List[float]
    ) -> float:
        """
        Average of all daily closing balances for the month.
        Only include negative balances (days when CC is drawn).
        """
        drawn_balances = [abs(b) for b in daily_balances if b < 0]
        if not drawn_balances:
            return 0.0
        return round(sum(drawn_balances) / len(daily_balances), 2)
    
    def verify_actual_roi(
        self,
        interest_charged: float,
        principal: float,
        tenure_days: int
    ) -> float:
        """
        Actual ROI = (Interest Charged ÷ Principal) ÷ Tenure_Days × 365
        """
        if principal == 0 or tenure_days == 0:
            return 0.0
        actual_roi = (interest_charged / principal) / tenure_days * 365
        return round(actual_roi * 100, 4)

    def compute_notional_interest_loss(
        self,
        daily_balances: List[float],
        roi_percent: float
    ) -> float:
        """
        Interest Loss = Avg Positive Balance × CC ROI × Days ÷ 365
        Applies to Current accounts with positive balance.
        """
        positive_balances = [b for b in daily_balances if b > 0]
        if not positive_balances:
            return 0.0
        avg_positive = sum(positive_balances) / len(positive_balances)
        notional_loss = (avg_positive * roi_percent * len(positive_balances)) / (100 * 365)
        return round(notional_loss, 2)

    def compute_ai_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model_name: str = "Gemini 1.5 Flash"
    ) -> float:
        """
        Calculates LLM cost based on token usage.
        Rate formula: (prompt / 1M * input_rate) + (completion / 1M * output_rate)
        """
        from .ai_config import get_model_rate
        
        rates = get_model_rate(model_name)
        input_rate = rates.get("input", 0.075)
        output_rate = rates.get("output", 0.3)
        
        cost = (prompt_tokens / 1_000_000 * input_rate) + (completion_tokens / 1_000_000 * output_rate)
        return round(cost, 6) # Higher precision for small costs

    def compute_all(self, accounts_data: List[Dict], wcdl_data: List[Dict], ai_usage: List[Dict] = None) -> Dict[str, Any]:
        """ Wrapper for running all formulas on processed accounts. """
        total_cc_interest = 0.0
        total_wcdl_interest = 0.0
        total_avg_utilisation = 0.0
        total_ai_cost = 0.0
        total_notional_loss = 0.0
        
        # CC Interests
        for acct in accounts_data:
            roi = acct.get("cc_roi_percent") or 7.60
            txns = acct.get("full_month_transactions") or acct.get("transactions", [])
            balances = [txn.get("closing_balance") if txn.get("closing_balance") is not None else 0 for txn in txns]
            total_cc_interest += self.compute_monthly_cc_interest(balances, roi)
            avg_util = self.compute_average_utilisation(balances)
            total_avg_utilisation += avg_util
            total_notional_loss += self.compute_notional_interest_loss(balances, roi)
            
        # WCDL Interests
        for loan in wcdl_data:
            interest = self.compute_wcdl_interest(
                loan.get("principal") or 0,
                loan.get("roi_percent") or 0,
                loan.get("tenure_days") or 0
            )
            total_wcdl_interest += interest
            
        # AI Costs
        if ai_usage:
            for usage in ai_usage:
                total_ai_cost += self.compute_ai_cost(
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                    usage.get("model", usage.get("model", "OpenRouter"))
                )
            
        total_interest = total_cc_interest + total_wcdl_interest
        finance_cost_pct = self.compute_finance_cost_percent(total_interest, total_avg_utilisation)
        
        # Cross-validation (Phase 6)
        # Verify: Opening + Deposits - Withdrawals = Closing
        for acct in accounts_data:
            txns = acct.get("transactions", [])
            if not txns: continue
            
            calc_deposits = sum(t.get("deposit") or 0 for t in txns)
            calc_withdrawals = sum(t.get("withdrawal") or 0 for t in txns)
            opening = acct.get("opening_balance") or 0
            closing = acct.get("closing_balance")
            
            if closing is not None:
                expected_closing = opening + calc_deposits - calc_withdrawals
                diff = abs(float(expected_closing) - float(closing))
                
                acct["_reconciliation"] = {
                    "status": "PASS" if diff <= 1.0 else ("WARN" if diff <= 10.0 else "FAIL"),
                    "diff": round(diff, 2),
                    "expected_closing": round(expected_closing, 2),
                    "actual_closing": round(closing, 2)
                }
                
                if acct["_reconciliation"]["status"] == "FAIL":
                    print(f"[RECONCILE] FAIL for {acct.get('bank_name')}: Diff of {diff}")

        return {
            "total_cc_interest": total_cc_interest,
            "total_notional_loss": total_notional_loss,
            "total_wcdl_interest": total_wcdl_interest,
            "total_interest": total_interest,
            "average_utilisation": total_avg_utilisation,
            "finance_cost_pct": finance_cost_pct,
            "total_ai_cost": round(total_ai_cost, 4),
            "roi_status": "OK" if finance_cost_pct < 10 else "FLAG"
        }
