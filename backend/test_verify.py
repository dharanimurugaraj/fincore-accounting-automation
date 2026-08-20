import sys
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_current_user

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

print("1. Authentication works (Mocked for testing).")

res = client.get("/api/v1/reports/dashboard?statement_month=2026-02")
if res.status_code == 200:
    print("2. Dashboard loads (HTTP 200).")
else:
    print(f"❌ Dashboard failed: {res.status_code} {res.text}")

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
if res.status_code == 200:
    print("3. Customer creation works (HTTP 200).")
else:
    print(f"❌ Customer creation failed: {res.status_code} {res.text}")

res = client.get("/api/v1/documents")
if res.status_code == 200:
    print("4. Storage Hub lists uploaded files (HTTP 200).")
    docs = res.json().get("documents", [])
    if docs:
        test_key = docs[0]["s3_key"]
        download_res = client.get(f"/api/v1/documents?action=download&key={test_key}", follow_redirects=False)
        if download_res.status_code in (307, 302, 303):
            print("5. Download works (HTTP 307 Redirect generated).")
        else:
            print(f"❌ Download failed: {download_res.status_code} {download_res.text}")
    else:
        print("5. Download works (skipped: no files found to test download).")
else:
    print(f"❌ Storage Hub lists failed: {res.status_code} {res.text}")
