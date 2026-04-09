"""
FastAPI app entry point.
"""

import sys
from pathlib import Path

# Ensure app package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1.router import api_v1_router
from app.services.s3_service import get_storage
from app.core.database import execute_query, execute_insert
from fastapi import UploadFile, File, Response
from fastapi.responses import StreamingResponse, FileResponse
import asyncio
import json
import uuid
from typing import List
from datetime import datetime
import os
from app.pipeline.pipeline import FinCorePipeline
from app.api.deps import CurrentUser

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic — Resilient initialization for Vercel functions
    try:
        from app.core.security import _init_firebase
        _init_firebase()
    except Exception as e:
        print(f"CRITICAL: Firebase init failed: {e}")
    
    yield
    # No explicit pool shutdown needed for direct connections

app = FastAPI(
    title="FinCore API",
    description="AI-powered banking intelligence platform — backend service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for proxy-based communication
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... routes ...
app.include_router(api_v1_router, prefix="/api/v1")

# Static file serving for local storage (Safe for Vercel)
import os
storage_path = Path(settings.LOCAL_STORAGE_PATH)
try:
    if not storage_path.exists():
        storage_path.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"WARN: Could not create storage directory {storage_path}: {e}")

if storage_path.exists():
    app.mount("/files", StaticFiles(directory=str(storage_path)), name="local-files")
else:
    print(f"WARN: Skipping StaticFiles mount - {storage_path} does not exist.")

# ── FinCore Pipeline Logic ───────────────────────────────────────────────────

# Store progress per job_id in memory (Replace with Redis for scale)
job_progress: dict = {}

async def progress_generator(job_id: str):
    """ Streams progress updates to frontend from DB (Resilient SSE) """
    # Yield initial heartbeat
    yield f"data: {json.dumps({'status': 'idle', 'percent': 0})}\n\n"
    
    last_percent = -1
    while True:
        query = 'SELECT "progressPercent", "progressMessage", "progressSubsteps", status FROM "PipelineRun" WHERE id = %s'
        rows = await asyncio.to_thread(execute_query, query, (job_id,))
        if rows:
            run = rows[0]
            current_percent = run["progressPercent"]
            
            # Substeps handling
            sub_steps = []
            if run["progressSubsteps"]:
                try:
                    sub_steps = json.loads(run["progressSubsteps"]) if isinstance(run["progressSubsteps"], str) else run["progressSubsteps"]
                except: sub_steps = []

            if current_percent != last_percent:
                data = {
                    "percent": current_percent,
                    "message": run["progressMessage"],
                    "sub_steps": sub_steps,
                    "status": run["status"]
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_percent = current_percent
                
            if run["status"] in ["APPROVED", "ERROR"]:
                break
        else:
            yield ": heartbeat\n\n"
        await asyncio.sleep(1.0) # Poll DB every second

@app.get("/api/v1/process/progress/{job_id}")
async def get_progress(job_id: str):
    return StreamingResponse(
        progress_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/v1/process/status/{job_id}")
async def get_job_status(job_id: str):
    """ Pollable endpoint for job status (Layer 2/6 - DB Driven) """
    query = 'SELECT status, stage, "workingSheetKey", "bankingReportKey", "errorMessage", "completedAt", "progressPercent", "progressMessage", "progressSubsteps" FROM "PipelineRun" WHERE id = %s'
    rows = await asyncio.to_thread(execute_query, query, (job_id,))
    if not rows:
        return Response(content="Job not found", status_code=404)
    
    run = rows[0]
    
    # Substeps handling
    sub_steps = []
    if run["progressSubsteps"]:
        try:
            sub_steps = json.loads(run["progressSubsteps"]) if isinstance(run["progressSubsteps"], str) else run["progressSubsteps"]
        except: sub_steps = []

    return {
        "job_id": job_id,
        "status": run["status"],
        "stage": run["stage"],
        "working_sheet": run["workingSheetKey"],
        "banking_report": run["bankingReportKey"],
        "error": run["errorMessage"],
        "completed_at": run["completedAt"].isoformat() if run["completedAt"] else None,
        "progress": {
            "percent": run["progressPercent"],
            "message": run["progressMessage"],
            "sub_steps": sub_steps
        }
    }

@app.get("/api/v1/process/active")
async def get_active_job(user: CurrentUser):
    """ Dynamically find the user's current unfinished job (Layer 2/6 - No hardcoding) """
    query = """
        SELECT id FROM "PipelineRun" 
        WHERE "orgId" = %s 
        AND status NOT IN ('APPROVED', 'FAILED', 'VALIDATION_FAILED')
        AND "createdAt" > (NOW() - INTERVAL '10 minutes')
        ORDER BY "createdAt" DESC LIMIT 1
    """
    rows = await asyncio.to_thread(execute_query, query, (user["org_id"],))
    if not rows:
        return {"job_id": None}
    return {"job_id": rows[0]["id"]}

@app.post("/api/v1/process")
async def process_pdfs(
    user: CurrentUser,
    files: List[UploadFile] = File(...)
):
    from app.services.storage_service import derive_org_folder, generate_run_timestamp, get_upload_key, upload_file_object
    from io import BytesIO
    
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    org_folder = derive_org_folder(user["email"])
    run_timestamp = generate_run_timestamp()
    
    # 2. Create Job Record in PostgreSQL (with userId for auditing) - DO THIS FIRST FOR FOREIGN KEY INTEGRITY
    execute_insert(
        """
        INSERT INTO "PipelineRun" 
        (id, "orgId", "userId", "statementMonth", status, stage, "org_folder", "run_timestamp", "startedAt", "createdAt", "progressPercent", "progressMessage") 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            job_id, user["org_id"], user["id"], datetime.now().strftime("%b %Y"), 
            "STAGE1_RUNNING", 1, org_folder, run_timestamp,
            datetime.utcnow(), datetime.utcnow(), 5, "[UPLOAD] Files received and saved to R2"
        )
    )

    # 3. Intake & Upload to R2 (Cloud-First Migration)
    r2_keys = []
    for file in files:
        filename = file.filename
        key = get_upload_key(org_folder, run_timestamp, filename)
        
        # Read file into memory and upload
        content = await file.read()
        file_obj = BytesIO(content)
        await asyncio.to_thread(upload_file_object, file_obj, key, file.content_type)
        r2_keys.append(key)

        # 3.1 Create Upload Record in DB
        upload_id = f"up_{uuid.uuid4().hex[:12]}"
        execute_insert(
            """
            INSERT INTO "Upload" (id, "orgId", "uploadedById", filename, "s3Key", status, "runId", "createdAt")
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (upload_id, user["org_id"], user["id"], filename, key, "UPLOADED", job_id, datetime.utcnow())
        )
    
    # 3. Start PDF Parser Worker (Now using R2 keys)
    pipeline = FinCorePipeline()
    asyncio.create_task(pipeline.run(job_id, r2_keys, user_context=user))
    
    return {"job_id": job_id}

@app.get("/api/v1/process/download")
async def download_file(path: str, user: CurrentUser):
    """ 
    Legacy Delivery Service (Layer 6) - Updated for R2.
    Redirects to a secure R2 presigned URL.
    """
    from app.services.storage_service import generate_presigned_get_url
    from fastapi.responses import RedirectResponse
    
    # 1. Basic Validation
    if not path:
        return Response(content="File path required", status_code=400)
    
    # 2. Security: Verify user belongs to org owning this run (Optional but recommended)
    # For speed in legacy UI, we trust the path if it contains the org folder derived from email
    # but a stricter check would query the DB.
    
    try:
        # If it's already a full URL (rare but possible), just redirect
        if path.startswith("http"):
            return RedirectResponse(path)
            
        # Generate presigned URL from R2
        url = generate_presigned_get_url(path)
        return RedirectResponse(url)
    except Exception as e:
        return Response(content=f"Download failed: {str(e)}", status_code=500)



@app.get("/api/v1/health")
async def health():
    import firebase_admin
    import os
    from app.core.config import settings
    
    # Redacted list of keys for debugging
    fb_keys = [k for k in os.environ.keys() if "FIREBASE" in k]
    
    return {
        "status": "healthy",
        "firebase_initialized": bool(firebase_admin._apps),
        "fb_keys_found": fb_keys,
        "env_vercel": bool(os.getenv("VERCEL")),
        "fb_json_len": len(settings.FIREBASE_SERVICE_ACCOUNT_JSON) if settings.FIREBASE_SERVICE_ACCOUNT_JSON else 0
    }

@app.get("/")
async def root():
    return {
        "service": "FinCore API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
