"""
Backend Settings API
Handles Personal Preferences, Organization Profile, and Global Platform Constants
"""

from typing import Annotated
from fastapi import APIRouter, HTTPException, Body, Response
from app.core.database import execute_query
from app.api.deps import CurrentUser, AdminUser, SuperAdminUser

router = APIRouter()

# ------------------------------------------------------------------------------
# 1. PERSONAL PREFERENCES (All Roles)
# ------------------------------------------------------------------------------
@router.get("/profile")
async def get_my_profile(user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "private, max-age=60"
    rows = execute_query(
        'SELECT email, name, title, phone, theme, timezone, "dateFormat", "emailAlerts" FROM "User" WHERE id = %s',
        (user["id"],)
    )
    return {"profile": rows[0] if rows else {}}

@router.patch("/profile")
async def update_my_profile(user: CurrentUser, payload: dict = Body(...)):
    allowed_keys = ["name", "title", "phone", "theme", "timezone", "dateFormat", "emailAlerts"]
    updates = []
    params = []
    
    for k, v in payload.items():
        if k in allowed_keys:
            updates.append(f'"{k}" = %s')
            params.append(v)
            
    if updates:
        params.append(user["id"])
        query = f'UPDATE "User" SET {", ".join(updates)} WHERE id = %s'
        execute_query(query, tuple(params))
        
    return {"status": "ok", "message": "Profile updated"}

# ------------------------------------------------------------------------------
# 2. ORGANIZATION SETTINGS (Admins & Super Admins)
# ------------------------------------------------------------------------------
@router.get("/organization")
async def get_organization(user: AdminUser, response: Response):
    response.headers["Cache-Control"] = "private, max-age=300"
    rows = execute_query(
        'SELECT id, name, "legalName", address, "logoUrl", departments FROM "Organisation" WHERE id = %s',
        (user["org_id"],)
    )
    return {"organization": rows[0] if rows else {}}

@router.patch("/organization")
async def update_organization(user: AdminUser, payload: dict = Body(...)):
    allowed_keys = ["name", "legalName", "address", "logoUrl"]
    updates = []
    params = []
    
    for k, v in payload.items():
        if k in allowed_keys:
            updates.append(f'"{k}" = %s')
            params.append(v)
            
    if updates:
        params.append(user["org_id"])
        query = f'UPDATE "Organisation" SET {", ".join(updates)} WHERE id = %s'
        execute_query(query, tuple(params))
        
    return {"status": "ok", "message": "Organization updated"}

# ------------------------------------------------------------------------------
# 3. GLOBAL PLATFORM (Super Admins Only)
# ------------------------------------------------------------------------------
@router.get("/platform")
async def get_platform_config(user: SuperAdminUser, response: Response):
    response.headers["Cache-Control"] = "private, max-age=300"
    try:
        rows = execute_query('SELECT key, value FROM "GlobalConfig"')
        config = {r["key"]: r["value"] for r in rows}
        return {"platform": config}
    except Exception as e:
        # Gracefully handle missing table or other query errors in Dev
        print(f"DEBUG: settings/platform retrieval skipped: {e}")
        return {"platform": {}, "warning": "GlobalConfig table not found or inaccessible"}

@router.get("/credits")
async def get_credits(user: SuperAdminUser):
    """Fetch live OpenRouter credit balance for Super Admins."""
    import httpx
    from app.core.config import settings
    
    url = "https://openrouter.ai/api/v1/credits"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                return response.json()
            return {"error": f"OpenRouter API error: {response.status_code}", "data": None}
    except Exception as e:
        return {"error": str(e), "data": None}

@router.patch("/platform")
async def update_platform_config(user: SuperAdminUser, payload: dict = Body(...)):
    for key, value in payload.items():
        # Upsert global parameters natively using conflict resolution
        execute_query("""
            INSERT INTO "GlobalConfig" (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "updatedAt" = CURRENT_TIMESTAMP
        """, (key, value))
        
    return {"status": "ok", "message": "Platform Config Synced"}
