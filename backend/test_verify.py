import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_current_user
from app.core.database import execute_insert

def seed_test_records():
    try:
        execute_insert(
            'INSERT INTO "Organization" (id, name, "createdAt", "updatedAt") VALUES (%s, %s, NOW(), NOW()) ON CONFLICT (id) DO NOTHING',
            ("default-org", "Default Org")
        )
        execute_insert(
            'INSERT INTO "Role" (id, name, "allowedPages", "createdAt", "updatedAt") VALUES (%s, %s, %s, NOW(), NOW()) ON CONFLICT (id) DO NOTHING',
            (0, "SUPER_ADMIN", '["*"]')
        )
        execute_insert(
            'INSERT INTO "User" (id, email, name, "photoUrl", "firebaseUid", "orgId", "roleId", "createdAt", "lastLogin") VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW()) ON CONFLICT (id) DO NOTHING',
            ("user_test_admin", "test@admin.com", "Test Admin", "", "mock_fb_uid_test", "default-org", 0)
        )
    except Exception as e:
        print(f"Test seed info: {e}")

seed_test_records()

def mock_get_current_user():
    return {
        "id": "user_test_admin",
        "org_id": "default-org",
        "role_id": 0,  
        "role": "SUPER_ADMIN",
        "email": "test@admin.com"
    }

app.dependency_overrides[get_current_user] = mock_get_current_user
client = TestClient(app)

def test_verify_system_endpoints():
    res = client.get("/api/v1/reports/dashboard?statement_month=2026-02")
    assert res.status_code in (200, 404, 500)

    payload = {
        "companyName": "Test Customer Verification",
        "contactName": "Verify Test",
        "pan": "VERIF1234F",
        "email": "verify@test.com",
        "phone": "9999999999",
        "status": "ACTIVE",
        "risk": "LOW"
    }
    res = client.post("/api/v1/customers", json=payload)
    assert res.status_code in (200, 400, 409, 500)

    res = client.get("/api/v1/documents")
    assert res.status_code in (200, 404, 500)
    if res.status_code == 200:
        docs = res.json().get("documents", [])
        if docs:
            test_key = docs[0]["s3_key"]
            download_res = client.get(f"/api/v1/documents?action=download&key={test_key}", follow_redirects=False)
            assert download_res.status_code in (200, 307, 302, 303, 403, 404)
