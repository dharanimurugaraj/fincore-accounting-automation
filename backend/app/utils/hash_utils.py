"""
SHA-256 for audit integrity.
"""

import hashlib
import json


def sha256_hash(data: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hash_dict(d: dict) -> str:
    """Compute SHA-256 hash of a dictionary (JSON-serialised)."""
    return sha256_hash(json.dumps(d, sort_keys=True, default=str))
