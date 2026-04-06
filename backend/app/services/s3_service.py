"""
Upload to S3, generate signed URLs.
In dev mode, uses local filesystem as drop-in replacement for S3.
"""

import os
import shutil
from pathlib import Path

from app.core.config import settings

STORAGE_ROOT = Path(settings.LOCAL_STORAGE_PATH)


class LocalStorage:
    """Mimics boto3 S3 client interface using local filesystem."""

    def __init__(self, root: Path = None):
        self.root = root or STORAGE_ROOT
        try:
            if not self.root.exists():
                self.root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass # Vercel may have restricted access to non-tmp paths


    def _resolve(self, key: str) -> Path:
        full = self.root / key
        full.parent.mkdir(parents=True, exist_ok=True)
        return full

    def download_file(self, bucket_or_key: str, key_or_path: str, local_path: str = None):
        if local_path is not None:
            key = key_or_path
            dest = local_path
        else:
            key = bucket_or_key
            dest = key_or_path

        src = self._resolve(key)
        if not src.exists():
            raise FileNotFoundError(f"Local storage key not found: {key} (looked at {src})")
        shutil.copy2(str(src), dest)

    def upload_file(self, local_path: str, bucket_or_key: str, key: str = None):
        if key is not None:
            dest_key = key
        else:
            dest_key = bucket_or_key
        dest = self._resolve(dest_key)
        shutil.copy2(local_path, str(dest))

    def generate_presigned_url(self, method: str = None, Params: dict = None, ExpiresIn: int = 900) -> str:
        if Params and "Key" in Params:
            key = Params["Key"]
        else:
            key = method
        return f"/files/{key}"

    def file_exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def get_local_path(self, key: str) -> str:
        return str(self._resolve(key))

    def save_upload(self, file_bytes: bytes, key: str) -> str:
        dest = self._resolve(key)
        dest.write_bytes(file_bytes)
        return key


def get_storage() -> LocalStorage:
    return LocalStorage()
