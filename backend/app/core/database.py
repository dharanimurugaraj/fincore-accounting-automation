import json
import logging
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from app.core.config import settings


logger = logging.getLogger("fincore.db")

# Global pool for local development (Lazy initialized)
_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        url = settings.DATABASE_URL
        if not url:
            raise ValueError("DATABASE_URL is missing.")
        
        # Determine pool size
        is_vercel = os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        
        if is_vercel:
            return None
            
        try:
            logger.info(f"Initializing Local Connection Pool -> {url.split('@')[-1]}")
            _pool = ThreadedConnectionPool(1, 10, url, cursor_factory=RealDictCursor)
        except Exception as e:
            logger.error(f"FAILED to initialize local pool: {e}")
            logger.error("TIP: If you are using Prisma Accelerate, ensure you have provided the DIRECT CONNECTION URL (pointing to the actual DB host) instead of the proxy URL.")
            return None # Fallback to direct connections which might give better errors
        
    return _pool


def get_db_connection():
    """Create or retrieve a connection. Uses pool locally, direct in serverless."""
    pool = _get_pool()
    
    if pool:
        return pool.getconn()
        
    # Serverless fallback (Direct connection)
    url = settings.DATABASE_URL
    
    # 🏹 PRISMA ACCELERATE COMPATIBILITY FIX
    # Python (psycopg2) CANNOT talk to prisma.io/sk_... proxies.
    # It will hang and cause a 504. We must use a DIRECT connection URL here.
    if "prisma.io" in url or "sk_" in url:
        # Check standard direct URL variables provided by Prisma/Vercel
        alternatives = [
            os.getenv("DIRECT_DATABASE_URL"),
            os.getenv("POSTGRES_URL_NON_POOLING"),
            os.getenv("PSQL_DIRECT_URL")
        ]
        
        # Pick the first one that exists and is NOT a prisma proxy
        valid_fallback = next((a for a in alternatives if a and "prisma.io" not in a), None)
        
        if valid_fallback:
            logger.info("Production Fix: Diverting Python traffic to DIRECT Connection string.")
            url = valid_fallback
        else:
            logger.warning("CRITICAL: Python is connecting to a Prisma Proxy with NO DIRECT fallback.")
            logger.warning("TIP: Find the 'Direct connection string' in Prisma Console and add it as DIRECT_DATABASE_URL in Vercel.")
    
    try:
        # If sslmode is already in the URL, don't pass it as a separate param 
        if 'sslmode=' in url:
            return psycopg2.connect(url, cursor_factory=RealDictCursor, connect_timeout=3)

        ssl = 'require' if 'prisma' in url or '.io' in url or 'neon' in url else 'prefer'
        return psycopg2.connect(url, cursor_factory=RealDictCursor, sslmode=ssl, connect_timeout=3)
    except Exception as e:
        logger.error(f"DATABASE CONNECT FAILED: {e}")
        # Re-raise with more context
        raise ConnectionError(f"Database connection blocked. Error: {str(e)}")



@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        pool = _get_pool()
        if pool:
            pool.putconn(conn)
        else:
            conn.close()

def execute_query(query: str, params: tuple = None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            conn.commit()
            return []
    except Exception as e:
        logger.error(f"DB Query Failed: {e}")
        raise
    finally:
        pool = _get_pool()
        if pool:
            pool.putconn(conn)
        else:
            conn.close()

def execute_insert(query: str, params: tuple = None):
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
        pool = _get_pool()
        if pool:
            pool.putconn(conn)
        else:
            conn.close()


def update_pipeline_status(run_id: str, status: str, stage: int = None, metadata: dict = None, error: str = None):
    """Update pipeline run status, stage, and metadata."""
    query = 'UPDATE "PipelineRun" SET status = %s'
    params = [status]
    
    if stage is not None:
        query += ', stage = %s'
        params.append(stage)
        
    if metadata:
        query += ', metadata = %s'
        params.append(json.dumps(metadata))
        
    if error:
        query += ', "errorMessage" = %s'
        params.append(error)
        
    query += ', "updatedAt" = NOW() WHERE id = %s'
    params.append(run_id)
    
    execute_query(query, tuple(params))


def update_pipeline_s3_key(run_id: str, field: str, s3_key: str):
    """Update a specific S3 key field in the PipelineRun."""
    # Validate field name against known columns
    allowed = {"statementExcelKey", "workingSheetKey", "bankingReportKey"}
    if field not in allowed:
        logger.error(f"Invalid pipeline field update: {field}")
        return
        
    query = f'UPDATE "PipelineRun" SET "{field}" = %s, "updatedAt" = NOW() WHERE id = %s'
    execute_query(query, (s3_key, run_id))
