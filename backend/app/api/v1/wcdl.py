"""
API Router for WCDL (Working Capital Demand Loan) Tracking.
"""

from typing import Optional
from fastapi import APIRouter, Query
from app.core.database import execute_query
from app.api.deps import CurrentUser

router = APIRouter()

@router.get("")
async def get_wcdl_tracker(
    user: CurrentUser,
    month: Optional[str] = Query(None),
):
    """List all WCDL loans for the organisation, filtered by month if provided."""
    org_id = user["org_id"]
    
    query = 'SELECT * FROM "WCDLLoan" WHERE "orgId" = %s'
    params: list = [org_id]
    
    # Optional filtering by month if we decide to track specific snapshots
    # For now, return all active/historical ones.
    
    rows = execute_query(query, tuple(params))
    
    return {
        "loans": [
            {
                "id": r["id"],
                "loanNumber": r["loanNumber"],
                "bankName": r["bankName"],
                "principal": float(r["principalAmount"]),
                "roi": float(r["roi"]),
                "startDate": str(r["startDate"]),
                "maturityDate": str(r["maturityDate"]),
                "prepaymentDate": str(r["prepaymentDate"]) if r["prepaymentDate"] else None,
                "status": r["status"]
            }
            for r in rows
        ]
    }
