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
    user_email: Optional[str] = Query(None),
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
    if current_role <= 1 and user_id:
        query += ' AND al."userId" = %s'
        params.append(user_id)

    if current_role <= 1 and role_id_filter is not None:
        query += ' AND u."roleId" = %s'
        params.append(role_id_filter)

    if model:
        query += " AND al.model = %s"
        params.append(model)
        
    if user_email:
        query += ' AND al."userEmail" ILIKE %s'
        params.append(f"%{user_email}%")

    if time_filter == "1d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '1 day'"
    elif time_filter == "7d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '7 days'"
    elif time_filter == "30d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '30 days'"

    # Aggregated Summary (Run this BEFORE pagination)
    summary_q = """
        SELECT COUNT(*) as total_queries,
               COALESCE(SUM("tokensIn"), 0) as total_tokens_in,
               COALESCE(SUM("tokensOut"), 0) as total_tokens_out,
               COALESCE(SUM("costUsd"), 0) as total_cost_usd
        FROM "AIUsageLog" al
        WHERE 1=1
    """
    s_params = []
    
    # Replicate main filter logic for summary
    if current_role == 1:
        summary_q += ' AND al."orgId" = %s'
        s_params.append(org_id)
    elif current_role > 1:
        summary_q += ' AND al."userId" = %s'
        s_params.append(current_uid)
        
    if model:
        summary_q += " AND al.model = %s"
        s_params.append(model)
        
    if user_email:
        summary_q += ' AND al."userEmail" ILIKE %s'
        s_params.append(f"%{user_email}%")

    if time_filter == "1d":
        summary_q += " AND al.\"createdAt\" >= NOW() - INTERVAL '1 day'"
    elif time_filter == "7d":
        summary_q += " AND al.\"createdAt\" >= NOW() - INTERVAL '7 days'"
    elif time_filter == "30d":
        summary_q += " AND al.\"createdAt\" >= NOW() - INTERVAL '30 days'"

    import asyncio
    summary_rows = await asyncio.to_thread(execute_query, summary_q, tuple(s_params))
    s = summary_rows[0] if summary_rows else {}
    summary = {
        "total_queries": s.get("total_queries") or 0,
        "total_tokens_in": int(s.get("total_tokens_in") or 0),
        "total_tokens_out": int(s.get("total_tokens_out") or 0),
        "total_cost_usd": round(float(s.get("total_cost_usd") or 0.0), 6)
    }

    # Pagination & Execution
    query += ' ORDER BY al."createdAt" DESC LIMIT %s OFFSET %s'
    rows = await asyncio.to_thread(execute_query, query, tuple(params + [limit, offset]))

    entries = []
    from datetime import timedelta
    for r in rows:
        dt = r["createdAt"]
        ist_time = dt + timedelta(hours=5, minutes=30)
        iso_ts = ist_time.strftime("%d %b, %I:%M %p").replace("AM", "am").replace("PM", "pm")
        
        entries.append({
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
            "session_id": r.get("sessionId"),
            "created_at": iso_ts,
        })

    return {"entries": entries, "summary": summary, "total": summary["total_queries"]}
