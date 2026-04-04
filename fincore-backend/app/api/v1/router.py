"""
Mounts all v1 routes into a single APIRouter.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.pipeline import router as pipeline_router
from app.api.v1.reports import router as reports_router

api_v1_router = APIRouter()

# Health check — inline
@api_v1_router.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "1.0.0", "service": "fincore-api"}


api_v1_router.include_router(auth_router,     prefix="/auth",      tags=["Auth"])
api_v1_router.include_router(uploads_router,  prefix="/uploads",   tags=["Uploads"])
api_v1_router.include_router(pipeline_router, prefix="/pipeline",  tags=["Pipeline"])
api_v1_router.include_router(reports_router,  prefix="/reports",   tags=["Reports"])
