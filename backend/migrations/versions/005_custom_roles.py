"""
Migration 005: Add 'allowedPages' to Role table
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(backend_dir))

from app.core.database import execute_query

def run_migration():
    print("Running migration 005: Custom Roles & Allowed Pages")

    try:
        # Add the 'allowedPages' column to Role if it doesn't exist
        print("Adding allowedPages column to Role table...")
        execute_query("""
            ALTER TABLE "Role"
            ADD COLUMN IF NOT EXISTS "allowedPages" TEXT[] DEFAULT '{"*"}';
        """, ())

        # Ensure base roles have universal access as defaults, or we can leave as default arrays
        execute_query("""
            UPDATE "Role" SET "allowedPages" = '{"*"}'
            WHERE id IN (0, 1) AND "allowedPages" IS NULL;
        """, ())

        # For Analyst (2) and Viewer (3), we might set an explicit array, or leave as "*".
        # We will leave as "*" for backwards compatibility immediately, the UI can limit it later.
        execute_query("""
            UPDATE "Role" SET "allowedPages" = '{"Dashboard", "Upload", "Documents", "Reports", "WCDL Tracker", "Forex Register", "Activity", "Audit Logs"}'
            WHERE id IN (2, 3) AND ("allowedPages" IS NULL OR "allowedPages" = '{"*"}');
        """, ())
        
        # We will alter `id` to leverage a sequence if custom roles are to be added,
        # but PostgreSQL requires sequence creation manually if altering an existing int to SERIAL.
        # Since we might have inserted explicitly 0, 1, 2, 3, let's create a sequence strictly starting from 4
        print("Creating sequence for dynamic custom roles...")
        execute_query("""
            CREATE SEQUENCE IF NOT EXISTS role_id_seq START WITH 4;
            ALTER TABLE "Role" ALTER COLUMN id SET DEFAULT nextval('role_id_seq');
        """, ())

        print("Migration 005 complete.")

    except Exception as e:
        print(f"Migration 005 failed: {e}")
        # Ignore duplicate column errors or allow them to bubble gracefully if needed

if __name__ == "__main__":
    run_migration()
