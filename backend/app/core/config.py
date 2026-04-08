"""
All environment variables for FinCore.
Reads from .env, validates, and exposes as a singleton `settings` object.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in current folder or parents to find the backend root
_search_dir = Path(__file__).parent.parent.parent
_env_path = _search_dir / ".env"

if not os.getenv("VERCEL"):
    if _env_path.exists():
        print(f"DEBUG: Found .env at {_env_path}")
        load_dotenv(_env_path, override=True)
    else:
        # Fallback to project root if being run from root
        _root_env = _search_dir.parent / ".env"
        if _root_env.exists():
            print(f"DEBUG: Found fallback .env at {_root_env}")
            load_dotenv(_root_env, override=True)



class Settings:
    """Central config — all env vars in one place."""

    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")


    # ── Storage (S3 or local) ───────────────────────────────────────────────
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    S3_REGION: str = os.getenv("S3_REGION", "ap-south-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    # In Vercel, the filesystem is read-only except /tmp
    _default_stor = "/tmp/fincore" if os.getenv("VERCEL") else str(Path(__file__).parent.parent.parent / "storage" / "data")
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", _default_stor)
    USE_LOCAL_STORAGE: bool = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"

    # ── AI / LLM ───────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

    # ── Firebase ────────────────────────────────────────────────────────────
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_SERVICE_ACCOUNT: str = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")
    
    # Pre-process the JSON string to fix escaped newlines common in Vercel/Docker
    _raw_fb_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    FIREBASE_SERVICE_ACCOUNT_JSON: str = _raw_fb_json.replace("\\n", "\n") if _raw_fb_json else ""

    # ── Frontend ────────────────────────────────────────────────────────────
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # ── Forex ───────────────────────────────────────────────────────────────
    USE_RATE_FIXTURES: bool = os.getenv("USE_RATE_FIXTURES", "false").lower() == "true"

    # ── Notification ────────────────────────────────────────────────────────
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")

    @property
    def gemini_available(self) -> bool:
        return bool(self.GEMINI_API_KEY and not self.GEMINI_API_KEY.startswith("REPLACE"))


settings = Settings()
