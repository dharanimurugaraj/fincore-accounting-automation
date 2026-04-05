"""
Admin API for Role Management.
Allows Super Admins to dynamically create and manage roles with specific UI permissions.
"""

from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from app.core.database import execute_query, execute_insert
from app.api.deps import SuperAdminUser, AdminUser

router = APIRouter()

@router.get("")
async def get_all_roles(user: AdminUser):
    """List all available roles (Super Admin + Admins can view)."""
    rows = execute_query('SELECT id, name, description, "allowedPages" FROM "Role" ORDER BY id ASC')
    return {"roles": rows}

@router.post("")
async def create_or_update_role(
    req: dict, # { name, description, allowedPages }
    user: SuperAdminUser
):
    """
    Create a new dynamic role or update an existing one. (Super Admin strictly)
    `allowedPages` is an array of strings e.g. ["Dashboard", "Upload"].
    """
    name = req.get("name")
    description = req.get("description", "")
    allowed_pages = req.get("allowedPages", ["*"]) # Default fully permissive if not sent

    if not name:
        raise HTTPException(status_code=400, detail="Role name is required")

    # Clean the pages, let Postgres default it correctly
    if "*" in allowed_pages:
        allowed_pages = ["*"]
        
    try:
        # Check if role exists
        existing = execute_query('SELECT id FROM "Role" WHERE name = %s', (name.upper(),))
        
        if existing:
            role_id = existing[0]["id"]
            # Avoid editing system base roles accidentally through this naive endpoint 
            if role_id in [0, 1]:
                raise HTTPException(status_code=403, detail="System base roles cannot be modified dynamically.")
                
            execute_query(
                'UPDATE "Role" SET description = %s, "allowedPages" = %s WHERE id = %s',
                (description, allowed_pages, role_id)
            )
            return {"status": "ok", "action": "updated", "id": role_id}
            
        else:
            execute_insert(
                'INSERT INTO "Role" (name, description, "allowedPages") VALUES (%s, %s, %s)',
                (name.upper(), description, allowed_pages)
            )
            return {"status": "ok", "action": "created"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
