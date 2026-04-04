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

app = FastAPI(
    title="FinCore API",
    description="AI-powered banking intelligence platform — backend service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all v1 routes under /api/v1
app.include_router(api_v1_router, prefix="/api/v1")

# Static file serving for local storage
storage = get_storage()
storage_path = Path(settings.LOCAL_STORAGE_PATH)
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(storage_path)), name="local-files")


@app.get("/")
async def root():
    return {
        "service": "FinCore API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
