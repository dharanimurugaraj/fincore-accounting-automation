import uuid
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.database import execute_query, execute_insert
from app.services.storage_service import (
    derive_org_folder, 
    generate_run_timestamp, 
    get_upload_key, 
    generate_presigned_put_url
)
from app.pipeline.pipeline import FinCorePipeline

router = APIRouter()

class RunCreate(BaseModel):
    statement_month: str
    filenames: List[str]

@router.post("")
async def create_run(user: CurrentUser, data: RunCreate):
    """
    Initializes a pipeline run, derives org folder, generates timestamp,
    and returns presigned PUT URLs for direct R2 upload.
    """
    org_id = user["org_id"]
    email = user["email"]
    
    # 1. Derive Storage metadata
    org_folder = derive_org_folder(email)
    run_timestamp = generate_run_timestamp()
    
    # 2. Create PipelineRun record
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    try:
        execute_insert(
            """
            INSERT INTO "PipelineRun" 
            (id, "orgId", "statementMonth", status, stage, "org_folder", "run_timestamp", "startedAt", "createdAt", "progressPercent", "progressMessage") 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                run_id, org_id, data.statement_month, "PENDING", 0, 
                org_folder, run_timestamp, datetime.utcnow(), datetime.utcnow(), 
                0, "Run initialized, pending file uploads"
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create run: {str(e)}")

    # 3. Generate presigned URLs for each file
    uploads = []
    for filename in data.filenames:
        key = get_upload_key(org_folder, run_timestamp, filename)
        presigned_url = generate_presigned_put_url(key)
        
        # Also store upload record (Layer 2)
        upload_id = f"upl_{uuid.uuid4().hex[:12]}"
        execute_insert(
            """
            INSERT INTO "Upload" (id, "orgId", "uploadedById", filename, "s3Key", status, "runId", "createdAt")
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (upload_id, org_id, user["id"], filename, key, "UPLOADED", run_id, datetime.utcnow())
        )
        
        uploads.append({
            "filename": filename,
            "s3_key": key,
            "presigned_url": presigned_url
        })

    return {
        "run_id": run_id,
        "org_folder": org_folder,
        "run_timestamp": run_timestamp,
        "uploads": uploads
    }

@router.post("/{run_id}/start")
async def start_run(run_id: str, user: CurrentUser):
    """
    Triggers the actual pipeline execution after files are uploaded.
    """
    # Verify run exists and belongs to org
    rows = execute_query(
        'SELECT id, "org_folder", "run_timestamp" FROM "PipelineRun" WHERE id = %s AND "orgId" = %s',
        (run_id, user["org_id"])
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = rows[0]
    
    # Update status to staged
    execute_query(
        'UPDATE "PipelineRun" SET status = %s, stage = 1 WHERE id = %s',
        ("STAGE1_RUNNING", run_id)
    )

    # Get all upload keys for this run
    upload_rows = execute_query(
        'SELECT "s3Key" FROM "Upload" WHERE "runId" = %s',
        (run_id,)
    )
    s3_keys = [r["s3Key"] for r in upload_rows]

    if not s3_keys:
        raise HTTPException(status_code=400, detail="No files uploaded for this run")

    # Pass to pipeline (using asyncio.create_task for now as Celery isn't fully wired)
    # Using the existing pipeline runner logic
    import asyncio
    pipeline = FinCorePipeline()
    # Note: We pass the keys directly. Pipeline will need to be updated to download from R2.
    asyncio.create_task(pipeline.run(run_id, s3_keys, user_context=user))

    return {"run_id": run_id, "status": "started"}

@router.get("")
async def list_runs(user: CurrentUser, limit: int = 50, offset: int = 0):
    """
    Lists all runs for the authenticated user's organization with associated uploads.
    Super Admins (Role 0) see across ALL organizations.
    """
    is_super_admin = user.get("role_id") == 0
    
    if is_super_admin:
        query = """
            SELECT pr.id, pr."statementMonth", pr.status, pr.stage, pr."orgId", pr."org_folder", pr."run_timestamp", 
                   pr."validationResult", pr."errorMessage", pr."startedAt", pr."completedAt", pr."createdAt",
                   pr."workingSheetKey", pr."bankingReportKey", u.email as "user_email"
            FROM "PipelineRun" pr
            LEFT JOIN "User" u ON pr."userId" = u.id
            ORDER BY pr."createdAt" DESC
            LIMIT %s OFFSET %s
        """
        params = (limit, offset)
    else:
        query = """
            SELECT pr.id, pr."statementMonth", pr.status, pr.stage, pr."orgId", pr."org_folder", pr."run_timestamp", 
                   pr."validationResult", pr."errorMessage", pr."startedAt", pr."completedAt", pr."createdAt",
                   pr."workingSheetKey", pr."bankingReportKey", u.email as "user_email"
            FROM "PipelineRun" pr
            LEFT JOIN "User" u ON pr."userId" = u.id
            WHERE pr."orgId" = %s
            ORDER BY pr."createdAt" DESC
            LIMIT %s OFFSET %s
        """
        params = (user["org_id"], limit, offset)

    rows = execute_query(query, params)
    
    # Enrich runs with their associated uploads for "Directory Mapping"
    enriched_runs = []
    for run in rows:
        uploads = execute_query(
            """
            SELECT up.id, up.filename, up."s3Key", up.status, u.email as "uploaded_by" 
            FROM "Upload" up
            LEFT JOIN "User" u ON up."uploadedById" = u.id
            WHERE up."runId" = %s
            """,
            (run["id"],)
        )
        run_dict = dict(run)
        run_dict["uploads"] = uploads
        enriched_runs.append(run_dict)

    return {"runs": enriched_runs}
