"""
PostgreSQL connection helpers.
Wraps psycopg2 for synchronous DB access with connection pooling.

All modules use `execute_query` / `execute_insert` — never raw psycopg2.
"""

import json
import logging
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL
logger = logging.getLogger("fincore.db")

# Initialize connection pool singleton
# We use ThreadedConnectionPool for FastAPI dev servers (which are multi-threaded)
_pool: Optional[ThreadedConnectionPool] = None

def get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL is not set in environment variables.")
        try:
            # Min 1, Max 10 connections. Adjust based on load.
            _pool = ThreadedConnectionPool(
                1, 10, 
                DATABASE_URL, 
                cursor_factory=RealDictCursor,
                sslmode='require' if 'prisma.io' in DATABASE_URL else 'prefer'
            )
            logger.info("Database connection pool initialized.")
        except Exception as e:
            logger.error(f"DATABASE_ERROR: Failed to initialize pool: {e}")
            raise
    return _pool


def close_pool():
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Database connection pool closed.")


@contextmanager
def get_db():
    """Get a connection from the pool and return it when done."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"DATABASE_ERROR: Transaction failed: {e}")
        raise
    finally:
        pool.putconn(conn)


def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """Execute a SELECT query and return all results as dicts."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            return []


def execute_insert(query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
    """Execute an INSERT/UPDATE/DELETE and return one result (for RETURNING)."""
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
