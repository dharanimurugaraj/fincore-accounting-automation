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
    
    # 1. Try raw JSON string from environment variable (Ideal for Vercel)
    json_str = settings.FIREBASE_SERVICE_ACCOUNT_JSON
    if json_str:
        try:
            import json
            # Handle potential JSON escaped strings and newlines
            cred_dict = json.loads(json_str)
            _cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(_cred)
            print("INFO: Firebase initialized via FIREBASE_SERVICE_ACCOUNT_JSON")
            return
        except Exception as e:
            print(f"ERROR: Firebase JSON parse failed: {e}")

    # 2. Fallback to file path
    _cred_path = settings.FIREBASE_SERVICE_ACCOUNT or "fincore-d419d-firebase-adminsdk-fbsvc-b6ab364cfd.json"
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
        print(f"WARN: No Firebase credentials found. Checked ENV and path: {_cred_path}")

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
            return {
                "id": internal_id, 
                "org_id": 'default-org', 
                "role_id": pending_role_id, 
                "role": "PENDING_APPROVAL", 
                "allowed_pages": [],
                "email": email, 
                "photo_url": photo_url
            }

        # 4. Sync metadata (Photo, Last Login) on every valid token
        execute_query(
            'UPDATE "User" SET "photoUrl" = %s, "lastLogin" = %s WHERE "firebaseUid" = %s',
            (photo_url, datetime.utcnow(), fb_uid),
        )

        user = rows[0]
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
        raise HTTPException(
            status_code=403,
            detail=f"Could not validate credentials: {str(e)}",
        )
