"""
GET /audit-logs         — immutable audit log. Scoped by numeric role ID (0, 1, 2+).
GET /audit-logs/export  — download audit log as CSV
"""

import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.database import execute_query
from app.api.deps import CurrentUser

router = APIRouter()

@router.get("")
async def list_audit_log(
    user: CurrentUser,
    user_id: Optional[str] = Query(None),
    role_id_filter: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    time_filter: Optional[str] = Query(None), # 1d, 7d, 30d
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """Return audit log entries with numeric RBAC access controls."""
    org_id = user["org_id"]
    current_role = user.get("role_id", 2)
    current_uid = user["id"]

    query = """
        SELECT al.id, al."orgId", al."userId", al.action,
               al."entityType", al."entityId", al.metadata, al."createdAt",
               u.email as user_email, u."roleId", r.name as role_name
        FROM "AuditLog" al
        LEFT JOIN "User" u ON u.id = al."userId"
        LEFT JOIN "Role" r ON u."roleId" = r.id
        WHERE 1=1
    """
    params: list = []

    # 1. Access Scoping
    if current_role == 0:
        # Super Admin sees everything across the platform
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

    if action:
        query += " AND al.action = %s"
        params.append(action.upper())
        
    if time_filter == "1d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '1 day'"
    elif time_filter == "7d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '7 days'"
    elif time_filter == "30d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '30 days'"

    from_idx = query.upper().find("FROM")
    count_q = "SELECT COUNT(*) \n        " + query[from_idx:]

    query += ' ORDER BY al."createdAt" DESC LIMIT %s OFFSET %s'
    rows = execute_query(query, tuple(params + [limit, offset]))
    count_rows = execute_query(count_q, tuple(params))
    total = count_rows[0]["count"] if count_rows else 0

    entries = [
        {
            "id": r["id"],
            "org_id": r["orgId"],
            "user_id": r["userId"],
            "user_email": r["user_email"] or "System",
            "user_role_id": r["roleId"],
            "user_role_name": r["role_name"] or "Unknown",
            "action": r["action"],
            "entity_type": r["entityType"],
            "entity_id": r["entityId"],
            "metadata": r["metadata"],
            "created_at": r["createdAt"].isoformat() if r["createdAt"] else None,
        }
        for r in rows
    ]

    return {"entries": entries, "total": total}

@router.get("/export")
async def export_audit_log(
    user: CurrentUser,
    time_filter: Optional[str] = Query(None),
):
    """Download full audit log as CSV. Admins (0, 1) only."""
    current_role = user.get("role_id", 2)
    if current_role > 1:
        raise HTTPException(status_code=403, detail="Admin access required")

    org_id = user["org_id"]
    query = """
        SELECT al.id, al."userId", u.email as user_email, al.action,
               al."entityType", al."entityId", al."createdAt", r.name as role_name
        FROM "AuditLog" al
        LEFT JOIN "User" u ON u.id = al."userId"
        LEFT JOIN "Role" r ON u."roleId" = r.id
        WHERE 1=1
    """
    params: list = []

    if current_role == 1:
        query += ' AND al."orgId" = %s'
        params.append(org_id)

    if time_filter == "1d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '1 day'"
    elif time_filter == "7d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '7 days'"
    elif time_filter == "30d":
        query += " AND al.\"createdAt\" >= NOW() - INTERVAL '30 days'"

    query += ' ORDER BY al."createdAt" DESC LIMIT 5000'
    rows = execute_query(query, tuple(params))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "User ID", "User Email", "Role", "Action", "Entity Type", "Entity ID", "Timestamp"])
    for r in rows:
        writer.writerow([
            r["id"], r["userId"], r["user_email"], r["role_name"], r["action"],
            r["entityType"], r["entityId"],
            r["createdAt"].isoformat() if r["createdAt"] else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_log_{date.today()}.csv"},
    )
