"""
FastAPI app entry point.
"""

import sys
from pathlib import Path

# Ensure app package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1.router import api_v1_router
from app.services.s3_service import get_storage

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic — Resilient initialization for Vercel functions
    try:
        from app.core.security import _init_firebase
        _init_firebase()
    except Exception as e:
        print(f"CRITICAL: Firebase init failed: {e}")
    
    yield
    # No explicit pool shutdown needed for direct connections

app = FastAPI(
    title="FinCore API",
    description="AI-powered banking intelligence platform — backend service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for proxy-based communication
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... routes ...
app.include_router(api_v1_router, prefix="/api/v1")

# Static file serving for local storage (Safe for Vercel)
import os
storage_path = Path(settings.LOCAL_STORAGE_PATH)
try:
    if not storage_path.exists():
        storage_path.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"WARN: Could not create storage directory {storage_path}: {e}")

if storage_path.exists():
    app.mount("/files", StaticFiles(directory=str(storage_path)), name="local-files")
else:
    print(f"WARN: Skipping StaticFiles mount - {storage_path} does not exist.")



@app.get("/api/v1/health")
async def health():
    import firebase_admin
    import os
    from app.core.config import settings
    
    # Redacted list of keys for debugging
    fb_keys = [k for k in os.environ.keys() if "FIREBASE" in k]
    
    return {
        "status": "healthy",
        "firebase_initialized": bool(firebase_admin._apps),
        "fb_keys_found": fb_keys,
        "env_vercel": bool(os.getenv("VERCEL")),
        "fb_json_len": len(settings.FIREBASE_SERVICE_ACCOUNT_JSON) if settings.FIREBASE_SERVICE_ACCOUNT_JSON else 0
    }

@app.get("/")
async def root():
    return {
        "service": "FinCore API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
