"""
All environment variables for FinCore.
Reads from .env, validates, and exposes as a singleton `settings` object.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend folder (where the environment-specific config lives)
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path, override=True)


class Settings:
    """Central config — all env vars in one place."""

    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://fincore:fincore_dev@localhost:5432/fincore_dev",
    )

    # ── Storage (S3 or local) ───────────────────────────────────────────────
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    S3_REGION: str = os.getenv("S3_REGION", "ap-south-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    LOCAL_STORAGE_PATH: str = os.getenv(
        "LOCAL_STORAGE_PATH",
        str(Path(__file__).parent.parent.parent / "storage" / "data"),
    )
    USE_LOCAL_STORAGE: bool = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"

    # ── AI / LLM ───────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")

    # ── Firebase ────────────────────────────────────────────────────────────
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_SERVICE_ACCOUNT: str = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")
    FIREBASE_SERVICE_ACCOUNT_JSON: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")

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
