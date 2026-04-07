from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.core.database import execute_query
from app.api.deps import CurrentUser

router = APIRouter()

@router.get("")
async def list_audit_logs(
    user: CurrentUser,
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    action: Optional[str] = Query(None),
    user_email: Optional[str] = Query(None),
):

    """
    List audit logs with RBAC filtering. Includes User Email and Role name.
    """
    # Security Gate: SuperAdmin (0), Admin (1) can see broader logs.
    # Analyst (2) can only see THEIR OWN logs.
    if user["role_id"] > 2:
        raise HTTPException(status_code=403, detail="Insufficient permissions to view audit logs")

    query = """
        SELECT 
            l.id, l.action, l."entityType" as entity_type, l."entityId" as entity_id, 
            l.metadata, l."createdAt" as created_at,
            u.id as user_id, u.email as user_email,
            r.id as user_role_id, r.name as user_role_name
        FROM "AuditLog" l
        LEFT JOIN "User" u ON l."userId" = u.id
        LEFT JOIN "Role" r ON u."roleId" = r.id
        WHERE 1=1
    """
    params = []

    # RBAC Filtering
    if user["role_id"] == 1:
        # Admin: Only their org
        query += ' AND l."orgId" = %s'
        params.append(user["org_id"])
    elif user["role_id"] == 2:
        # Analyst: ONLY their own logs
        query += ' AND l."userId" = %s'
        params.append(user["id"])
    
    if action:
        query += ' AND l.action = %s'
        params.append(action)


    query += ' ORDER BY l."createdAt" DESC LIMIT %s OFFSET %s'
    params.extend([limit, offset])

    rows = execute_query(query, tuple(params))
    
    entries = []
    for r in rows:
        entry = dict(r)
        if entry.get("created_at"):
            dt = entry["created_at"]
            # Force ISO format with 'Z' for UTC
            if hasattr(dt, 'strftime'):
                entry["created_at"] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        entries.append(entry)

    # Simple count for total
    count_query = """
        SELECT COUNT(*) 
        FROM "AuditLog" l 
        LEFT JOIN "User" u ON l."userId" = u.id 
        WHERE 1=1
    """
    count_params = []
    if user["role_id"] == 1:
        count_query += ' AND l."orgId" = %s'
        count_params.append(user["org_id"])
    elif user["role_id"] == 2:
        count_query += ' AND l."userId" = %s'
        count_params.append(user["id"])
    
    if action:
        count_query += ' AND l.action = %s'
        count_params.append(action)
    
    if user_email:
        count_query += ' AND u.email ILIKE %s'
        count_params.append(f"%{user_email}%")
    
    total_rows = execute_query(count_query, tuple(count_params))
    total = total_rows[0]["count"] if total_rows else 0

    return {
        "entries": entries,
        "total": total
    }




