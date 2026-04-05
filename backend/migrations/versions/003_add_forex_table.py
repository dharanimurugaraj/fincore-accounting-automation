"""
Add ForexTransaction table.
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

    print("[migration] Creating ForexTransaction table...")
    CREATE_FOREX_TABLE = """
    CREATE TABLE IF NOT EXISTS "ForexTransaction" (
        id               TEXT PRIMARY KEY,
        "orgId"          TEXT NOT NULL REFERENCES "Organisation"(id),
        "runId"          TEXT REFERENCES "PipelineRun"(id),
        "statementMonth" TEXT NOT NULL,
        "boeDate"        DATE,
        "valueDate"      DATE NOT NULL,
        "drawerName"     TEXT,
        "billReference"  TEXT,
        "currency"       TEXT NOT NULL,
        "fcAmount"       NUMERIC(15, 2) NOT NULL,
        "bankRate"       NUMERIC(10, 4) NOT NULL,
        "totalAmtINR"    NUMERIC(15, 2) NOT NULL,
        "excessVsAvg"    NUMERIC(12, 2) DEFAULT 0,
        "createdAt"      TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    try:
        cur.execute(CREATE_FOREX_TABLE)
        print("[migration] Created ForexTransaction table")
    except Exception as e:
        print(f"[migration] Error creating ForexTransaction table: {e}")

    cur.close()
    conn.close()
    print("[migration] Version 003 completed.")

if __name__ == "__main__":
    run_migration()
