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
_CURRENT_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _CURRENT_DIR.parent.parent # app -> core -> root

# Initialize Firebase Admin SDK
def _init_firebase():
    if firebase_admin._apps:
        return
    
    # 1. Robust search for JSON in ENV (Fixes Vercel/Docker whitespace issues)
    json_str = None
    fb_keys = []
    for k, v in os.environ.items():
        if "FIREBASE" in k:
            fb_keys.append(k)
        if k.strip() == "FIREBASE_SERVICE_ACCOUNT_JSON":
            json_str = v
            break
            
    if json_str:
        print(f"INFO: Firebase JSON found (len={len(json_str)})")
        try:
            import json
            cred_dict = json.loads(json_str.strip())
            _cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(_cred)
            print("INFO: Firebase initialized successfully.")
            return
        except Exception as e:
            print(f"ERROR: Firebase JSON parse/init failed: {e}")
    else:
        print(f"WARN: 'FIREBASE_SERVICE_ACCOUNT_JSON' not found. Found relate: {fb_keys}")

    # 2. Fallback to file path
    _cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT") or "fincore-d419d-firebase-adminsdk-fbsvc-b6ab364cfd.json"
    if not os.path.isabs(_cred_path):
        _cred_path = str(_BACKEND_ROOT / _cred_path)

    if os.path.exists(_cred_path):
        try:
            _cred = credentials.Certificate(_cred_path)
            firebase_admin.initialize_app(_cred)
            print(f"INFO: Firebase initialized with file: {os.path.basename(_cred_path)}")
        except Exception as e:
            print(f"ERROR: File init failed: {e}")
    else:
        print(f"WARN: No Firebase credentials found. Checked path: {_cred_path}")

security = HTTPBearer()


async def get_current_user(res: HTTPAuthorizationCredentials = Security(security)):
    """Dependency to get the currently authenticated user based on Firebase Token."""
    # ENSURE FIREBASE IS INITIALIZED (Critical for Vercel Serverless)
    if not firebase_admin._apps:
        _init_firebase()
    
    token = res.credentials
    try:
        # 1. Verify Firebase Token with large clock skew tolerance (60s) for Windows sync jitter
        decoded_token = auth.verify_id_token(token, clock_skew_seconds=60)


        fb_uid = decoded_token['uid']
        email = decoded_token.get('email')
        name = decoded_token.get('name', '')
        photo_url = decoded_token.get('picture', '') # Firebase provides 'picture' for Google Auth

        # 2. Check if user exists in our DB
        rows = execute_query(
            'SELECT u.id, u."orgId", u."roleId", r.name as role_name, r."allowedPages" '
            'FROM "User" u JOIN "Role" r ON u."roleId" = r.id '
            'WHERE u."firebaseUid" = %s',
            (fb_uid,),
        )

        if not rows:
            # 3. Dynamic User Creation
            internal_id = f"user_{fb_uid[:12]}"
            
            # Fetch the actual ID of PENDING_APPROVAL dynamically just in case sequences shifted it
            role_rows = execute_query('SELECT id FROM "Role" WHERE name = %s', ("PENDING_APPROVAL",))
            pending_role_id = role_rows[0]["id"] if role_rows else 4 # Fallback
            
            execute_insert(
                """
                INSERT INTO "User" (id, email, name, "photoUrl", "firebaseUid", "orgId", "roleId", "lastLogin")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (internal_id, email, name, photo_url, fb_uid, 'default-org', pending_role_id, datetime.utcnow()),
            )
            print(f"[auth] Created NEW user: {email} (Role: {pending_role_id})")
            return {
                "id": internal_id, 
                "org_id": 'default-org', 
                "role_id": pending_role_id, 
                "role": "PENDING_APPROVAL", 
                "allowed_pages": [],
                "email": email, 
                "photo_url": photo_url
            }

        user = rows[0]
        print(f"[auth] User Identity Verified: {email} (Role: {user['roleId']})")
        return {
            "id": user["id"],
            "org_id": user["orgId"],
            "role_id": user["roleId"],
            "role": user["role_name"],
            "allowed_pages": user["allowedPages"] or ["*"],
            "email": email,
            "photo_url": photo_url,
        }


    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Auth Error: {e}")
        # Log the token for debugging (only first 10 chars for security)
        safe_token = f"{token[:10]}..." if token else "None"
        print(f"Token involved: {safe_token}")
        raise HTTPException(
            status_code=403,
            detail=f"Could not validate credentials: {str(e)}",
        )
