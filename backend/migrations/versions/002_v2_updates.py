"""
FinCore v2.0 Database Updates.
Adds SHA-256 checksums to PipelineRun and creates the WCDLLoans table.
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

    print("[migration] Adding checksum columns to PipelineRun...")
    try:
        cur.execute('ALTER TABLE "PipelineRun" ADD COLUMN IF NOT EXISTS "checksum" TEXT;')
        print("[migration] Added 'checksum' to PipelineRun")
    except Exception as e:
        print(f"[migration] Error adding checksum: {e}")

    print("[migration] Creating WCDLLoans table...")
    CREATE_WCDL_TABLE = """
    CREATE TABLE IF NOT EXISTS "WCDLLoan" (
        id               TEXT PRIMARY KEY,
        "orgId"          TEXT NOT NULL REFERENCES "Organisation"(id),
        "loanNumber"     TEXT NOT NULL,
        "bankName"       TEXT NOT NULL,
        "principalAmount" NUMERIC(15, 2) NOT NULL,
        "roi"            NUMERIC(5, 4) NOT NULL,
        "startDate"      DATE NOT NULL,
        "maturityDate"   DATE NOT NULL,
        "prepaymentDate" DATE,
        "status"         TEXT NOT NULL DEFAULT 'ACTIVE',
        "createdAt"      TIMESTAMPTZ NOT NULL DEFAULT now(),
        "updatedAt"      TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    try:
        cur.execute(CREATE_WCDL_TABLE)
        print("[migration] Created WCDLLoan table")
    except Exception as e:
        print(f"[migration] Error creating WCDLLoan table: {e}")

    cur.close()
    conn.close()
    print("[migration] Version 002 completed.")

if __name__ == "__main__":
    run_migration()
