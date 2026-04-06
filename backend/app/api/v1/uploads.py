"""
POST /uploads, GET /uploads — file upload and listing.
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.services.s3_service import get_storage
from app.schemas.upload import (
    UploadCompleteRequest,
    UploadResponse,
    DocumentListResponse,
    UploadStatusEnum,
)
from app.core.database import execute_query, execute_insert
from app.api.deps import CurrentUser

router = APIRouter()
storage = get_storage()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user: CurrentUser,
    statement_month: str = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """List all uploaded documents for an organisation."""
    query = """
        SELECT id, filename, "s3Key", "bankName", "accountType",
               "accountId", "statementMonth", status, "createdAt"
        FROM "Upload"
        WHERE "orgId" = %s
    """
    params: list = [user["org_id"]]

    if statement_month:
        query += ' AND "statementMonth" = %s'
        params.append(statement_month)

    count_query = 'SELECT COUNT(*) FROM "Upload" WHERE "orgId" = %s'
    if statement_month:
        count_query += ' AND "statementMonth" = %s'

    query += ' ORDER BY "createdAt" DESC LIMIT %s OFFSET %s'
    params_with_pagination = params + [limit, offset]

    rows = execute_query(query, tuple(params_with_pagination))
    count_rows = execute_query(count_query, tuple(params))
    total = count_rows[0]["count"] if count_rows else 0

    documents = [
        UploadResponse(
            id=row["id"],
            filename=row["filename"],
            s3_key=row["s3Key"],
            bank_name=row["bankName"],
            account_type=row["accountType"],
            account_id=row["accountId"],
            statement_month=row["statementMonth"],
            status=UploadStatusEnum(row["status"]),
            created_at=row["createdAt"],
        )
        for row in rows
    ]

    return DocumentListResponse(documents=documents, total=total)


@router.post("/upload-files")
async def upload_files(
    user: CurrentUser,
    files: List[UploadFile] = File(...),
    statement_month: str = Form(...),
    customer_id: Optional[str] = Form(None),
):
    """Accept multipart file uploads, save to local storage, register in DB."""
    results = []
    org_id = user["org_id"]
    uploaded_by_id = user["id"]

    for upload_file in files:
        filename = upload_file.filename or f"unnamed_{uuid.uuid4().hex[:8]}.pdf"
        file_bytes = await upload_file.read()

        year_mo = statement_month.split("-")
        key = f"uploads/{org_id}/{year_mo[0]}/{year_mo[1]}/{int(datetime.utcnow().timestamp())}_{filename}"

        storage.save_upload(file_bytes, key)

        upload_id = f"upl_{uuid.uuid4().hex[:16]}"
        try:
            execute_insert(
                """
                INSERT INTO "Upload"
                    (id, "orgId", "uploadedById", filename, "s3Key",
                     "bankName", "accountType", "accountId",
                     "statementMonth", "fileSizeBytes", status, "customerId", "createdAt")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    upload_id, org_id, uploaded_by_id, filename, key,
                    "PENDING", "PENDING", "",
                    statement_month, len(file_bytes),
                    UploadStatusEnum.UPLOADED.value, customer_id, datetime.utcnow(),
                ),
            )
        except Exception:
            pass

        results.append({
            "upload_id": upload_id,
            "filename": filename,
            "s3_key": key,
            "size": len(file_bytes),
        })

    return {"uploads": results}


@router.post("/upload-complete", response_model=UploadResponse)
async def register_upload(req: UploadCompleteRequest):
    """Called by frontend after upload completes — registers in DB."""
    upload_id = f"upl_{uuid.uuid4().hex[:16]}"

    row = execute_insert(
        """
        INSERT INTO "Upload"
            (id, "orgId", "uploadedById", filename, "s3Key", "bankName",
             "accountType", "accountId", "statementMonth", "fileSizeBytes",
             status, "createdAt")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, filename, "s3Key", "bankName", "accountType",
                  "accountId", "statementMonth", status, "createdAt"
        """,
        (
            upload_id, req.org_id, req.uploaded_by_id, req.filename,
            req.s3_key, req.bank_name, req.account_type, req.account_id,
            req.statement_month, req.file_size_bytes,
            UploadStatusEnum.UPLOADED.value, datetime.utcnow(),
        ),
    )

    return UploadResponse(
        id=upload_id,
        filename=row["filename"],
        s3_key=row["s3Key"],
        bank_name=row["bankName"],
        account_type=row["accountType"],
        account_id=row["accountId"],
        statement_month=row["statementMonth"],
        status=UploadStatusEnum(row["status"]),
        created_at=row["createdAt"],
    )


@router.get("/download/{file_key:path}")
async def download_file_by_key(file_key: str):
    """Serve a file from local storage."""
    local_path = storage.get_local_path(file_key)
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_key}")
    return FileResponse(local_path, filename=os.path.basename(local_path))
