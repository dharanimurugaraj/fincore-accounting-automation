"""
User Management API
Enables Super Admins and Admins to view users and assign internal platform roles.
"""

from typing import Annotated
from fastapi import APIRouter, HTTPException, Body
from app.core.database import execute_query
from app.api.deps import AdminUser

router = APIRouter()

@router.get("")
async def list_users(user: AdminUser):
    """
    List users on the platform.
    Super Admins (0) see all users globally.
    Admins (1) see users exactly in their organization.
    """
    current_role = user.get("role_id", 2)
    org_id = user["org_id"]

    query = """
        SELECT u.id, u.email, u.name, u."lastLogin", u."createdAt", u."roleId", r.name as role_name
        FROM "User" u
        LEFT JOIN "Role" r ON u."roleId" = r.id
        WHERE 1=1
    """
    params = []

    if current_role == 1:
        query += ' AND u."orgId" = %s'
        params.append(org_id)

    query += ' ORDER BY u."createdAt" DESC'
    rows = execute_query(query, tuple(params))

    # Strip purely internal logic safely
    users = []
    for r in rows:
        users.append({
            "id": r["id"],
            "email": r["email"],
            "name": r["name"],
            "role_id": r["roleId"],
            "role_name": r["role_name"],
            "last_login": r["lastLogin"].isoformat() if r["lastLogin"] else None,
            "created_at": r["createdAt"].isoformat() if r["createdAt"] else None,
        })

    return {"users": users}

@router.patch("/{target_user_id}/role")
async def update_user_role(
    target_user_id: str,
    user: AdminUser,
    role_id: int = Body(..., embed=True)
):
    """
    Change a user's role.
    Super Admin (0) can assign any role.
    Admin (1) can only assign roles > 1, to users strictly in their org.
    """
    current_role = user.get("role_id", 2)
    org_id = user["org_id"]

    # 1. Fetch User Target
    target = execute_query('SELECT "orgId", "roleId" FROM "User" WHERE id = %s', (target_user_id,))
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
        
    target_org = target[0]["orgId"]
    target_curr_role = target[0]["roleId"]

    # 2. Check Permissions
    if current_role == 1:
        # Admins can only touch their own org
        if target_org != org_id:
            raise HTTPException(status_code=403, detail="Cannot edit users outside your organization")
        # Admins cannot edit other Admins or Super Admins
        if target_curr_role <= 1:
            raise HTTPException(status_code=403, detail="Admins cannot override peer or senior administrator roles")
        # Admins cannot promote someone to Admin or Super Admin
        if role_id <= 1:
            raise HTTPException(status_code=403, detail="Admins cannot promote users to Administrator tiers")

    # 3. Check if target Role exists
    role_check = execute_query('SELECT id FROM "Role" WHERE id = %s', (role_id,))
    if not role_check:
        raise HTTPException(status_code=400, detail="Invalid role ID provided")

    # 4. Perform Update
    execute_query('UPDATE "User" SET "roleId" = %s WHERE id = %s', (role_id, target_user_id))
    
    return {"status": "success", "message": "Role updated"}
