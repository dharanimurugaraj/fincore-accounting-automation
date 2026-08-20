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
            # Increased max connections to 20 to handle concurrent parsing threads + UI polling
            _pool = ThreadedConnectionPool(2, 20, url, cursor_factory=RealDictCursor)
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
    # Python (psycopg2) CANNOT talk to prisma.io/sk_... proxies over standard TCP easily.
    # We must try to divert to a direct connection if available.
    direct_url = os.getenv("DIRECT_DATABASE_URL") or os.getenv("POSTGRES_URL_NON_POOLING")
    
    if direct_url and "prisma.io" not in direct_url:
        logger.info("Production Fix: Diverting Python traffic to DIRECT Connection string.")
        url = direct_url
    elif "prisma.io" in url or "sk_" in url:
        logger.warning("CRITICAL: Python is connecting to a Prisma Proxy. This may cause 504 timeouts.")
        logger.info("TIP: If you experience timeouts, add DIRECT_DATABASE_URL to Vercel.")

    # Robust Connection Parameters for Proxy environments
    connect_args = {
        "cursor_factory": RealDictCursor,
        "connect_timeout": 7, # Give it time to resolve, but fail fast enough to retry within proxy limits
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }

    # Determine SSL
    ssl = 'require' if ('prisma' in url or '.io' in url or 'neon' in url or 'sslmode=require' in url) else 'prefer'
    
    # Retry logic (3 attempts - total max 21s)
    last_err = None
    for attempt in range(3):
        try:
            # Detect Neon direct vs pooled
            if "neon.tech" in url and "-pooler" not in url and attempt == 0:
                logger.debug("Neon detected: Connecting to direct endpoint. This may be slower during cold starts.")
            
            return psycopg2.connect(url, sslmode=ssl, **connect_args)
        except Exception as e:
            last_err = e
            logger.warning(f"Database connection attempt {attempt+1}/3 failed: {e}")
            if "connection limit" in str(e).lower() or "too many connections" in str(e).lower():
                logger.error("TIP: You are hitting Neon/Postgres connection limits. Add a POOLED connection string to DATABASE_URL.")
            
            if attempt < 2:
                import time
                time.sleep(1) # Wait between retries
    
    logger.error(f"DATABASE CONNECT FAILED after all attempts: {last_err}")
    # Provide a more helpful error for the Proxy to catch
    raise ConnectionError(f"Backend failed to connect to database. Check DATABASE_URL in Vercel. Error: {str(last_err)}")



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


def execute_values_insert(query: str, values: list, page_size: int = 100):
    """
    High-performance batch insertion using psycopg2.extras.execute_values.
    Significantly reduces SSL handshake overhead in serverless/proxy environments.
    """
    from psycopg2.extras import execute_values
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, query, values, page_size=page_size)
            conn.commit()
    except Exception as e:
        logger.error(f"DB Batch Insert Failed: {e}")
        conn.rollback()
        raise
    finally:
        pool = _get_pool()
        if pool:
            pool.putconn(conn)
        else:
            conn.close()

def update_pipeline_s3_key(run_id: str, field: str, s3_key: str):
    """Update a specific S3 key field in the PipelineRun."""
    # Validate field name against known columns
    allowed = {"statementExcelKey", "workingSheetKey", "bankingReportKey", "fxSheetKey"}
    if field not in allowed:
        logger.error(f"Invalid pipeline field update: {field}")
        return
        
    query = f'UPDATE "PipelineRun" SET "{field}" = %s, "updatedAt" = NOW() WHERE id = %s'
    execute_query(query, (s3_key, run_id))
