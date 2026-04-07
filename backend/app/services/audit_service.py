from datetime import datetime
import uuid
import json
from typing import Any, Dict, Optional
from app.core.database import execute_insert

def log_action(
    user: Dict[str, Any],
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Centralized logging for EVERY critical action in the system.
    Tracks User, Org, Action, and relevant metadata.
    """
    log_id = f"audit_{uuid.uuid4().hex[:16]}"
    
    # Enrich metadata with user context
    audit_metadata = metadata or {}
    audit_metadata.update({
        "user_email": user.get("email"),
        "role_id": user.get("role_id"),
        "role_name": user.get("role_name"),
        "ip_address": user.get("ip_address", "internal")
    })

    try:
        execute_insert(
            """
            INSERT INTO "AuditLog"
                (id, "orgId", "userId", action, "entityType", "entityId", metadata, "createdAt")
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                log_id,
                user.get("org_id"),
                user.get("id"),
                action,
                entity_type,
                entity_id,
                json.dumps(audit_metadata),
                datetime.utcnow()
            )
        )
    except Exception as e:
        # We don't want audit failure to crash the main request, but we should log it
        print(f"CRITICAL: Failed to record audit log: {e}")
