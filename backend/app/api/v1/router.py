"""
Mounts all v1 routes into a single APIRouter.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.pipeline import router as pipeline_router
from app.api.v1.reports import router as reports_router
from app.api.v1.wcdl import router as wcdl_router
from app.api.v1.forex import router as forex_router
from app.api.v1.admin.formulas import router as formulas_router
from app.api.v1.admin.models import router as models_router
from app.api.v1.admin.roles import router as roles_router
from app.api.v1.admin.users import router as users_router
from app.api.v1.settings import router as settings_router
from app.api.v1.activity import router as activity_router
from app.api.v1.audit import router as audit_router
from app.api.v1.customers import router as customers_router

api_v1_router = APIRouter()

# Health check — inline (debug mode)
@api_v1_router.get("/health", tags=["Health"])
async def health_check():
    import firebase_admin, os
    from app.core.config import settings
    fb_keys = [k for k in os.environ.keys() if "FIREBASE" in k]
    return {
        "status": "ok",
        "firebase_initialized": bool(firebase_admin._apps),
        "fb_keys_found": fb_keys,
        "fb_json_len": len(settings.FIREBASE_SERVICE_ACCOUNT_JSON) if settings.FIREBASE_SERVICE_ACCOUNT_JSON else 0,
        "env_vercel": bool(os.getenv("VERCEL")),
    }


api_v1_router.include_router(auth_router,     prefix="/auth",      tags=["Auth"])
api_v1_router.include_router(uploads_router,  prefix="/uploads",   tags=["Uploads"])
api_v1_router.include_router(uploads_router,  prefix="/documents",   tags=["Documents"])
api_v1_router.include_router(pipeline_router, prefix="/pipeline",  tags=["Pipeline"])
api_v1_router.include_router(reports_router,  prefix="/reports",   tags=["Reports"])
api_v1_router.include_router(wcdl_router,     prefix="/wcdl",      tags=["WCDL"])
api_v1_router.include_router(forex_router,    prefix="/forex",     tags=["Forex"])
api_v1_router.include_router(formulas_router, prefix="/admin/formulas", tags=["Admin Formulas"])
api_v1_router.include_router(models_router,   prefix="/admin/models",   tags=["Admin Models"])
api_v1_router.include_router(roles_router,    prefix="/admin/roles",    tags=["Admin Roles"])
api_v1_router.include_router(users_router,    prefix="/admin/users",    tags=["Admin Users"])
api_v1_router.include_router(settings_router, prefix="/settings",       tags=["Settings"])
api_v1_router.include_router(activity_router, prefix="/activity",       tags=["Activity"])
api_v1_router.include_router(audit_router,    prefix="/audit-logs",     tags=["Audit"])
api_v1_router.include_router(customers_router, prefix="/customers",     tags=["Customers"])
