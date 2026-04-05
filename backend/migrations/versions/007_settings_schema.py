"""
Migration 007: Settings Profile and Preferences Updates
"""

import sys
import os
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(backend_dir))

from app.core.database import execute_query

def run_migration():
    print("Running migration 007: Settings architecture")

    try:
        # Organization Extensibility
        print("Adding Organisation settings columns...")
        execute_query("""
            ALTER TABLE "Organisation"
            ADD COLUMN IF NOT EXISTS "legalName" TEXT,
            ADD COLUMN IF NOT EXISTS "address" TEXT,
            ADD COLUMN IF NOT EXISTS "logoUrl" TEXT,
            ADD COLUMN IF NOT EXISTS "departments" TEXT[] DEFAULT '{}';
        """, ())

        # User Extensibility
        print("Adding User settings columns...")
        execute_query("""
            ALTER TABLE "User"
            ADD COLUMN IF NOT EXISTS "title" TEXT,
            ADD COLUMN IF NOT EXISTS "phone" TEXT,
            ADD COLUMN IF NOT EXISTS "theme" TEXT DEFAULT 'dark',
            ADD COLUMN IF NOT EXISTS "timezone" TEXT DEFAULT 'UTC',
            ADD COLUMN IF NOT EXISTS "dateFormat" TEXT DEFAULT 'MM/DD/YYYY',
            ADD COLUMN IF NOT EXISTS "emailAlerts" BOOLEAN DEFAULT TRUE;
        """, ())
        
        # Platform Config Table - Simple Key/Value JSON Store for API limits, variables, constants
        print("Adding GlobalConfig table...")
        execute_query("""
            CREATE TABLE IF NOT EXISTS "GlobalConfig" (
                key TEXT PRIMARY KEY,
                value JSONB,
                "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """, ())
        
        # Seed default platform vars
        execute_query("""
            INSERT INTO "GlobalConfig" (key, value)
            VALUES ('costPer1KTokens', '0.005'), ('requireApprovals', 'true')
            ON CONFLICT (key) DO NOTHING;
        """, ())

        print("Migration 007 complete.")

    except Exception as e:
        print(f"Migration 007 failed: {e}")

if __name__ == "__main__":
    run_migration()
