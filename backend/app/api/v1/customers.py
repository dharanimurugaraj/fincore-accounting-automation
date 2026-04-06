import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerSummary
)
from app.core.database import execute_query, execute_insert
from app.api.deps import CurrentUser

router = APIRouter()

def generate_custom_id():
    """Generate a readable ID like CUST-1001 based on count."""
    count_query = 'SELECT COUNT(*) as count FROM "Customer"'
    res = execute_query(count_query)
    count = res[0].get("count", 0) if res else 0
    return f"CUST-{1001 + count}"

@router.get("", response_model=List[CustomerSummary])
async def list_customers(
    user: CurrentUser,
    status: Optional[str] = Query(None),
    risk: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
):
    """List all customers for the organization with summary stats."""
    query = """
        SELECT 
            c.id, c."customId", c."companyName", c.industry, c.status, c.risk, c.tags,
            (SELECT COUNT(*)::int FROM "Upload" u WHERE u."customerId" = c.id) as "documentCount",
            (SELECT COUNT(*)::int FROM "WCDLLoan" w WHERE w."customerId" = c.id) as "wcdlCount",
            (SELECT MAX("createdAt") FROM "Upload" u WHERE u."customerId" = c.id) as "lastActivity"
        FROM "Customer" c
        WHERE c."orgId" = %s
    """
    params = [user["org_id"]]

    if status:
        query += ' AND c.status = %s'
        params.append(status)
    if risk:
        query += ' AND c.risk = %s'
        params.append(risk)
    if industry:
        query += ' AND c.industry = %s'
        params.append(industry)

    query += ' ORDER BY c."createdAt" DESC'
    
    rows = execute_query(query, tuple(params))
    
    try:
        return [
            CustomerSummary(
                id=str(row["id"]),
                customId=str(row["customId"]),
                companyName=str(row["companyName"]),
                industry=row["industry"] if row["industry"] else None,
                status=str(row["status"]),
                risk=str(row["risk"]),
                tags=list(row["tags"]) if isinstance(row["tags"], (list, tuple)) else [],
                documentCount=int(row["documentCount"] or 0),
                wcdlCount=int(row["wcdlCount"] or 0),
                lastActivity=row["lastActivity"]
            )
            for row in rows
        ]
    except Exception as e:
        print(f"Customer List Validation Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Data Transformation Failed: {str(e)}")

@router.post("", response_model=CustomerResponse)
async def create_customer(user: CurrentUser, req: CustomerCreate):
    """Create a new customer profile."""
    cust_id = f"cust_{uuid.uuid4().hex[:16]}"
    custom_id = generate_custom_id()
    now = datetime.utcnow()

    row = execute_insert(
        """
        INSERT INTO "Customer"
            (id, "customId", "companyName", "contactName", pan, cin, email, 
             phone, industry, address, tags, status, risk, "orgId", "createdAt", "updatedAt")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            cust_id, custom_id, req.companyName, req.contactName, req.pan, req.cin,
            req.email, req.phone, req.industry, req.address, req.tags,
            req.status, req.risk, user["org_id"], now, now
        )
    )

    if not row:
        raise HTTPException(status_code=500, detail="Failed to create customer")
    
    return CustomerResponse(**row)

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(user: CurrentUser, customer_id: str):
    """Get detailed customer profile."""
    query = 'SELECT * FROM "Customer" WHERE id = %s AND "orgId" = %s'
    rows = execute_query(query, (customer_id, user["org_id"]))
    
    if not rows:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return CustomerResponse(**rows[0])

@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(user: CurrentUser, customer_id: str, req: CustomerUpdate):
    """Update customer fields."""
    update_data = req.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_data["updatedAt"] = datetime.utcnow()
    
    set_clause = ", ".join([f'"{k}" = %s' for k in update_data.keys()])
    query = f'UPDATE "Customer" SET {set_clause} WHERE id = %s AND "orgId" = %s RETURNING *'
    
    params = list(update_data.values()) + [customer_id, user["org_id"]]
    
    row = execute_insert(query, tuple(params))
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found or update failed")
    
    return CustomerResponse(**row)

@router.get("/{customer_id}/documents")
async def get_customer_documents(user: CurrentUser, customer_id: str):
    """Get all documents associated with a customer."""
    query = """
        SELECT id, filename, "s3Key", "bankName", "accountType", 
               "accountId", "statementMonth", status, "createdAt"
        FROM "Upload"
        WHERE "customerId" = %s AND "orgId" = %s
        ORDER BY "createdAt" DESC
    """
    rows = execute_query(query, (customer_id, user["org_id"]))
    return rows

@router.get("/{customer_id}/pipeline-runs")
async def get_customer_pipeline_runs(user: CurrentUser, customer_id: str):
    """Get all pipeline runs associated with a customer."""
    query = """
        SELECT id, "statementMonth", status, stage, "startedAt", "completedAt",
               "statementExcelKey", "workingSheetKey", "bankingReportKey"
        FROM "PipelineRun"
        WHERE "customerId" = %s AND "orgId" = %s
        ORDER BY "createdAt" DESC
    """
    rows = execute_query(query, (customer_id, user["org_id"]))
    return rows
