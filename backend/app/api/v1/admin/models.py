"""
Admin API for OpenRouter Model Management.
Fetches live models from OpenRouter and allows assigning them to agents.
"""

import os
import requests
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from app.core.database import execute_query, execute_insert
from app.api.deps import AdminUser

router = APIRouter()

@router.get("/external")
async def get_external_models():
    """Fetch live models from OpenRouter API."""
    try:
        response = requests.get("https://openrouter.ai/api/v1/models")
        if response.ok:
            return response.json()
        return {"data": []}
    except Exception as e:
        print(f"Error fetching OpenRouter models: {e}")
        return {"data": []}

@router.get("/config")
async def get_agent_configs(user: AdminUser):
    """List agent to model assignments for the org."""
    rows = execute_query(
        'SELECT * FROM "AgentConfig" WHERE "orgId" = %s',
        (user["org_id"],)
    )
    return {"configs": rows}

@router.post("/config")
async def update_agent_config(
    req: dict, # { agentId, primaryModel, fallbackModels, maxRetries, temperature }
    user: AdminUser
):
    """Assign models to an OCR agent."""
    org_id = user["org_id"]
    agent_id = req["agent_id"]
    primary = req["primary_model"]
    fallbacks = req.get("fallback_models", [])
    max_retries = req.get("max_retries", 3)
    temp = req.get("temperature", 0.0)

    import uuid
    id = f"agcfg-{uuid.uuid4().hex[:8]}"

    execute_query(
        """
        INSERT INTO "AgentConfig" 
            (id, "orgId", "agentId", "primaryModel", "fallbackModels", "maxRetries", "temperature", "updatedAt")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT ("orgId", "agentId") DO UPDATE SET
            "primaryModel" = EXCLUDED."primaryModel",
            "fallbackModels" = EXCLUDED."fallbackModels",
            "maxRetries" = EXCLUDED."maxRetries",
            "temperature" = EXCLUDED."temperature",
            "updatedAt" = EXCLUDED."updatedAt"
        """,
        (id, org_id, agent_id, primary, fallbacks, max_retries, temp, "now()")
    )

    return {"status": "ok"}
