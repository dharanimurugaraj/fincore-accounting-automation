"""
PostgreSQL connection helpers.
Wraps psycopg2 for synchronous DB access.

All modules use `execute_query` / `execute_insert` — never raw psycopg2.
"""

import json
from datetime import datetime
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL


def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in environment variables.")
    try:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"DATABASE_ERROR: Failed to connect to PostgreSQL: {e}")
        raise


@contextmanager
def get_db():
    conn = None
    try:
        conn = get_connection()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"DATABASE_ERROR: Session failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def execute_query(query: str, params: tuple = None) -> list[dict]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            return []


def execute_insert(query: str, params: tuple = None) -> dict | None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchone()
            return None


def update_pipeline_status(run_id: str, status: str, stage: int = None,
                           error: str = None, metadata: dict = None):
    """Update pipeline run status in PostgreSQL."""
    parts = ["status = %s"]
    params: list = [status]

    if stage is not None:
        parts.append("stage = %s")
        params.append(stage)

    if error is not None:
        parts.append('"errorMessage" = %s')
        params.append(error)

    if metadata is not None:
        parts.append('"validationResult" = %s')
        params.append(json.dumps(metadata))

    if status in ("STAGE1_RUNNING",):
        parts.append('"startedAt" = %s')
        params.append(datetime.utcnow())

    if status in ("APPROVED", "FAILED", "VALIDATION_FAILED"):
        parts.append('"completedAt" = %s')
        params.append(datetime.utcnow())

    params.append(run_id)
    set_clause = ", ".join(parts)

    execute_query(
        f'UPDATE "PipelineRun" SET {set_clause} WHERE id = %s',
        tuple(params),
    )


def update_pipeline_s3_key(run_id: str, key_field: str, s3_key: str):
    """Update a specific S3 key field on a pipeline run."""
    allowed = {"statementExcelKey", "workingSheetKey", "bankingReportKey"}
    if key_field not in allowed:
        raise ValueError(f"Invalid key field: {key_field}")
    execute_query(
        f'UPDATE "PipelineRun" SET "{key_field}" = %s WHERE id = %s',
        (s3_key, run_id),
    )
