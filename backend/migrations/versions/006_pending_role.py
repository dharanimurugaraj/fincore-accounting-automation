"""
Migration 006: Seed PENDING_APPROVAL Role
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(backend_dir))

from app.core.database import execute_query

def run_migration():
    print("Running migration 006: PENDING_APPROVAL Role")

    try:
        execute_query("""
            INSERT INTO "Role" (name, description, "allowedPages")
            VALUES ('PENDING_APPROVAL', 'Awaiting Administrator Approval', '{}')
            ON CONFLICT (name) DO NOTHING;
        """, ())

        print("Migration 006 complete.")

    except Exception as e:
        print(f"Migration 006 failed: {e}")

if __name__ == "__main__":
    run_migration()
