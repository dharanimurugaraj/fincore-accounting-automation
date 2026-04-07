from fastapi import APIRouter, Query
from typing import List, Optional
from app.core.database import execute_query
from app.api.deps import CurrentUser
from datetime import datetime

router = APIRouter()

@router.get("")
async def list_documents(
    user: CurrentUser,
    statement_month: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """List all uploaded documents for an organisation."""
    query = """
        SELECT id, filename, "s3Key" as s3_key, "bankName" as bank_name, 
               "accountType" as account_type, "accountId" as account_id, 
               "statementMonth" as statement_month, status, "createdAt" as created_at
        FROM "Upload"
        WHERE "orgId" = %s
    """
    params: list = [user["org_id"]]

    if statement_month:
        query += ' AND "statementMonth" = %s'
        params.append(statement_month)

    query += ' ORDER BY "createdAt" DESC LIMIT %s OFFSET %s'
    params_with_pagination = params + [limit, offset]

    rows = execute_query(query, tuple(params_with_pagination))
    
    # Simple count query
    count_query = 'SELECT COUNT(*) FROM "Upload" WHERE "orgId" = %s'
    if statement_month:
        count_query += ' AND "statementMonth" = %s'
    
    count_rows = execute_query(count_query, tuple(params))
    total = count_rows[0]["count"] if count_rows else 0

    return {"documents": rows, "total": total}
