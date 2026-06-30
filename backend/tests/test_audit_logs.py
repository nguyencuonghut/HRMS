"""Integration tests cho Audit Log endpoint."""
from fastapi.testclient import TestClient

BASE = "/api/v1/audit-logs"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_HR_MGR_EMAIL   = "hrmanager@hrms.local"
_OFFICER_EMAIL  = "hrofficer@hrms.local"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict:
    token = client.post("/api/v1/auth/login",
        json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient) -> dict:
    return _login(client)


def _hr_mgr(client: TestClient) -> dict:
    return _login(client, _HR_MGR_EMAIL)


def _officer(client: TestClient) -> dict:
    return _login(client, _OFFICER_EMAIL)


# ── Authorization ──────────────────────────────────────────────────────────────

def test_list_no_token_401(client: TestClient):
    resp = client.get(BASE)
    assert resp.status_code == 401


def test_list_officer_403(client: TestClient):
    # hr_officer không có audit_logs:view
    resp = client.get(BASE, headers=_officer(client))
    assert resp.status_code == 403


def test_list_admin_200(client: TestClient):
    resp = client.get(BASE, headers=_admin(client))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["items"], list)
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] >= len(data["items"])


def test_audit_log_meta_contract(client: TestClient):
    resp = client.get(f"{BASE}/meta", headers=_admin(client))
    assert resp.status_code == 200
    data = resp.json()
    assert any(item["code"] == "CREATE_CONTRACT" and item["label"] == "Tạo hợp đồng" for item in data["actions"])
    assert any(item["code"] == "employee_contract" and item["label"] == "Hợp đồng nhân viên" for item in data["entity_types"])


def test_list_hr_manager_200(client: TestClient):
    # hr_manager có audit_logs:view
    resp = client.get(BASE, headers=_hr_mgr(client))
    assert resp.status_code == 200


# ── Response shape ─────────────────────────────────────────────────────────────

def test_response_fields(client: TestClient):
    rows = client.get(BASE, headers=_admin(client)).json()["items"]
    assert len(rows) > 0
    row = rows[0]
    assert "id" in row
    assert "action" in row
    assert "action_label" in row
    assert "created_at" in row


def test_has_login_entries(client: TestClient):
    rows = client.get(BASE, params={"action": "LOGIN"}, headers=_admin(client)).json()["items"]
    assert len(rows) > 0
    assert all(r["action"] == "LOGIN" for r in rows)


# ── Filters ────────────────────────────────────────────────────────────────────

def test_filter_by_action(client: TestClient):
    rows = client.get(BASE, params={"action": "login"}, headers=_admin(client)).json()["items"]
    assert all(r["action"] == "LOGIN" for r in rows)


def test_filter_by_entity_type(client: TestClient):
    # Tạo 1 user để sinh audit CREATE entity_type=user
    import uuid
    client.post("/api/v1/users", json={
        "email": f"audittest{uuid.uuid4().hex[:6]}@test.local",
        "full_name": "Audit Test",
        "password": "Audit@123",
    }, headers=_admin(client))

    rows = client.get(BASE, params={"entity_type": "user", "action": "CREATE"},
        headers=_admin(client)).json()["items"]
    assert len(rows) > 0
    assert all(r["entity_type"] == "user" for r in rows)


def test_filter_by_user_id(client: TestClient):
    me = client.get("/api/v1/auth/me", headers=_admin(client)).json()
    rows = client.get(BASE, params={"user_id": me["id"]}, headers=_admin(client)).json()["items"]
    assert all(r["user_id"] == me["id"] for r in rows)


def test_filter_date_from_excludes_old(client: TestClient):
    rows = client.get(BASE, params={"date_from": "2099-01-01"}, headers=_admin(client)).json()["items"]
    assert rows == []


def test_filter_date_to_excludes_future(client: TestClient):
    rows = client.get(BASE, params={"date_to": "2000-01-01"}, headers=_admin(client)).json()["items"]
    assert rows == []


def test_limit_param(client: TestClient):
    resp = client.get(BASE, params={"page_size": 2}, headers=_admin(client))
    assert resp.status_code == 200
    rows = resp.json()["items"]
    assert len(rows) <= 2


def test_limit_max_500(client: TestClient):
    resp = client.get(BASE, params={"page_size": 101}, headers=_admin(client))
    assert resp.status_code == 422


def test_ordered_by_created_at_desc(client: TestClient):
    rows = client.get(BASE, params={"page_size": 10}, headers=_admin(client)).json()["items"]
    if len(rows) >= 2:
        assert rows[0]["created_at"] >= rows[-1]["created_at"]
