"""
Migration 004: Role Refactoring (Enum -> Table-based RBAC)
Creates 'Role' table and migrates User.role enum to User.roleId.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration():
    if not DATABASE_URL:
        print("DATABASE_URL not found in .env")
        return

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("[migration] Managing type name collisions (Role type vs Role table)...")
    try:
        cur.execute('DO $$ BEGIN ALTER TYPE "Role" RENAME TO "RoleEnum"; EXCEPTION WHEN undefined_object THEN null; END $$;')
    except Exception as e:
        print(f"[migration] Skipping type rename (likely already handled): {e}")

    print("[migration] Creating 'Role' table...")
    CREATE_ROLE_TABLE = """
    CREATE TABLE IF NOT EXISTS "Role" (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    );
    """
    cur.execute(CREATE_ROLE_TABLE)

    print("[migration] Seeding initial roles (0: SUPER_ADMIN, 1: ADMIN, 2: ANALYST, 3: VIEWER)...")
    SEED_ROLES = """
    INSERT INTO "Role" (id, name, description) VALUES 
    (0, 'SUPER_ADMIN', 'Platform-wide total access'),
    (1, 'ADMIN', 'Organization-level administration'),
    (2, 'ANALYST', 'Standard organization user'),
    (3, 'VIEWER', 'Read-only organization access')
    ON CONFLICT (id) DO UPDATE SET 
        name = EXCLUDED.name,
        description = EXCLUDED.description;
    """
    cur.execute(SEED_ROLES)

    print("[migration] Adding 'roleId' to 'User' table...")
    try:
        cur.execute('ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "roleId" INTEGER REFERENCES "Role"(id);')
    except Exception as e:
        print(f"[migration] Note: Column addition handled. Info: {e}")

    print("[migration] Migrating existing user roles to numeric IDs...")
    # Map Enum strings to the new numeric IDs
    MIGRATE_USER_ROLES = """
    -- Use pg_typeof to check if role exists as an enum column
    DO $$ 
    BEGIN 
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='User' AND column_name='role') THEN
            UPDATE "User" SET "roleId" = 1 WHERE role::text = 'ADMIN';
            UPDATE "User" SET "roleId" = 2 WHERE role::text = 'ANALYST' OR role IS NULL;
            UPDATE "User" SET "roleId" = 3 WHERE role::text = 'VIEWER';
        ELSE
            -- Default for new users if role column was already gone
            UPDATE "User" SET "roleId" = 2 WHERE "roleId" IS NULL;
        END IF;
    END $$;
    """
    cur.execute(MIGRATE_USER_ROLES)

    print("[migration] Finalizing schema (NOT NULL and DROP legacy enum column)...")
    try:
        cur.execute('ALTER TABLE "User" ALTER COLUMN "roleId" SET NOT NULL;')
        cur.execute('ALTER TABLE "User" DROP COLUMN IF EXISTS "role";')
        print("[migration] Legacy 'role' enum column dropped.")
    except Exception as e:
        print(f"[migration] Error finalizing User table: {e}")

    cur.close()
    conn.close()
    print("[migration] Migration 004 (Role Refactor) completed.")

if __name__ == "__main__":
    run_migration()
