import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings

logger = logging.getLogger("fincore.db")

from contextlib import contextmanager

def get_db_connection():
    """Create a new direct connection to the database (Best for Serverless)."""
    url = settings.DATABASE_URL
    if not url:
        raise ValueError("DATABASE_URL environment variable is missing.")
    
    # Force SSL for cloud providers like Prisma/Neon/AWS
    ssl = 'require' if 'prisma' in url or '.io' in url or 'neon' in url else 'prefer'
    
    return psycopg2.connect(
        url,
        cursor_factory=RealDictCursor,
        sslmode=ssl,
        connect_timeout=5
    )

@contextmanager
def get_db():
    """Context manager for DB connections — for legacy compatibility."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_query(query: str, params: tuple = None):
    """Execute a query and close connection immediately."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            conn.commit()
            return []
    except Exception as e:
        print(f"DB Query Failed: {e}")
        logger.error(f"DB Query Failed: {e}")
        raise
    finally:
        conn.close()

def execute_insert(query: str, params: tuple = None):
    """Execute insert and return RETURNING values."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            result = cur.fetchone() if cur.description else None
            conn.commit()
            return result
    except Exception as e:
        logger.error(f"DB Insert Failed: {e}")
        raise
    finally:
        conn.close()

def update_pipeline_status(run_id: str, status: str, **kwargs):
    # Simplified helper for status updates
    pass 
