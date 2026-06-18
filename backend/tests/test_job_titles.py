"""Integration tests cho /api/v1/job-titles — dùng synchronous TestClient."""
from fastapi.testclient import TestClient

BASE   = "/api/v1/job-titles"
_CODE  = "TEST_JT_001"
_CODE2 = "TEST_JT_002"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _delete_by_code(client: TestClient, code: str) -> None:
    headers = _admin(client)
    for item in client.get(BASE, headers=headers).json():
        if item["code"] == code:
            client.delete(f"{BASE}/{item['id']}", headers=headers)


# ── Session cleanup (chạy 1 lần trước/sau toàn session) ───────────────────────

import pytest

@pytest.fixture(scope="session", autouse=True)
def session_cleanup(client: TestClient):
    for code in [_CODE, _CODE2]:
        _delete_by_code(client, code)
    yield
    for code in [_CODE, _CODE2]:
        _delete_by_code(client, code)


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_list_returns_200(client: TestClient):
    resp = client.get(BASE, headers=_admin(client))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_success(client: TestClient):
    headers = _admin(client)
    resp = client.post(BASE, json={"code": _CODE, "name": "Test Chức danh", "level": 5}, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == _CODE
    assert data["name"] == "Test Chức danh"
    assert data["level"] == 5
    assert data["is_active"] is True
    client.delete(f"{BASE}/{data['id']}", headers=headers)


def test_create_code_auto_uppercase(client: TestClient):
    headers = _admin(client)
    resp = client.post(BASE, json={"code": "test_jt_001", "name": "Test Upper", "level": 1}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["code"] == _CODE
    client.delete(f"{BASE}/{resp.json()['id']}", headers=headers)


def test_create_duplicate_code_409(client: TestClient):
    headers = _admin(client)
    r1 = client.post(BASE, json={"code": _CODE, "name": "First", "level": 1}, headers=headers)
    assert r1.status_code == 201
    r2 = client.post(BASE, json={"code": _CODE, "name": "Duplicate", "level": 2}, headers=headers)
    assert r2.status_code == 409
    client.delete(f"{BASE}/{r1.json()['id']}", headers=headers)


def test_create_invalid_level_422(client: TestClient):
    resp = client.post(BASE, json={"code": _CODE, "name": "Bad level", "level": 0}, headers=_admin(client))
    assert resp.status_code == 422


def test_update_name_and_level(client: TestClient):
    headers = _admin(client)
    r = client.post(BASE, json={"code": _CODE, "name": "Original", "level": 3}, headers=headers)
    jt_id = r.json()["id"]

    resp = client.put(f"{BASE}/{jt_id}", json={"name": "Updated name", "level": 2}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated name"
    assert data["level"] == 2
    assert data["updated_at"] is not None
    client.delete(f"{BASE}/{jt_id}", headers=headers)


def test_update_deactivate(client: TestClient):
    headers = _admin(client)
    r = client.post(BASE, json={"code": _CODE, "name": "Active JT", "level": 1}, headers=headers)
    jt_id = r.json()["id"]

    resp = client.put(f"{BASE}/{jt_id}", json={"is_active": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    client.delete(f"{BASE}/{jt_id}", headers=headers)


def test_update_not_found_404(client: TestClient):
    resp = client.put(f"{BASE}/999999", json={"name": "ghost"}, headers=_admin(client))
    assert resp.status_code == 404


def test_delete_success(client: TestClient):
    headers = _admin(client)
    r = client.post(BASE, json={"code": _CODE, "name": "To delete", "level": 9}, headers=headers)
    jt_id = r.json()["id"]

    resp = client.delete(f"{BASE}/{jt_id}", headers=headers)
    assert resp.status_code == 200
    assert "Đã xóa" in resp.json()["message"]

    assert all(i["code"] != _CODE for i in client.get(BASE, headers=headers).json())


def test_delete_not_found_404(client: TestClient):
    resp = client.delete(f"{BASE}/999999", headers=_admin(client))
    assert resp.status_code == 404


def test_filter_by_is_active(client: TestClient):
    headers = _admin(client)
    r1 = client.post(BASE, json={"code": _CODE,  "name": "Active JT",   "level": 1}, headers=headers)
    r2 = client.post(BASE, json={"code": _CODE2, "name": "Inactive JT", "level": 2}, headers=headers)
    client.put(f"{BASE}/{r2.json()['id']}", json={"is_active": False}, headers=headers)

    active_codes   = [i["code"] for i in client.get(BASE, params={"is_active": "true"}, headers=headers).json()]
    inactive_codes = [i["code"] for i in client.get(BASE, params={"is_active": "false"}, headers=headers).json()]

    assert _CODE  in active_codes   and _CODE2 not in active_codes
    assert _CODE2 in inactive_codes and _CODE  not in inactive_codes

    client.delete(f"{BASE}/{r1.json()['id']}", headers=headers)
    client.delete(f"{BASE}/{r2.json()['id']}", headers=headers)
