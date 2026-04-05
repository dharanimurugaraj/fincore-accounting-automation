"""
GET /activity       — AI usage log per user. Scoped by numeric role ID (0, 1, 2+).
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.core.database import execute_query
from app.api.deps import CurrentUser

router = APIRouter()

@router.get("")
async def list_ai_usage(
    user: CurrentUser,
    user_id: Optional[str] = Query(None),
    role_id_filter: Optional[int] = Query(None),
    model: Optional[str] = Query(None),
    time_filter: Optional[str] = Query(None), # 1d, 7d, 30d
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """List AI usage logs with numeric RBAC access controls."""
    org_id = user["org_id"]
    current_role = user.get("role_id", 2)
    current_uid = user["id"]

    query = """
        SELECT al.id, al."userId", al."userEmail", al.model,
               al."tokensIn", al."tokensOut", al."costUsd",
               al.action, al."sessionId", al."createdAt",
               u."roleId", r.name as role_name
        FROM "AIUsageLog" al
        LEFT JOIN "User" u ON al."userId" = u.id
        LEFT JOIN "Role" r ON u."roleId" = r.id
        WHERE 1=1
    """
    params: list = []

    # 1. Access Scoping
    if current_role == 0:
        # Super Admin sees everything across the platform (or within an org if we prefer)
        # We will show all orgs for Super Admin, but filter if user_id etc provided.
        pass
    elif current_role == 1:
        # Admin sees everyone in their org
        query += ' AND al."orgId" = %s'
        params.append(org_id)
    else:
        # Analyst / Viewer sees only their own
        query += ' AND al."userId" = %s'
        params.append(current_uid)

    # 2. Add requested filters
    # If the user is Role 0/1 and wants to filter by a specific user:
    if current_role <= 1 and user_id:
        query += ' AND al."userId" = %s'
        params.append(user_id)

    # If the user is Role 0/1 and wants to filter by a specific role group:
    if current_role <= 1 and role_id_filter is not None:
        query += ' AND u."roleId" = %s'
        params.append(role_id_filter)

    if model:
        query += " AND al.model = %s"
        params.append(model)
        
    if time_filter == "1d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '1 day'"
    elif time_filter == "7d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '7 days'"
    elif time_filter == "30d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '30 days'"

    # Pagination & Execution
    from_idx = query.upper().find("FROM")
    count_q = "SELECT COUNT(*) \n        " + query[from_idx:]

    query += ' ORDER BY al."createdAt" DESC LIMIT %s OFFSET %s'
    
    rows = execute_query(query, tuple(params + [limit, offset]))
    count_rows = execute_query(count_q, tuple(params))
    total = count_rows[0]["count"] if count_rows else 0

    entries = [
        {
            "id": r["id"],
            "user_id": r["userId"],
            "user_email": r["userEmail"],
            "user_role_id": r["roleId"],
            "user_role_name": r["role_name"] or "Unknown",
            "model": r["model"],
            "tokens_in": r["tokensIn"] or 0,
            "tokens_out": r["tokensOut"] or 0,
            "cost_usd": float(r["costUsd"]) if r["costUsd"] else 0.0,
            "action": r["action"],
            "session_id": r["sessionId"],
            "created_at": r["createdAt"].isoformat() if r["createdAt"] else None,
        }
        for r in rows
    ]

    # Aggregated Summary (Only if they are Role 0 or 1. Role 2+ gets basic total summing from entries to save query time if complex caching isn't ready)
    summary = {
        "total_queries": total,
        "total_tokens_in": sum(e["tokens_in"] for e in entries),
        "total_tokens_out": sum(e["tokens_out"] for e in entries),
        "total_cost_usd": round(sum(e["cost_usd"] for e in entries), 6),
    }

    return {"entries": entries, "summary": summary, "total": total}
