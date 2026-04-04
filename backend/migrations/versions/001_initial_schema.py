"""
Initialize PostgreSQL database for local FinCore development.

Creates the fincore_dev database, all required tables (matching the Prisma schema),
enums, and seeds a default organisation + dev user.

Usage:
    cd backend

    # If your postgres superuser has a password:
    set PG_ADMIN_USER=postgres
    set PG_ADMIN_PASSWORD=yourpassword
    python db/init_db.py

    # Or use DATABASE_URL directly if the user/db already exist:
    python db/init_db.py --skip-create-db
"""

import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://fincore:fincore_dev@localhost:5432/fincore_dev")

PG_ADMIN_USER = os.getenv("PG_ADMIN_USER", "postgres")
PG_ADMIN_PASSWORD = os.getenv("PG_ADMIN_PASSWORD", "")


def parse_db_url(url: str):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return {
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "dbname": parsed.path.lstrip("/") or "fincore_dev",
    }


def ensure_database_and_role(params: dict):
    """Connect to 'postgres' database as admin and create role + database if needed."""
    admin_password = PG_ADMIN_PASSWORD
    admin_user = PG_ADMIN_USER

    conn = psycopg2.connect(
        user=admin_user,
        password=admin_password,
        host=params["host"],
        port=params["port"],
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    target_user = params["user"]
    target_password = params["password"]
    target_db = params["dbname"]

    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (target_user,))
    if not cur.fetchone():
        cur.execute(f"CREATE ROLE \"{target_user}\" WITH LOGIN PASSWORD %s", (target_password,))
        print(f"[init_db] Created role: {target_user}")
    else:
        print(f"[init_db] Role '{target_user}' already exists")

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{target_db}" OWNER "{target_user}"')
        print(f"[init_db] Created database: {target_db}")
    else:
        print(f"[init_db] Database '{target_db}' already exists")

    cur.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{target_db}" TO "{target_user}"')

    cur.close()
    conn.close()


CREATE_ENUMS = """
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'Role') THEN
        CREATE TYPE "Role" AS ENUM ('ADMIN', 'ANALYST', 'VIEWER');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'UploadStatus') THEN
        CREATE TYPE "UploadStatus" AS ENUM ('UPLOADED', 'OCR_RUNNING', 'OCR_COMPLETE', 'OCR_FAILED', 'NEEDS_REVIEW');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'RunStatus') THEN
        CREATE TYPE "RunStatus" AS ENUM (
            'PENDING', 'STAGE1_RUNNING', 'STAGE1_REVIEW', 'STAGE2_RUNNING',
            'STAGE3_RUNNING', 'VALIDATION_FAILED', 'AWAITING_APPROVAL', 'APPROVED', 'FAILED'
        );
    END IF;
END $$;
"""

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS "Organisation" (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "User" (
    id         TEXT PRIMARY KEY,
    email      TEXT UNIQUE NOT NULL,
    name       TEXT,
    role       "Role" NOT NULL DEFAULT 'ANALYST',
    "orgId"    TEXT NOT NULL REFERENCES "Organisation"(id),
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "PipelineRun" (
    id                  TEXT PRIMARY KEY,
    "orgId"             TEXT NOT NULL REFERENCES "Organisation"(id),
    "statementMonth"    TEXT NOT NULL,
    status              "RunStatus" NOT NULL DEFAULT 'PENDING',
    stage               INT NOT NULL DEFAULT 0,
    "statementExcelKey" TEXT,
    "workingSheetKey"   TEXT,
    "bankingReportKey"  TEXT,
    "validationResult"  TEXT,
    "errorMessage"      TEXT,
    "startedAt"         TIMESTAMPTZ,
    "completedAt"       TIMESTAMPTZ,
    "createdAt"         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "Upload" (
    id               TEXT PRIMARY KEY,
    "orgId"          TEXT NOT NULL REFERENCES "Organisation"(id),
    "uploadedById"   TEXT NOT NULL REFERENCES "User"(id),
    filename         TEXT NOT NULL,
    "s3Key"          TEXT UNIQUE NOT NULL,
    "bankName"       TEXT NOT NULL,
    "accountType"    TEXT NOT NULL,
    "accountId"      TEXT NOT NULL,
    "statementMonth" TEXT NOT NULL,
    "fileSizeBytes"  INT NOT NULL,
    status           "UploadStatus" NOT NULL DEFAULT 'UPLOADED',
    "createdAt"      TIMESTAMPTZ NOT NULL DEFAULT now(),
    "runId"          TEXT REFERENCES "PipelineRun"(id)
);

CREATE TABLE IF NOT EXISTS "Approval" (
    id         TEXT PRIMARY KEY,
    "runId"    TEXT NOT NULL REFERENCES "PipelineRun"(id),
    "userId"   TEXT NOT NULL REFERENCES "User"(id),
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "AuditLog" (
    id           TEXT PRIMARY KEY,
    "orgId"      TEXT NOT NULL,
    "userId"     TEXT NOT NULL,
    action       TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "entityId"   TEXT NOT NULL,
    metadata     TEXT,
    "createdAt"  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

SEED_DATA = """
INSERT INTO "Organisation" (id, name)
VALUES ('default-org', 'FinCore Dev Org')
ON CONFLICT (id) DO NOTHING;

INSERT INTO "User" (id, email, name, role, "orgId")
VALUES ('dev-user', 'dev@fincore.local', 'Dev User', 'ADMIN', 'default-org')
ON CONFLICT (id) DO NOTHING;
"""


def create_tables_and_seed(db_url: str):
    """Connect to the target database and create tables + seed data."""
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    print("[init_db] Creating enums...")
    cur.execute(CREATE_ENUMS)

    print("[init_db] Creating tables...")
    cur.execute(CREATE_TABLES)

    print("[init_db] Seeding default org + dev user...")
    cur.execute(SEED_DATA)

    cur.close()
    conn.close()

    print("[init_db] Done! Database is ready.")
    print("[init_db] Dev login: dev@fincore.local / dev")


def main():
    parser = argparse.ArgumentParser(description="Initialize FinCore PostgreSQL database")
    parser.add_argument("--skip-create-db", action="store_true",
                        help="Skip database/role creation (use if they already exist)")
    args = parser.parse_args()

    params = parse_db_url(DATABASE_URL)
    print(f"[init_db] Target: {params['host']}:{params['port']}/{params['dbname']} (user: {params['user']})")

    if not args.skip_create_db:
        print(f"[init_db] Admin user: {PG_ADMIN_USER}")
        print(f"[init_db] Set PG_ADMIN_USER / PG_ADMIN_PASSWORD env vars if the defaults don't work")
        try:
            ensure_database_and_role(params)
        except psycopg2.OperationalError as e:
            print(f"\n[init_db] Could not connect as admin user '{PG_ADMIN_USER}'.")
            print(f"[init_db] Error: {e}")
            print(f"[init_db] Options:")
            print(f"  1. Set PG_ADMIN_USER and PG_ADMIN_PASSWORD environment variables")
            print(f"  2. Create the database/role manually:")
            print(f"     CREATE ROLE fincore WITH LOGIN PASSWORD 'fincore_dev';")
            print(f"     CREATE DATABASE fincore_dev OWNER fincore;")
            print(f"  3. Re-run with: python db/init_db.py --skip-create-db")
            print()
            response = input("Try --skip-create-db (assuming DB already exists)? [y/N] ")
            if response.lower() != "y":
                sys.exit(1)

    create_tables_and_seed(DATABASE_URL)


if __name__ == "__main__":
    main()
