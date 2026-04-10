import math
from typing import List, Dict, Any
from datetime import datetime


def _eod_closing_balances_per_date(full_month_txns: List[Dict]) -> List[float]:
    """
    One signed closing balance per calendar date: the *last* row for that date
    (same rule as working sheet Positive Bal / Days). Avoids counting every
    intra-day line as a separate day for CC interest / avg utilisation.
    """
    if not full_month_txns:
        return []
    last_idx: Dict[str, int] = {}
    for i, t in enumerate(full_month_txns):
        dk = (t.get("date") or "")[:10]
        if dk:
            last_idx[dk] = i
    out: List[float] = []
    for dk in sorted(last_idx.keys()):
        row = full_month_txns[last_idx[dk]]
        out.append(float(row.get("closing_balance") or 0))
    return out


class FinCoreComputationEngine:
    
    def compute_cc_daily_interest(
        self,
        closing_balance: float,
        roi_percent: float,
        date: str = ""
    ) -> float:
        """
        CC Daily Interest = Closing Balance × ROI ÷ 365
        Note: The PRD prefers SUM(daily) * ROI / 365. 
        This individual method is for display/row-level estimates.
        """
        if closing_balance >= 0:
            return 0.0
        
        balance = abs(closing_balance)
        return (balance * roi_percent) / (100 * 365)
    
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
        SUM(daily_cc_utilisation) * ROI / 365
        Strictly follows PRD v1.1 formula. Round only at the end.
        """
        drawn_sum = sum(abs(b) for b in daily_balances if b < 0)
        interest = (drawn_sum * roi_percent) / (100 * 365)
        return round(interest, 2)
    
    def compute_finance_cost_percent(
        self,
        total_monthly_interest: float,
        average_utilisation: float,
        days_in_period: int = 30,
    ) -> float:
        """
        Finance Cost % (annualised) = (Interest / Avg_Util) × (365 / days_in_period)

        PRD constraint: use actual days/365 — NOT 12-month approximation.
        """
        if average_utilisation == 0:
            return 0.0
        # Annualised effective rate
        finance_cost = (total_monthly_interest / average_utilisation) * (365 / max(days_in_period, 1))
        return round(float(finance_cost) * 100, 4)

    def compute_blended_roi(
        self,
        total_interest: float,
        total_avg_utilisation: float,
        days_in_period: int,
    ) -> float:
        """
        Blended ROI % = (Total_Interest / Total_Avg_Util) × (365 / days)
        This is the back-calculated effective cost across ALL facilities.
        A higher result vs sanctioned ROI indicates product mix (e.g. CC drawing pattern).
        """
        if total_avg_utilisation == 0 or days_in_period == 0:
            return 0.0
        return round((total_interest / total_avg_utilisation) * (365 / days_in_period) * 100, 4)
    
    def compute_average_utilisation(
        self,
        daily_balances: List[float]
    ) -> float:
        """
        Average Utilisation = SUM(daily_cc_utilisation) / Total_Days_In_Month
        Note: Total_Days_In_Month includes both drawn and positive days.
        """
        if not daily_balances:
            return 0.0
        drawn_sum = sum(abs(b) for b in daily_balances if b < 0)
        return round(drawn_sum / len(daily_balances), 2)
    
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
        Interest Loss = (SUM(daily_positive_balances)) * ROI / 365
        Equivalent to: Avg Positive Balance * ROI * Positive_Days / 365
        """
        positive_sum = sum(b for b in daily_balances if b > 0)
        notional_loss = (positive_sum * roi_percent) / (100 * 365)
        return round(notional_loss, 2)

    def compute_ai_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model_name: str = "Gemini 1.5 Flash"
    ) -> float:
        """
        Calculates LLM cost based on token usage.
        """
        from .ai_config import get_model_rate
        
        rates = get_model_rate(model_name)
        input_rate = rates.get("input", 0.075)
        output_rate = rates.get("output", 0.3)
        
        cost = (prompt_tokens / 1_000_000 * input_rate) + (completion_tokens / 1_000_000 * output_rate)
        return round(cost, 6)

    def compute_all(
        self,
        accounts_data: List[Dict],
        wcdl_data: List[Dict],
        ai_usage: List[Dict] = None,
        days_in_period: int = 30,
    ) -> Dict[str, Any]:
        """
        Master computation wrapper.

        Args:
            accounts_data:  list of extracted account dicts (with full_month_transactions)
            wcdl_data:      list of WCDL loan dicts (raw rows from DB or pipeline input)
            ai_usage:       optional list of AI usage dicts for cost tracking
            days_in_period: actual calendar days in the statement period (28/29/30/31)
        """
        total_cc_interest     = 0.0
        total_wcdl_interest   = 0.0
        total_avg_utilisation = 0.0
        total_ai_cost         = 0.0
        total_notional_loss   = 0.0

        # ── CC Interest (per account, only for CC-type accounts) ─────────────
        for acct in accounts_data:
            if acct.get("account_type", "CC") not in ("CC", "OD"):
                continue  # CA / FX accounts don't have CC drawing interest
            roi = acct.get("cc_roi_percent") or 7.60
            txns = acct.get("full_month_transactions") or acct.get("transactions", [])
            balances = _eod_closing_balances_per_date(txns)
            total_cc_interest   += self.compute_monthly_cc_interest(balances, roi)
            total_avg_utilisation += self.compute_average_utilisation(balances)
            total_notional_loss += self.compute_notional_interest_loss(balances, roi)

        # ── WCDL Interests (actual days / 365) ───────────────────────────────
        for loan in wcdl_data:
            interest = self.compute_wcdl_interest(
                loan.get("principal") or loan.get("principalAmount") or 0,
                loan.get("roi_percent") or (float(loan.get("roi") or 0) * 100),
                loan.get("tenure_days") or 0,
            )
            total_wcdl_interest += interest

        # ── AI Costs ─────────────────────────────────────────────────────────
        if ai_usage:
            for usage in ai_usage:
                total_ai_cost += self.compute_ai_cost(
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                    usage.get("model", "OpenRouter"),
                )

        total_interest = total_cc_interest + total_wcdl_interest

        # ── Finance Cost % — Gap 5 Fix: uses actual days/365 ────────────────
        finance_cost_pct = self.compute_finance_cost_percent(
            total_interest, total_avg_utilisation, days_in_period
        )

        # ── Blended ROI — Gap 6: back-calculated effective annualised rate ───
        blended_roi_pct = self.compute_blended_roi(
            total_interest, total_avg_utilisation, days_in_period
        )

        # ── Cross-validation (opening + D/C = closing) ───────────────────────
        for acct in accounts_data:
            txns = acct.get("transactions", [])
            if not txns:
                continue
            calc_deposits     = sum(float(t.get("deposit") or 0) for t in txns)
            calc_withdrawals  = sum(float(t.get("withdrawal") or 0) for t in txns)
            opening           = float(acct.get("opening_balance") or 0)
            closing           = acct.get("closing_balance")
            if closing is not None:
                expected_closing = opening + calc_deposits - calc_withdrawals
                diff = abs(float(expected_closing) - float(closing))
                acct["_reconciliation"] = {
                    "status": "PASS" if diff <= 1.0 else ("WARN" if diff <= 10.0 else "FAIL"),
                    "diff": round(diff, 2),
                    "expected_closing": round(expected_closing, 2),
                    "actual_closing": round(float(closing), 2),
                }

        return {
            "total_cc_interest":     round(total_cc_interest, 2),
            "total_notional_loss":   round(total_notional_loss, 2),
            "total_wcdl_interest":   round(total_wcdl_interest, 2),
            "total_interest":        round(total_interest, 2),
            "average_utilisation":   round(total_avg_utilisation, 2),
            "finance_cost_pct":      finance_cost_pct,
            "blended_roi_pct":       blended_roi_pct,     # Gap 6
            "days_in_period":        days_in_period,
            "total_ai_cost":         round(total_ai_cost, 4),
            "roi_status":            "OK" if finance_cost_pct < 10 else "FLAG",
        }
