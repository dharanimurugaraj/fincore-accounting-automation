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

@app.post("/api/v1/process")
async def process_pdfs(
    user: CurrentUser,
    files: List[UploadFile] = File(...)
):
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 1. Intake & Validation (Layer 2)
    temp_dir = Path(settings.LOCAL_STORAGE_PATH) / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    saved_paths = []
    for file in files:
        path = temp_dir / f"{job_id}_{file.filename}"
        with open(path, "wb") as f:
            f.write(await file.read())
        saved_paths.append(str(path))
    
    # 2. Create Job Record in PostgreSQL (Layer 2 Source of Truth)
    execute_insert(
        'INSERT INTO "PipelineRun" (id, "orgId", "statementMonth", status, stage, "startedAt", "createdAt", "progressPercent", "progressMessage") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (job_id, user["org_id"], datetime.now().strftime("%b %Y"), "STAGE1_RUNNING", 1, datetime.utcnow(), datetime.utcnow(), 5, "[UPLOAD] Files received and saved")
    )
    
    # 3. Start PDF Parser Worker (Layer 3)
    pipeline = FinCorePipeline()
    asyncio.create_task(pipeline.run(job_id, saved_paths, user_context=user))
    
    return {"job_id": job_id}

@app.get("/api/v1/process/download")
async def download_file(path: str):
    """ Delivery Service (Layer 6) """
    if not os.path.exists(path):
        return Response(content="File not found", status_code=404)
    return FileResponse(path, filename=os.path.basename(path))



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
