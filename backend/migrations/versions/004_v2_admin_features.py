"""
Add FormulaConfiguration and AgentConfig tables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration():
    if not DATABASE_URL:
        print("DATABASE_URL not found in .env")
        return

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("[migration] Creating FormulaConfiguration and AgentConfig tables...")
    
    # Formula Configuration with Versioning
    CREATE_FORMULA_TABLE = """
    CREATE TABLE IF NOT EXISTS "FormulaConfiguration" (
        id               TEXT PRIMARY KEY,
        "orgId"          TEXT NOT NULL REFERENCES "Organisation"(id),
        name             TEXT NOT NULL, -- e.g., 'cc_interest', 'wcdl_interest'
        description      TEXT,
        expression       TEXT NOT NULL, -- The python/pseudo-code formula
        parameters       JSONB,         -- Default parameters like 'repo_rate', 'basis_points'
        version          INTEGER NOT NULL DEFAULT 1,
        "isActive"       BOOLEAN DEFAULT TRUE,
        "updatedBy"      TEXT,
        "updatedAt"      TIMESTAMPTZ NOT NULL DEFAULT now(),
        "createdAt"      TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    
    # Agent Configuration for OpenRouter models
    CREATE_AGENT_CONFIG_TABLE = """
    CREATE TABLE IF NOT EXISTS "AgentConfig" (
        id               TEXT PRIMARY KEY,
        "orgId"          TEXT NOT NULL REFERENCES "Organisation"(id),
        "agentId"        TEXT NOT NULL, -- e.g., 'hdfc_cc', 'wcdl_parser'
        "primaryModel"   TEXT NOT NULL, -- e.g., 'anthropic/claude-3-sonnet'
        "fallbackModels" TEXT[],        -- List of fallback models
        "maxRetries"     INTEGER DEFAULT 3,
        "temperature"    NUMERIC(3, 2) DEFAULT 0.0,
        "updatedAt"      TIMESTAMPTZ NOT NULL DEFAULT now(),
        "createdAt"      TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE("orgId", "agentId")
    );
    """

    try:
        cur.execute(CREATE_FORMULA_TABLE)
        print("[migration] Created FormulaConfiguration table")
        cur.execute(CREATE_AGENT_CONFIG_TABLE)
        print("[migration] Created AgentConfig table")
        
        # Seed default formulas
        print("[migration] Seeding default formulas...")
        SEED_FORMULAS = """
        INSERT INTO "FormulaConfiguration" (id, "orgId", name, description, expression, parameters, version)
        VALUES 
        ('f-001', 'default-org', 'cc_interest', 'Closing Balance * ROI / 365', 'balance * roi / 365', '{"days_in_year": 365}', 1),
        ('f-002', 'default-org', 'wcdl_interest', 'Principal * ROI * Tenure / 365', 'principal * roi * tenure_days / 365', '{"days_in_year": 365}', 1),
        ('f-003', 'default-org', 'notional_loss', 'Avg Positive Balance * CC ROI * Days / 365', 'avg_balance * cc_roi * days / 365', '{"days_in_year": 365}', 1),
        ('f-004', 'default-org', 'finance_cost_pct', '(Total Interest / Avg Utilisation) * 12', '(total_interest / avg_utilisation) * 12', '{}', 1),
        ('f-005', 'default-org', 'actual_roi', '(Interest / Principal) / Tenure * 365', '(interest / principal) / tenure_days * 365', '{"days_in_year": 365}', 1),
        ('f-006', 'default-org', 'forex_excess', 'FCY * (Bank Rate - Market Rate)', 'fc_amount * (bank_rate - market_rate)', '{}', 1)
        ON CONFLICT (id) DO NOTHING;
        """
        cur.execute(SEED_FORMULAS)
        print("[migration] Seeded formulas.")

    except Exception as e:
        print(f"[migration] Error: {e}")

    cur.close()
    conn.close()
    print("[migration] Version 004 completed.")

if __name__ == "__main__":
    run_migration()
