"""
API Router for Forex Transaction Tracking and Dispute Analysis.
"""

from typing import Optional
from fastapi import APIRouter, Query
from app.core.database import execute_query
from app.api.deps import CurrentUser

router = APIRouter()

@router.get("")
async def get_forex_register(
    user: CurrentUser,
    month: Optional[str] = Query(None),
):
    """List all forex transactions for the organisation, with overcharge detection."""
    org_id = user["org_id"]
    
    query = 'SELECT * FROM "ForexTransaction" WHERE "orgId" = %s'
    params: list = [org_id]
    
    if month:
        query += ' AND "statementMonth" = %s'
        params.append(month)
    
    query += ' ORDER BY "valueDate" DESC'
    
    rows = execute_query(query, tuple(params))
    
    return {
        "transactions": [
            {
                "id": r["id"],
                "boeDate": str(r["boeDate"]) if r["boeDate"] else None,
                "valueDate": str(r["valueDate"]),
                "drawerName": r["drawerName"],
                "billReference": r["billReference"],
                "currency": r["currency"],
                "fcAmount": float(r["fcAmount"]),
                "bankRate": float(r["bankRate"]),
                "totalAmtINR": float(r["totalAmtINR"]),
                "excessVsAvg": float(r["excessVsAvg"])
            }
            for r in rows
        ]
    }
