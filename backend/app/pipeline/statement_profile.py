"""
Per-PDF statement profile: scout-derived layout + optional bank_config overlay.

Single place to document what drove parsing vs what came from JSON registry.
No bank-name hardcoding — matching uses registry.resolve_from_schema only.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .bank_schema import BankSchema


def _registry_roi_to_percent(cc_roi: Any) -> Optional[float]:
    """JSON stores cc_roi as annual decimal (e.g. 0.0725); sheet/engine expect percent (7.25)."""
    if cc_roi is None:
        return None
    try:
        v = float(cc_roi)
    except (TypeError, ValueError):
        return None
    return v * 100 if abs(v) <= 1 else v


def apply_registry_overlay(schema: BankSchema, registry_cfg: Optional[Dict[str, Any]]) -> None:
    """
    Fill gaps on schema from bank_config.json (limits, ROI) when scout left them null.
    Does not replace scout column names or layout enums.
    """
    if not registry_cfg:
        return
    if schema.cc_roi_percent is None:
        pct = _registry_roi_to_percent(registry_cfg.get("cc_roi"))
        if pct is not None:
            schema.cc_roi_percent = pct
    if schema.cc_limit is None:
        lim = registry_cfg.get("cc_sanctioned_limit")
        if lim is not None:
            try:
                schema.cc_limit = float(lim)
            except (TypeError, ValueError):
                pass


def build_statement_profile(
    schema: BankSchema,
    registry_cfg: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Return a JSON-serialisable profile: PDF column labels from scout, registry snapshot, merged view.
    """
    scout_pdf = {
        "date_header": "Date",
        "narration_col_name": schema.narration_col_name,
        "ref_col_name": schema.ref_col_name,
        "withdrawal_col_name": schema.withdrawal_col_name,
        "deposit_col_name": schema.deposit_col_name,
        "balance_col_name": schema.balance_col_name,
        "date_format": schema.date_format,
        "amount_style": schema.amount_style,
        "balance_style": schema.balance_style,
        "column_layout": schema.column_layout,
        "dr_cr_order": schema.dr_cr_order,
        "positive_markers": list(schema.positive_markers),
        "negative_markers": list(schema.negative_markers),
        "strict_column_amounts": schema.strict_column_amounts,
        "use_excel_balance_formulas": schema.use_excel_balance_formulas,
    }
    registry_snapshot = dict(registry_cfg) if registry_cfg else None
    merged = {
        **scout_pdf,
        "bank_name": schema.bank_name,
        "account_number": schema.account_number,
        "account_type": schema.account_type,
        "currency": (registry_cfg or {}).get("currency"),
        "cc_roi_percent": schema.cc_roi_percent,
        "cc_limit": schema.cc_limit,
        "wcdl_sanctioned_limit": (registry_cfg or {}).get("wcdl_sanctioned_limit"),
        "total_wc_limit": (registry_cfg or {}).get("total_wc_limit"),
    }
    return {
        "scout_pdf_columns": scout_pdf,
        "registry": registry_snapshot,
        "merged": merged,
    }
