# Pipeline package — FinCore Intelligence Engine
# All new modules are exported here for clean imports anywhere in the app.

# ── Core calculation engine ────────────────────────────────────────────────────
from .engine import FinCoreComputationEngine

# ── Universal banking engine (multi-bank, type-routed) ───────────────────────
from .banking_engine import UniversalBankingEngine, DailyRow

# ── Dynamic bank config registry (JSON-driven, zero code changes for new banks)
from .bank_config import registry as bank_config_registry, BankConfigRegistry
from .statement_profile import apply_registry_overlay, build_statement_profile

# ── Loan tracker (WCDL / BC / PQL) ───────────────────────────────────────────
from .loan_tracker import (
    LoanTracker,
    BankConfigMappingError,
    get_wcdl_utilisation,
    get_bc_utilisation,
    get_pql_utilisation,
    calculate_loan_interest,
    loans_from_wcdl_rows,
)

# ── Excel output generators ────────────────────────────────────────────────────
from .working_sheet import generate_working_sheet
from .banking_report import generate_banking_report
from .fx_sheet import generate_fx_sheet, build_daily_loan_util_dict

# ── Pipeline orchestrator ─────────────────────────────────────────────────────
from .pipeline import FinCorePipeline
