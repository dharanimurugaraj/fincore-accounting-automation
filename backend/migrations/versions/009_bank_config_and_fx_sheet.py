"""
009_bank_config_and_fx_sheet.py

Migration: Add BankConfig table (dynamic bank registry) and fxSheetKey column on PipelineRun.

This enables:
  - Gap 1: Dynamic bank config stored in DB (one INSERT = new bank, zero code changes)
  - Gap 7: fxSheetKey stored on PipelineRun for FX sheet download
  - Gap 2: Extend WCDLLoan with loan_type, account_number, interest_as_per_bank columns
"""

from app.core.database import execute_query, execute_insert
import json


def up():
    """Apply migration."""

    # ── 1. BankConfig table ───────────────────────────────────────────────────
    execute_query("""
        CREATE TABLE IF NOT EXISTS "BankConfig" (
            id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            "orgId"         TEXT REFERENCES "Organisation"(id) ON DELETE CASCADE,
            "bankKey"       TEXT NOT NULL,        -- e.g. "HDFC-521"
            "bankName"      TEXT NOT NULL,
            "accountNumber" TEXT NOT NULL,
            "accountType"   TEXT NOT NULL DEFAULT 'CC',  -- CC | CA | FX | WCDL
            "currency"      TEXT NOT NULL DEFAULT 'INR', -- INR | USD | EUR | GBP
            "colDate"       TEXT,                  -- col name in statement for date
            "dateFormat"    TEXT,                  -- e.g. "DD-Mon-YYYY"
            "colBalance"    TEXT,                  -- col name for closing balance
            "balanceSign"   TEXT DEFAULT 'flagged',-- signed | flagged
            "colDrCrFlag"   TEXT,                  -- col name for Dr/Cr flag (if flagged)
            "drValue"       TEXT,                  -- e.g. "OD", "Dr", "DR"
            "colFxBalance"  TEXT,                  -- FC balance col (FX accounts)
            "colFxRate"     TEXT,                  -- exchange rate col (FX accounts)
            "ccRoi"         NUMERIC(8,6) DEFAULT 0,
            "ccLimit"       NUMERIC(18,2) DEFAULT 0,
            "wcdlLimit"     NUMERIC(18,2) DEFAULT 0,
            "totalWcLimit"  NUMERIC(18,2) DEFAULT 0,
            "isActive"      BOOLEAN DEFAULT TRUE,
            "createdAt"     TIMESTAMPTZ DEFAULT now(),
            "updatedAt"     TIMESTAMPTZ DEFAULT now(),
            UNIQUE("orgId", "bankKey")
        )
    """)

    # ── 2. Add loan_type, account_number, interest_as_per_bank to WCDLLoan ───
    for col_def in [
        ("loanType",          "TEXT NOT NULL DEFAULT 'WCDL'"),     # WCDL | BC | PQL
        ("accountNumber",     "TEXT"),                              # which bank account
        ("interestAsPerBank", "NUMERIC(15,2)"),                     # from bank statement
        ("fcAmount",          "NUMERIC(18,4)"),                     # BC: FC amount
        ("fcCurrency",        "TEXT"),                              # BC: USD/EUR/GBP
        ("exchangeRateAtDrawdown", "NUMERIC(10,4)"),               # BC: locked rate
    ]:
        col_name, col_type = col_def
        try:
            execute_query(
                f'ALTER TABLE "WCDLLoan" ADD COLUMN IF NOT EXISTS "{col_name}" {col_type}'
            )
        except Exception as e:
            print(f"WARN: Could not add WCDLLoan.{col_name}: {e}")

    # ── 3. Add fxSheetKey column to PipelineRun ───────────────────────────────
    try:
        execute_query(
            'ALTER TABLE "PipelineRun" ADD COLUMN IF NOT EXISTS "fxSheetKey" TEXT'
        )
    except Exception as e:
        print(f"WARN: Could not add PipelineRun.fxSheetKey: {e}")

    # ── 4. Seed BankConfig with default banks (org-agnostic, NULL orgId) ─────
    seed_banks = [
        {
            "bankKey": "HDFC-521", "bankName": "HDFC BANK",
            "accountNumber": "XXXXXXXX521", "accountType": "CC", "currency": "INR",
            "colDate": "Date", "dateFormat": "DD-Mon-YYYY",
            "colBalance": "Balance", "balanceSign": "flagged",
            "colDrCrFlag": "Dr/Cr Flag", "drValue": "OD",
            "ccRoi": 0.0725, "ccLimit": 225000000, "wcdlLimit": 550000000, "totalWcLimit": 775000000,
        },
        {
            "bankKey": "HDFC-512", "bankName": "HDFC BANK",
            "accountNumber": "XXXXXXXX512", "accountType": "CA", "currency": "INR",
            "colDate": "Date", "dateFormat": "DD-Mon-YYYY",
            "colBalance": "Balance", "balanceSign": "flagged",
            "colDrCrFlag": "Dr/Cr Flag", "drValue": "Dr",
            "ccRoi": 0, "ccLimit": 0, "wcdlLimit": 0, "totalWcLimit": 0,
        },
        {
            "bankKey": "HDFC-552", "bankName": "HDFC BANK",
            "accountNumber": "XXXXXXXX552", "accountType": "CA", "currency": "INR",
            "colDate": "Date", "dateFormat": "DD-Mon-YYYY",
            "colBalance": "Balance", "balanceSign": "flagged",
            "colDrCrFlag": "Dr/Cr Flag", "drValue": "Dr",
            "ccRoi": 0, "ccLimit": 0, "wcdlLimit": 0, "totalWcLimit": 0,
        },
        {
            "bankKey": "UBI-001", "bankName": "UNION BANK OF INDIA",
            "accountNumber": "XXXXXXXXX001", "accountType": "CC", "currency": "INR",
            "colDate": "Value Date", "dateFormat": "DD/MM/YYYY",
            "colBalance": "Balance", "balanceSign": "flagged",
            "colDrCrFlag": "Dr/Cr", "drValue": "Dr",
            "ccRoi": 0.085, "ccLimit": 0, "wcdlLimit": 0, "totalWcLimit": 0,
        },
    ]
    for bank in seed_banks:
        try:
            execute_query("""
                INSERT INTO "BankConfig" (
                    "bankKey", "bankName", "accountNumber", "accountType", "currency",
                    "colDate", "dateFormat", "colBalance", "balanceSign",
                    "colDrCrFlag", "drValue",
                    "ccRoi", "ccLimit", "wcdlLimit", "totalWcLimit"
                ) VALUES (
                    %(bankKey)s, %(bankName)s, %(accountNumber)s, %(accountType)s, %(currency)s,
                    %(colDate)s, %(dateFormat)s, %(colBalance)s, %(balanceSign)s,
                    %(colDrCrFlag)s, %(drValue)s,
                    %(ccRoi)s, %(ccLimit)s, %(wcdlLimit)s, %(totalWcLimit)s
                )
                ON CONFLICT ("orgId", "bankKey") DO NOTHING
            """, bank)
        except Exception as e:
            print(f"WARN: Seed bank {bank['bankKey']} skipped: {e}")

    print("[009] Migration applied: BankConfig table, WCDLLoan extensions, PipelineRun.fxSheetKey")


def down():
    """Rollback migration."""
    execute_query('DROP TABLE IF EXISTS "BankConfig"')
    execute_query('ALTER TABLE "PipelineRun" DROP COLUMN IF EXISTS "fxSheetKey"')
    for col in ["loanType", "accountNumber", "interestAsPerBank", "fcAmount", "fcCurrency", "exchangeRateAtDrawdown"]:
        try:
            execute_query(f'ALTER TABLE "WCDLLoan" DROP COLUMN IF EXISTS "{col}"')
        except Exception:
            pass
    print("[009] Migration rolled back.")


if __name__ == "__main__":
    up()
