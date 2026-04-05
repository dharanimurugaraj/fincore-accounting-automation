"""
Admin API for Formula Management.
Allows organization admins to configure live math expressions for interest and fees.
"""

import uuid
import json
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from app.core.database import execute_query, execute_insert
from app.api.deps import AdminUser

router = APIRouter()

@router.get("")
async def get_formulas(user: AdminUser):
    """List all formulas for the organisation."""
    rows = execute_query(
        'SELECT * FROM "FormulaConfiguration" WHERE "orgId" = %s AND "isActive" = TRUE',
        (user["org_id"],)
    )
    return {"formulas": rows}

@router.get("/{name}/history")
async def get_formula_history(name: str, user: AdminUser):
    """List version history for a specific formula."""
    rows = execute_query(
        'SELECT * FROM "FormulaConfiguration" WHERE "orgId" = %s AND "name" = %s ORDER BY version DESC',
        (user["org_id"], name)
    )
    return {"history": rows}

@router.post("")
async def update_formula(
    req: dict, # { name, expression, parameters, description }
    user: AdminUser
):
    """Create a new version of a formula."""
    org_id = user["org_id"]
    name = req["name"]
    expr = req["expression"]
    params = req.get("parameters", "{}")
    desc = req.get("description", "")

    # Get latest version
    rows = execute_query(
        'SELECT MAX(version) as last_v FROM "FormulaConfiguration" WHERE "orgId" = %s AND "name" = %s',
        (org_id, name)
    )
    v = (rows[0]["last_v"] or 0) + 1

    # Deactive old
    execute_query(
        'UPDATE "FormulaConfiguration" SET "isActive" = FALSE WHERE "orgId" = %s AND "name" = %s',
        (org_id, name)
    )

    # Insert new
    id = f"frm-{uuid.uuid4().hex[:8]}"
    execute_insert(
        """
        INSERT INTO "FormulaConfiguration" 
            (id, "orgId", name, expression, parameters, description, version, "isActive", "updatedAt")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (id, org_id, name, expr, json.dumps(params), desc, v, True, datetime.utcnow())
    )

    return {"status": "ok", "version": v}
