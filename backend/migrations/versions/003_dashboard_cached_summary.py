"""
Migration 003: FinCore Dashboard Schema Alignment.
Adds 'reportSummary' to PipelineRun and 'statementMonth' to WCDLLoan.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
print(f"[migration] Loading env from: {env_path.absolute()}")
load_dotenv(env_path)
DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration():
    if not DATABASE_URL:
        print("DATABASE_URL not found in .env")
        return

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("[migration] Updating PipelineRun table...")
    try:
        cur.execute('ALTER TABLE "PipelineRun" ADD COLUMN IF NOT EXISTS "reportSummary" TEXT;')
        print("[migration] Added 'reportSummary' to PipelineRun")
    except Exception as e:
        print(f"[migration] Error adding reportSummary: {e}")

    print("[migration] Updating WCDLLoan table...")
    try:
        cur.execute('ALTER TABLE "WCDLLoan" ADD COLUMN IF NOT EXISTS "statementMonth" TEXT;')
        print("[migration] Added 'statementMonth' to WCDLLoan")
    except Exception as e:
        print(f"[migration] Error adding statementMonth: {e}")

    cur.close()
    conn.close()
    print("[migration] Migration 003 completed.")

if __name__ == "__main__":
    run_migration()
