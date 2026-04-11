import httpx
from fastapi import APIRouter
from app.api.deps import AdminUser
from app.pipeline.ai_config import AI_MODELS

router = APIRouter()

# Simple Cache for OpenRouter models
_cached_models = []
_last_fetch = 0

@router.get("/external")
async def get_external_models():
    """Fetch live models from OpenRouter API WITH local model hub fallback."""
    global _cached_models, _last_fetch
    
    import time
    now = time.time()
    
    # Return cache if fresh (2 minutes)
    if _cached_models and (now - _last_fetch < 120):
        return {"data": _cached_models}

    # Start with local models
    all_models = []
    seen_ids = set()
    
    for provider, models in AI_MODELS.items():
        for m in models:
            m_id = f"{provider.lower()}/{m['name'].lower().replace(' ', '-')}"
            all_models.append({
                "id": m_id,
                "name": f"{provider}: {m['name']}",
                "context": m.get("context", 128000),
                "pricing": {
                    "prompt": m.get("input", 0),
                    "completion": m.get("output", 0)
                },
                "provider": provider,
                "is_local_hub": True
            })
            seen_ids.add(m_id)

    # Try fetching from OpenRouter with a short timeout
    try:
        async with httpx.AsyncClient() as client:
            # Short timeout to prevent backend hang
            response = await client.get("https://openrouter.ai/api/v1/models", timeout=2.5)
            if response.status_code == 200:
                external_data = response.json().get("data", [])
                for ext in external_data[:40]:
                    model_id = ext.get("id")
                    if model_id not in seen_ids:
                        all_models.append({
                            "id": model_id,
                            "name": ext.get("name"),
                            "context": ext.get("context_length"),
                            "pricing": ext.get("pricing"),
                            "provider": "OpenRouter",
                            "is_local_hub": False
                        })
                        seen_ids.add(model_id)
        
        # update cache only on success
        _cached_models = all_models
        _last_fetch = now
        
    except Exception as e:
        print(f"DEBUG: OpenRouter skip: {e}")
        # Always return local models at minimum
        if not _cached_models:
             _cached_models = all_models

    return {"data": _cached_models or all_models}

@router.get("/key-info")
async def get_key_info(user: AdminUser):
    """Fetch OpenRouter key usage and limits for credit management."""
    from app.core.config import settings
    import httpx
    
    url = "https://openrouter.ai/api/v1/auth/key"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"OpenRouter API error: {response.status_code}", "data": None}
    except Exception as e:
        return {"error": str(e), "data": None}

@router.get("/config")
async def get_agent_configs(user: AdminUser):
    """Placeholder for agent configurations."""
    return {"configs": []}
