"""
Admin API for Role Management.
Allows Super Admins to dynamically create and manage roles with specific UI permissions.
"""

from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from app.core.database import execute_query, execute_insert
from app.api.deps import SuperAdminUser, AdminUser

from app.services.audit_service import log_action

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
    `allowedPages` supports granular permissions e.g. ["Customers:read", "Dashboard:write"].
    """
    name = req.get("name")
    description = req.get("description", "")
    allowed_pages = req.get("allowedPages", ["*"]) # Default fully permissive if not sent

    if not name:
        raise HTTPException(status_code=400, detail="Role name is required")

    # Standardize naming
    role_name = name.upper().strip()
    
    # Internal Base Roles Protection
    protected_roles = ["SUPER_ADMIN", "ADMIN"]
    if role_name in protected_roles:
        raise HTTPException(status_code=403, detail=f"System base role {role_name} cannot be modified dynamically.")

    try:
        # Check if role exists
        existing = execute_query('SELECT id FROM "Role" WHERE name = %s', (role_name,))
        
        if existing:
            role_id = existing[0]["id"]
            
            execute_query(
                'UPDATE "Role" SET description = %s, "allowedPages" = %s WHERE id = %s',
                (description, allowed_pages, role_id)
            )
            
            log_action(user, "UPDATE_ROLE", "Role", str(role_id), 
                       {"name": role_name, "permissions": allowed_pages})
                       
            return {"status": "ok", "action": "updated", "id": role_id}
            
        else:
            execute_insert(
                'INSERT INTO "Role" (name, description, "allowedPages") VALUES (%s, %s, %s)',
                (role_name, description, allowed_pages)
            )
            
            log_action(user, "CREATE_ROLE", "Role", role_name, 
                       {"name": role_name, "permissions": allowed_pages})
                       
            return {"status": "ok", "action": "created"}
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

