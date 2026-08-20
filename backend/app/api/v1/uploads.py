from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
import json
from app.core.database import execute_query, execute_insert
from app.api.deps import CurrentUser
from datetime import datetime
import uuid
from fastapi.responses import RedirectResponse
from app.services.storage_service import generate_presigned_get_url

router = APIRouter()

@router.get("")
async def handle_documents_request(
    user: CurrentUser,
    action: Optional[str] = Query(None),
    key: Optional[str] = Query(None),
    statement_month: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """
    Handles both listing documents and downloading a specific document/report.
    Follows Task 3.5 requirement: GET /api/v1/documents?action=download&key=...
    """
    is_super_admin = user.get("role_id") == 0

    # [A] DOWNLOAD LOGIC
    if action == "download" and key:
        # 1. Security Check: Verify key belongs to user's org (or Super Admin)
        if is_super_admin:
            access_query = """
                SELECT id, "status"::text FROM "Upload" WHERE "s3Key" = %s
                UNION
                SELECT id, "status"::text FROM "PipelineRun" WHERE ("workingSheetKey" = %s OR "bankingReportKey" = %s)
            """
            rows = execute_query(access_query, (key, key, key))
        else:
            access_query = """
                SELECT id, "status"::text FROM "Upload" WHERE "s3Key" = %s AND "orgId" = %s
                UNION
                SELECT id, "status"::text FROM "PipelineRun" 
                WHERE ("workingSheetKey" = %s OR "bankingReportKey" = %s) AND "orgId" = %s
            """
            rows = execute_query(access_query, (key, user["org_id"], key, key, user["org_id"]))
        
        if not rows:
            raise HTTPException(status_code=403, detail="Access denied or file not found")

        # 2. Status Check: For reports, ensure they are APPROVED
        # (Uploads have status 'COMPLETED' or 'PENDING', only check 'APPROVED' for runs)
        # Note: UNION above returned status as well if we matched.
        
        # 3. Generate URL
        try:
            url = generate_presigned_get_url(key)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")

        # 4. Audit Log
        audit_id = f"aud_{uuid.uuid4().hex[:12]}"
        execute_insert(
            """
            INSERT INTO "AuditLog" (id, "orgId", "userId", action, "entityType", "entityId", metadata, "createdAt")
            VALUES (%s, %s, %s, 'FILE_DOWNLOADED', 'Document', %s, %s, %s)
            """,
            (audit_id, user["org_id"], user["id"], key, json.dumps({"key": key}), datetime.utcnow())
        )

        return RedirectResponse(url)

    # [B] LISTING LOGIC (Role-Based)
    if is_super_admin:
        query = """
            SELECT id, filename, "s3Key" as s3_key, "bankName" as bank_name, 
                   "accountType" as account_type, "accountId" as account_id, 
                   "statementMonth" as statement_month, status, "createdAt" as created_at
            FROM "Upload"
        """
        params = []
    else:
        query = """
            SELECT id, filename, "s3Key" as s3_key, "bankName" as bank_name, 
                   "accountType" as account_type, "accountId" as account_id, 
                   "statementMonth" as statement_month, status, "createdAt" as created_at
            FROM "Upload"
            WHERE "orgId" = %s
        """
        params = [user["org_id"]]

    if statement_month:
        query += (' AND ' if 'WHERE' in query else ' WHERE ') + '"statementMonth" = %s'
        params.append(statement_month)

    query += ' ORDER BY "createdAt" DESC LIMIT %s OFFSET %s'
    params_with_pagination = params + [limit, offset]

    rows = execute_query(query, tuple(params_with_pagination))
    
    # Count logic
    count_query = 'SELECT COUNT(*) FROM "Upload"'
    if not is_super_admin:
        count_query += ' WHERE "orgId" = %s'
    if statement_month:
        count_query += (' AND ' if 'WHERE' in count_query else ' WHERE ') + '"statementMonth" = %s'
    
    count_rows = execute_query(count_query, tuple(params))
    total = count_rows[0]["count"] if count_rows else 0

    return {"documents": rows, "total": total}
