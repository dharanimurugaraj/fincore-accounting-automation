"""
POST /pipeline/run, GET /pipeline/{id}/status
POST /pipeline/confirm, POST /pipeline/approve
"""

import json
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query

from app.schemas.statement import (
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineStatusResponse,
    PipelineConfirmReviewRequest,
    PipelineApprovalRequest,
    PipelineRunListItem,
    RunStatusEnum,
    DownloadURLResponse,
)
from app.core.database import execute_query, execute_insert

router = APIRouter()


@router.post("/run", response_model=PipelineRunResponse)
async def trigger_pipeline(req: PipelineRunRequest, background_tasks: BackgroundTasks):
    """Trigger the 3-stage pipeline."""
    run_id = f"run_{uuid.uuid4().hex[:16]}"

    execute_insert(
        """
        INSERT INTO "PipelineRun" (id, "orgId", "statementMonth", status, stage, "createdAt")
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (run_id, req.org_id, req.statement_month, RunStatusEnum.PENDING.value, 0, datetime.utcnow()),
    )

    pdf_s3_keys = []

    if req.pdf_s3_keys:
        pdf_s3_keys = req.pdf_s3_keys
    elif req.upload_ids:
        upload_rows = execute_query(
            'SELECT "s3Key" FROM "Upload" WHERE id = ANY(%s)',
            (req.upload_ids,),
        )
        pdf_s3_keys = [row["s3Key"] for row in upload_rows]
        execute_query(
            'UPDATE "Upload" SET "runId" = %s WHERE id = ANY(%s)',
            (run_id, req.upload_ids),
        )

    if not pdf_s3_keys:
        raise HTTPException(
            status_code=400,
            detail="No PDF keys found. Provide either upload_ids or pdf_s3_keys.",
        )

    from app.pipeline.graph import run_pipeline
    background_tasks.add_task(
        run_pipeline,
        run_id=run_id,
        pdf_s3_keys=pdf_s3_keys,
        org_id=req.org_id,
        month=req.statement_month,
    )

    return PipelineRunResponse(
        run_id=run_id,
        status=RunStatusEnum.PENDING,
        message="Pipeline started. Poll /api/v1/pipeline/status/{run_id} for progress.",
    )


@router.get("/status/{run_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(run_id: str):
    """Poll pipeline status."""
    rows = execute_query(
        """
        SELECT id, status, stage, "statementMonth",
               "statementExcelKey", "workingSheetKey", "bankingReportKey",
               "validationResult", "errorMessage",
               "startedAt", "completedAt"
        FROM "PipelineRun"
        WHERE id = %s
        """,
        (run_id,),
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    run = rows[0]
    validation = None
    if run["validationResult"]:
        try:
            validation = json.loads(run["validationResult"])
        except (json.JSONDecodeError, TypeError):
            validation = None

    review_fields = None
    if run["status"] == RunStatusEnum.STAGE1_REVIEW.value and validation:
        review_fields = validation.get("review_required", [])

    return PipelineStatusResponse(
        run_id=run["id"],
        status=RunStatusEnum(run["status"]),
        stage=run["stage"],
        statement_month=run["statementMonth"],
        statement_excel_key=run["statementExcelKey"],
        working_sheet_key=run["workingSheetKey"],
        banking_report_key=run["bankingReportKey"],
        validation_result=validation,
        error_message=run["errorMessage"],
        started_at=run["startedAt"],
        completed_at=run["completedAt"],
        review_fields=review_fields,
    )


@router.post("/confirm", response_model=PipelineRunResponse)
async def confirm_review(req: PipelineConfirmReviewRequest, background_tasks: BackgroundTasks):
    """User confirms low-confidence OCR fields. Resumes pipeline from Stage 2."""
    rows = execute_query(
        'SELECT id, status FROM "PipelineRun" WHERE id = %s',
        (req.run_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Run not found")

    run = rows[0]
    if run["status"] != RunStatusEnum.STAGE1_REVIEW.value:
        raise HTTPException(
            status_code=400,
            detail=f"Run is in status {run['status']}, not STAGE1_REVIEW",
        )

    from app.pipeline.graph import resume_pipeline_from_stage2
    background_tasks.add_task(resume_pipeline_from_stage2, run_id=req.run_id)

    return PipelineRunResponse(
        run_id=req.run_id,
        status=RunStatusEnum.STAGE2_RUNNING,
        message="Review confirmed. Pipeline resuming from Stage 2.",
    )


@router.post("/approve", response_model=PipelineRunResponse)
async def approve_run(req: PipelineApprovalRequest):
    """Human approval gate — enables report download."""
    rows = execute_query(
        'SELECT id, status FROM "PipelineRun" WHERE id = %s',
        (req.run_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Run not found")

    run = rows[0]
    if run["status"] != RunStatusEnum.AWAITING_APPROVAL.value:
        raise HTTPException(
            status_code=400,
            detail=f"Run is in status {run['status']}, not AWAITING_APPROVAL",
        )

    execute_query(
        """
        UPDATE "PipelineRun"
        SET status = %s, "completedAt" = %s
        WHERE id = %s
        """,
        (RunStatusEnum.APPROVED.value, datetime.utcnow(), req.run_id),
    )

    approval_id = f"appr_{uuid.uuid4().hex[:12]}"
    execute_insert(
        """
        INSERT INTO "Approval" (id, "runId", "userId", "createdAt")
        VALUES (%s, %s, %s, %s)
        """,
        (approval_id, req.run_id, req.user_id, datetime.utcnow()),
    )

    audit_id = f"aud_{uuid.uuid4().hex[:12]}"
    execute_insert(
        """
        INSERT INTO "AuditLog" (id, "orgId", "userId", action, "entityType", "entityId", "createdAt")
        SELECT %s, "orgId", %s, 'APPROVED', 'PipelineRun', %s, %s
        FROM "PipelineRun" WHERE id = %s
        """,
        (audit_id, req.user_id, req.run_id, datetime.utcnow(), req.run_id),
    )

    return PipelineRunResponse(
        run_id=req.run_id,
        status=RunStatusEnum.APPROVED,
        message="Run approved. Reports are now available for download.",
    )


@router.get("/runs", response_model=list[PipelineRunListItem])
async def list_pipeline_runs(
    org_id: str = Query(...),
    limit: int = Query(20, le=100),
):
    """List all pipeline runs for an organisation."""
    rows = execute_query(
        """
        SELECT pr.id, pr."statementMonth", pr.status, pr.stage,
               pr."statementExcelKey", pr."workingSheetKey", pr."bankingReportKey",
               pr."createdAt", pr."completedAt",
               COUNT(u.id) as upload_count
        FROM "PipelineRun" pr
        LEFT JOIN "Upload" u ON u."runId" = pr.id
        WHERE pr."orgId" = %s
        GROUP BY pr.id
        ORDER BY pr."createdAt" DESC
        LIMIT %s
        """,
        (org_id, limit),
    )

    return [
        PipelineRunListItem(
            run_id=row["id"],
            statement_month=row["statementMonth"],
            status=RunStatusEnum(row["status"]),
            stage=row["stage"],
            upload_count=row["upload_count"],
            statement_excel_key=row["statementExcelKey"],
            working_sheet_key=row["workingSheetKey"],
            banking_report_key=row["bankingReportKey"],
            created_at=row["createdAt"],
            completed_at=row["completedAt"],
        )
        for row in rows
    ]


@router.get("/{run_id}/download/{file_type}", response_model=DownloadURLResponse)
async def download_file(run_id: str, file_type: str):
    """Return a local download URL for a pipeline output."""
    key_map = {
        "statement_excel": "statementExcelKey",
        "working_sheet": "workingSheetKey",
        "banking_report": "bankingReportKey",
    }
    if file_type not in key_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file_type '{file_type}'. Must be one of: {list(key_map.keys())}",
        )

    rows = execute_query(
        f'SELECT status, "{key_map[file_type]}" as s3_key FROM "PipelineRun" WHERE id = %s',
        (run_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Run not found")

    run = rows[0]
    if run["status"] != RunStatusEnum.APPROVED.value:
        raise HTTPException(status_code=403, detail="Reports can only be downloaded after approval.")

    s3_key = run["s3_key"]
    if not s3_key:
        raise HTTPException(status_code=404, detail=f"{file_type} has not been generated yet.")

    url = f"/files/{s3_key}"
    return DownloadURLResponse(url=url, expires_in_seconds=86400)
