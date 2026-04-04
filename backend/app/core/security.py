"""
Firebase Authentication Security — Token verification and User mapping.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.database import execute_query, execute_insert

# Setup Absolute Paths to the Backend Root (where .env and keys live)
# Path of this file: app/core/security.py
_CURRENT_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _CURRENT_DIR.parent.parent # app -> core -> root

# Initialize Firebase Admin SDK
_cred_path = settings.FIREBASE_SERVICE_ACCOUNT
if not _cred_path:
    # Use default filename if not set in .env
    _cred_path = "fincore-d419d-firebase-adminsdk-fbsvc-b6ab364cfd.json"

# Resolve correctly relative to root if not already absolute
if not os.path.isabs(_cred_path):
    _cred_path = str(_BACKEND_ROOT / _cred_path)

if os.path.exists(_cred_path):
    if not firebase_admin._apps:
        try:
            _cred = credentials.Certificate(_cred_path)
            firebase_admin.initialize_app(_cred)
            print(f"INFO: Firebase initialized successfully with: {os.path.basename(_cred_path)}")
        except Exception as e:
            print(f"ERROR: Failed to init Firebase with {_cred_path}: {e}")
else:
    print(f"WARN: Firebase service account key NOT FOUND at {_cred_path}")
    print(f"DEBUG: Current Root was resolved to {_BACKEND_ROOT}")

security = HTTPBearer()


async def get_current_user(res: HTTPAuthorizationCredentials = Security(security)):
    """Dependency to get the currently authenticated user based on Firebase Token."""
    token = res.credentials
    try:
        # 1. Verify Firebase Token
        decoded_token = auth.verify_id_token(token)
        fb_uid = decoded_token['uid']
        email = decoded_token.get('email')
        name = decoded_token.get('name', '')
        photo_url = decoded_token.get('picture', '') # Firebase provides 'picture' for Google Auth

        # 2. Check if user exists in our DB
        rows = execute_query(
            'SELECT id, "orgId", role FROM "User" WHERE "firebaseUid" = %s',
            (fb_uid,),
        )

        if not rows:
            # 3. Dynamic User Creation
            internal_id = f"user_{fb_uid[:12]}"
            execute_insert(
                """
                INSERT INTO "User" (id, email, name, "photoUrl", "firebaseUid", "orgId", role, "lastLogin")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (internal_id, email, name, photo_url, fb_uid, 'default-org', 'ANALYST', datetime.utcnow()),
            )
            return {"id": internal_id, "org_id": 'default-org', "role": 'ANALYST', "email": email, "photo_url": photo_url}

        # 4. Sync metadata (Photo, Last Login) on every valid token
        execute_query(
            'UPDATE "User" SET "photoUrl" = %s, "lastLogin" = %s WHERE "firebaseUid" = %s',
            (photo_url, datetime.utcnow(), fb_uid),
        )

        user = rows[0]
        return {
            "id": user["id"],
            "org_id": user["orgId"],
            "role": user["role"],
            "email": email,
        }

    except Exception as e:
        raise HTTPException(
            status_code=403,
            detail=f"Could not validate credentials: {str(e)}",
        )
