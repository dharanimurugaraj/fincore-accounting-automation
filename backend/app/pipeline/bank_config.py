"""
bank_config.py — Dynamic Bank Config Registry

One-time setup per bank. Zero code changes to add a new bank.
Loaded from bank_config.json at runtime (or seeded defaults).

Gap 1 Fix: Replaces the static BANK_REGISTRY in banking_engine.py.
"""

import json
import os
from typing import Dict, Any, Optional

# ── Path to the runtime config file ──────────────────────────────────────────
_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "bank_config.json")

# ── Seed defaults (written to JSON on first run if file missing) ───────────────
_SEED_BANK_CONFIG: Dict[str, Any] = {
    "HDFC-521": {
        "bank_name": "HDFC BANK",
        "account_number": "XXXXXXXX521",
        "account_type": "CC",
        "currency": "INR",
        "col_date": "Date",
        "date_format": "DD-Mon-YYYY",
        "col_closing_balance": "Balance",
        "balance_sign_convention": "flagged",
        "col_dr_cr_flag": "Dr/Cr Flag",
        "dr_value": "OD",
        "cc_roi": 0.0725,
        "cc_sanctioned_limit": 225000000.0,
        "wcdl_sanctioned_limit": 550000000.0,
        "total_wc_limit": 775000000.0,
    },
    "HDFC-512": {
        "bank_name": "HDFC BANK",
        "account_number": "XXXXXXXX512",
        "account_type": "CA",
        "currency": "INR",
        "col_date": "Date",
        "date_format": "DD-Mon-YYYY",
        "col_closing_balance": "Balance",
        "balance_sign_convention": "flagged",
        "col_dr_cr_flag": "Dr/Cr Flag",
        "dr_value": "Dr",
        "cc_roi": 0.0,
        "cc_sanctioned_limit": 0.0,
        "wcdl_sanctioned_limit": 0.0,
        "total_wc_limit": 0.0,
    },
    "HDFC-552": {
        "bank_name": "HDFC BANK",
        "account_number": "XXXXXXXX552",
        "account_type": "CA",
        "currency": "INR",
        "col_date": "Date",
        "date_format": "DD-Mon-YYYY",
        "col_closing_balance": "Balance",
        "balance_sign_convention": "flagged",
        "col_dr_cr_flag": "Dr/Cr Flag",
        "dr_value": "Dr",
        "cc_roi": 0.0,
        "cc_sanctioned_limit": 0.0,
        "wcdl_sanctioned_limit": 0.0,
        "total_wc_limit": 0.0,
    },
    "UBI-001": {
        "bank_name": "UNION BANK OF INDIA",
        "account_number": "XXXXXXXXX001",
        "account_type": "CC",
        "currency": "INR",
        "col_date": "Value Date",
        "date_format": "DD/MM/YYYY",
        "col_closing_balance": "Balance",
        "balance_sign_convention": "flagged",
        "col_dr_cr_flag": "Dr/Cr",
        "dr_value": "Dr",
        "cc_roi": 0.085,
        "cc_sanctioned_limit": 0.0,
        "wcdl_sanctioned_limit": 0.0,
        "total_wc_limit": 0.0,
    },
    "HDFC-FX": {
        "bank_name": "HDFC BANK",
        "account_number": "XXXXXXXXFX01",
        "account_type": "FX",
        "currency": "USD",
        "col_date": "Date",
        "date_format": "DD/MM/YYYY",
        "col_closing_balance": "Closing Balance",
        "balance_sign_convention": "signed",
        "col_dr_cr_flag": None,
        "dr_value": None,
        "col_fx_balance": "Balance (FC)",
        "col_fx_rate": "Exchange Rate",
        "cc_roi": 0.0,
        "cc_sanctioned_limit": 0.0,
        "wcdl_sanctioned_limit": 0.0,
        "total_wc_limit": 0.0,
    },
}

_SEED_FACILITY_CONFIG: Dict[str, Any] = {
    "HDFC-521": {
        "cc_sanctioned_limit": 225000000.0,
        "wcdl_sanctioned_limit": 550000000.0,
        "total_wc_limit": 775000000.0,
        "cc_roi": 0.0725,
    },
    "UBI-001": {
        "cc_sanctioned_limit": 0.0,
        "wcdl_sanctioned_limit": 0.0,
        "total_wc_limit": 0.0,
        "cc_roi": 0.085,
    },
}


# ── Registry class ─────────────────────────────────────────────────────────────

class BankConfigRegistry:
    """
    Loads bank config from bank_config.json.
    Seeded with defaults on first boot.
    To add a new bank: add one entry to bank_config.json, no code change.
    """

    def __init__(self):
        self._bank_config: Dict[str, Any] = {}
        self._facility_config: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if os.path.exists(_CONFIG_FILE):
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._bank_config = raw.get("banks", {})
            self._facility_config = raw.get("facilities", {})
        else:
            # Seed defaults on first run
            self._bank_config = _SEED_BANK_CONFIG
            self._facility_config = _SEED_FACILITY_CONFIG
            self._save()
            print("[BankConfigRegistry] Seeded bank_config.json with defaults.")

    def _save(self):
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"banks": self._bank_config, "facilities": self._facility_config},
                f,
                indent=2,
            )

    def get_bank(self, key: str) -> Optional[Dict[str, Any]]:
        """Return config for a bank key (e.g. 'HDFC-521'). None if unknown."""
        return self._bank_config.get(key)

    def all_banks(self) -> Dict[str, Any]:
        return dict(self._bank_config)

    def get_facility(self, key: str) -> Optional[Dict[str, Any]]:
        return self._facility_config.get(key)

    def add_bank(self, key: str, config: Dict[str, Any]):
        """
        Register a new bank at runtime and persist to JSON.
        Zero code changes required.
        """
        self._bank_config[key] = config
        self._save()
        print(f"[BankConfigRegistry] Added new bank: {key}")

    def resolve_from_schema(self, bank_name: str, account_number: str) -> Optional[Dict[str, Any]]:
        """
        Match extracted bank name + account number against registry.
        Returns first config entry where account_number suffix matches.
        Falls back to None if no match (engine will use schema-derived config).
        """
        acct_suffix = str(account_number).strip()[-4:] if account_number else ""
        bname_upper = (bank_name or "").upper()
        for key, cfg in self._bank_config.items():
            cfg_bank = cfg.get("bank_name", "").upper()
            cfg_acct = str(cfg.get("account_number", ""))
            if bname_upper and bname_upper in cfg_bank:
                if not acct_suffix or cfg_acct.endswith(acct_suffix):
                    return cfg
        return None


# ── Module-level singleton ─────────────────────────────────────────────────────
registry = BankConfigRegistry()
