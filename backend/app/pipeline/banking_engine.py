"""
banking_engine.py — Universal Banking Calculation Engine

Gap 1 Fix: BANK_REGISTRY removed — replaced by bank_config.BankConfigRegistry (JSON-driven).
Gap 3 Fix: get_bc_utilisation and get_pql_utilisation now wired from loan_tracker.py.
Gap 8 Fix: BankConfigMappingError raised when a config-mapped column is missing.
Gap 9 Fix: account_type drives calculation routing (CC / CA / FX).

All functions are pure — no logic inside Excel-writing code.
"""

import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

from .bank_config import registry as bank_registry
from .loan_tracker import (
    LoanTracker,
    BankConfigMappingError,
    get_wcdl_utilisation,
    get_bc_utilisation,
    get_pql_utilisation,
    calculate_loan_interest,
    loans_from_wcdl_rows,
)


# ── DailyRow — normalised per-day snapshot ─────────────────────────────────────

class DailyRow:
    """
    One day's worth of data for a single bank account.

    Attributes:
        date:               calendar date
        closing_balance:    internal signed float
                              negative → Dr (CC drawing)
                              positive → Cr (credit/positive balance)
        withdrawal:         total debits for the day (unsigned)
        deposit:            total credits for the day (unsigned)
        cc_utilisation:     ABS(closing_balance) if negative else 0   [CC accounts]
        positive_balance:   closing_balance if positive else 0         [CA/positive days]
        no_of_days_positive: 1 if closing_balance > 0 else 0
        wcdl_day:           WCDL utilisation for this day (filled externally)
        bc_day:             BC utilisation for this day
        pql_day:            PQL utilisation for this day
    """

    def __init__(
        self,
        date: datetime,
        closing_balance: float,
        withdrawal: float = 0.0,
        deposit: float = 0.0,
        narration: str = "",
        ref_no: str = "",
        account_type: str = "CC",
        transformed_positive_balance: Optional[float] = None,
        transformed_no_of_days: Optional[int] = None,
    ):
        self.date = date
        self.closing_balance = closing_balance
        self.withdrawal = withdrawal
        self.deposit = deposit
        self.narration = narration
        self.ref_no = ref_no
        self.account_type = account_type

        # ── PRD Calculations ─────────────────────────────────────────────────
        if account_type == "CC":
            # CC: utilisation = abs(balance) when negative (OD)
            self.cc_utilisation = abs(closing_balance) if closing_balance < 0 else 0.0
        else:
            self.cc_utilisation = 0.0

        if transformed_positive_balance is not None:
            self.positive_balance = float(transformed_positive_balance)
            self.no_of_days_positive = int(
                transformed_no_of_days
                if transformed_no_of_days is not None
                else (1 if self.positive_balance > 0 else 0)
            )
        else:
            # PRD Rule: Positive balance and days strictly depend on Credit (positive) status
            self.positive_balance = closing_balance if closing_balance > 0 else 0.0
            self.no_of_days_positive = 1 if closing_balance > 0 else 0

        # Filled by loan utilisation engine after parse_statement
        self.wcdl_day: float = 0.0
        self.bc_day:   float = 0.0
        self.pql_day:  float = 0.0

    @property
    def total_utilisation(self) -> float:
        return self.cc_utilisation + self.wcdl_day + self.bc_day + self.pql_day


# ── Core Engine ────────────────────────────────────────────────────────────────

class UniversalBankingEngine:
    """
    Core Calculation Engine.
    Every function is pure (input → output, no side effects).
    """

    # ── Step 3a: Parse & normalise bank statement data ─────────────────────
    def parse_statement(
        self,
        extracted_data: Dict[str, Any],
        bank_config: Optional[Dict[str, Any]] = None,
    ) -> List[DailyRow]:
        """
        Normalise raw extracted transactions into a full-calendar DailyRow list.

        Args:
            extracted_data: output dict from PDFExtractor (contains 'transactions', 'period_from', etc.)
            bank_config: optional dict from BankConfigRegistry; used for column name validation.
                         If None, auto-resolved from bank_name + account_number.

        Returns:
            List[DailyRow] — one entry per calendar day, sorted ascending.

        Raises:
            BankConfigMappingError: if a col_xxx mapping from bank_config is absent in extracted data.
        """
        txns = extracted_data.get("transactions", [])
        account_type = extracted_data.get("account_type", "CC")

        if not txns:
            return []

        # ── Resolve bank config from registry if not supplied ───────────────
        if bank_config is None:
            bank_config = bank_registry.resolve_from_schema(
                extracted_data.get("bank_name", ""),
                extracted_data.get("account_number", ""),
            ) or {}

        # ── Validate column mapping (Gap 8) ─────────────────────────────────
        self._validate_column_mapping(extracted_data, bank_config)

        df = pd.DataFrame(txns)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])

        # ── Full calendar period ─────────────────────────────────────────────
        period_from = extracted_data.get("period_from")
        period_to   = extracted_data.get("period_to")
        start_date  = pd.to_datetime(period_from) if period_from else df["date"].min()
        end_date    = pd.to_datetime(period_to)   if period_to   else df["date"].max()
        all_dates   = pd.date_range(start=start_date, end=end_date, freq="D")

        # ── Aggregate (last closing balance, sum W/D) ────────────────────────
        agg_map: Dict[str, Any] = {}
        if "withdrawal_dr" in df.columns:
            agg_map["withdrawal_dr"] = "sum"
        elif "withdrawal" in df.columns:
            agg_map["withdrawal"] = "sum"
        if "deposit_cr" in df.columns:
            agg_map["deposit_cr"] = "sum"
        elif "deposit" in df.columns:
            agg_map["deposit"] = "sum"
        if "closing_balance" in df.columns:
            agg_map["closing_balance"] = "last"
        if "narration" in df.columns:
            agg_map["narration"] = lambda x: " ; ".join(filter(None, map(str, x)))
        if "ref_number" in df.columns:
            agg_map["ref_number"] = lambda x: " / ".join(filter(None, map(str, x)))
        if "positive_balance" in df.columns:
            agg_map["positive_balance"] = "last"
        if "no_of_days" in df.columns:
            agg_map["no_of_days"] = "last"

        if not agg_map:
            return []

        daily_agg = (
            df.groupby("date")
            .agg(agg_map)
            .reindex(all_dates)
        )

        # ── Carry-forward for missing dates (bank practice) ─────────────────
        opening_bal = float(extracted_data.get("opening_balance") or 0.0)
        if "closing_balance" in daily_agg.columns:
            daily_agg["closing_balance"] = (
                daily_agg["closing_balance"].ffill().fillna(opening_bal)
            )
        else:
            daily_agg["closing_balance"] = opening_bal

        for col in ("withdrawal_dr", "deposit_cr", "withdrawal", "deposit"):
            if col in daily_agg.columns:
                daily_agg[col] = daily_agg[col].fillna(0.0)
        if "withdrawal_dr" not in daily_agg.columns and "withdrawal" not in daily_agg.columns:
            daily_agg["withdrawal"] = 0.0
        if "deposit_cr" not in daily_agg.columns and "deposit" not in daily_agg.columns:
            daily_agg["deposit"] = 0.0

        if "narration" in daily_agg.columns:
            daily_agg["narration"] = daily_agg["narration"].fillna("NO TRANSACTION")
        else:
            daily_agg["narration"] = "NO TRANSACTION"

        if "ref_number" in daily_agg.columns:
            daily_agg["ref_number"] = daily_agg["ref_number"].fillna("-")
        else:
            daily_agg["ref_number"] = "-"

        daily_agg = daily_agg.reset_index()
        daily_agg.columns = ["date"] + [c for c in daily_agg.columns if c != "index"][1:]

        rows = []
        for _, r in daily_agg.iterrows():
            tpb, tnd = None, None
            if "positive_balance" in df.columns:
                v = r.get("positive_balance")
                if pd.notna(v):
                    tpb = float(v)
                    ndv = r.get("no_of_days")
                    tnd = int(ndv) if pd.notna(ndv) else (1 if tpb > 0 else 0)
            wd = float(r.get("withdrawal_dr", r.get("withdrawal", 0)))
            dp = float(r.get("deposit_cr", r.get("deposit", 0)))
            rows.append(DailyRow(
                date=r["date"],
                closing_balance=float(r.get("closing_balance", 0)),
                withdrawal=wd,
                deposit=dp,
                narration=str(r.get("narration", "")),
                ref_no=str(r.get("ref_number", "")),
                account_type=account_type,
                transformed_positive_balance=tpb,
                transformed_no_of_days=tnd,
            ))
        return rows

    # ── Step 3b: CC utilisation metrics ───────────────────────────────────
    def get_cc_utilisation(self, daily_rows: List[DailyRow]) -> Dict[str, float]:
        """
        Compute CC utilisation metrics for a CC account.

        Returns:
            avg_cc:                 SUM(cc_day) / total_days
            total_days:             number of calendar days
            total_utilisation_inr:  SUM of all cc_day values
        """
        if not daily_rows:
            return {"avg_cc": 0.0, "total_days": 0, "total_utilisation_inr": 0.0}

        total_cc   = sum(r.cc_utilisation for r in daily_rows)
        total_days = len(daily_rows)

        return {
            "avg_cc": total_cc / total_days,
            "total_days": total_days,
            "total_utilisation_inr": total_cc,
        }

    # ── Step 3c: Attach loan utilisation to daily rows ─────────────────────
    def attach_loan_utilisation(
        self,
        daily_rows: List[DailyRow],
        loans: List[LoanTracker],
    ) -> List[DailyRow]:
        """
        Enriches each DailyRow with wcdl_day, bc_day, pql_day from loan tracker.

        Args:
            daily_rows: output of parse_statement()
            loans:      list of LoanTracker instances

        Returns:
            The same DailyRow list, mutated in-place with loan utilisation.
        """
        date_list = [r.date.date() if hasattr(r.date, "date") else r.date for r in daily_rows]

        wcdl_util = get_wcdl_utilisation(loans, date_list)
        bc_util   = get_bc_utilisation(loans, date_list)
        pql_util  = get_pql_utilisation(loans, date_list)

        for row in daily_rows:
            d = row.date.date() if hasattr(row.date, "date") else row.date
            row.wcdl_day = wcdl_util.get(d, 0.0)
            row.bc_day   = bc_util.get(d, 0.0)
            row.pql_day  = pql_util.get(d, 0.0)

        return daily_rows

    # ── Step 3d: Interest calculation ──────────────────────────────────────
    def calculate_cc_interest(
        self,
        daily_rows: List[DailyRow],
        roi: float,
    ) -> Dict[str, Any]:
        """
        CC Monthly Interest = SUM(daily_cc_utilisation) × roi / 365

        Args:
            daily_rows: enriched DailyRow list
            roi: annual decimal rate (e.g. 0.0725)

        Returns:
            dict with calculated_interest, effective_roi_daily, days_processed
        """
        total_util = sum(r.cc_utilisation for r in daily_rows)
        days = len(daily_rows)
        calc_int = (total_util * roi) / 365

        return {
            "calculated_interest": round(calc_int, 2),
            "effective_roi_daily": roi / 365,
            "days_processed": days,
            "total_cc_util_sum": round(total_util, 2),
        }

    def calculate_wcdl_all(self, loans: List[LoanTracker]) -> List[Dict]:
        """
        Calculate interest for every loan in the tracker.
        Returns a list of result dicts (see calculate_loan_interest).
        """
        return [calculate_loan_interest(l) for l in loans]

    # ── Step 3e: Back-calculate effective ROI ─────────────────────────────
    def verify_effective_roi(
        self,
        interest_charged: float,
        avg_utilisation: float,
        days_in_period: int,
    ) -> float:
        """
        Effective ROI = (Interest_Charged / Avg_Utilisation) × (365 / days_in_period)

        This is the back-check column in the banking report.
        A difference vs sanctioned ROI indicates product mix effect.

        Args:
            interest_charged:  total interest debited for the period
            avg_utilisation:   average daily utilisation in INR
            days_in_period:    actual days (28/29/30/31)

        Returns:
            effective_roi_annualised as decimal (e.g. 0.07561...)
        """
        if avg_utilisation == 0 or days_in_period == 0:
            return 0.0
        monthly_rate = interest_charged / avg_utilisation
        return round(monthly_rate * (365 / days_in_period), 6)

    # ── Validation helper (Gap 8) ──────────────────────────────────────────
    def _validate_column_mapping(
        self,
        extracted_data: Dict[str, Any],
        bank_config: Dict[str, Any],
    ) -> None:
        """
        Checks that columns referenced in bank_config exist in extracted_data.
        Raises BankConfigMappingError with a descriptive message if not.
        """
        if not bank_config:
            return  # Nothing to validate against

        bank_name = extracted_data.get("bank_name", "Unknown Bank")

        # Check col_date presence (transactions should have 'date')
        col_date = bank_config.get("col_date")
        if col_date and extracted_data.get("transactions"):
            first_txn = extracted_data["transactions"][0]
            if "date" not in first_txn:
                raise BankConfigMappingError(
                    f"col_date '{col_date}' not found in {bank_name} statement. "
                    f"Available keys: {list(first_txn.keys())}"
                )

        # Check col_closing_balance
        col_bal = bank_config.get("col_closing_balance")
        if col_bal and extracted_data.get("transactions"):
            first_txn = extracted_data["transactions"][0]
            if "closing_balance" not in first_txn:
                raise BankConfigMappingError(
                    f"col_closing_balance '{col_bal}' not found in {bank_name} statement. "
                    f"Available keys: {list(first_txn.keys())}"
                )
