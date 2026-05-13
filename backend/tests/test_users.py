"""Integration tests cho User Management endpoints."""
import uuid
from fastapi.testclient import TestClient

BASE = "/api/v1/users"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_HR_MGR_EMAIL   = "hrmanager@hrms.local"
_OFFICER_EMAIL  = "hrofficer@hrms.local"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict:
    token = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient) -> dict:
    return _login(client)


def _hr_mgr(client: TestClient) -> dict:
    return _login(client, _HR_MGR_EMAIL)


def _officer(client: TestClient) -> dict:
    return _login(client, _OFFICER_EMAIL)


def _create_test_user(client: TestClient, suffix: str = "") -> dict:
    unique = uuid.uuid4().hex[:8]
    email = f"test{suffix}{unique}@test.local"
    resp = client.post(BASE, json={
        "email": email,
        "full_name": f"Test User {suffix or unique}",
        "password": "Test@1234",
        "is_active": True,
        "is_superuser": False,
    }, headers=_admin(client))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── GET /users ─────────────────────────────────────────────────────────────────

def test_list_users_admin_200(client: TestClient):
    resp = client.get(BASE, headers=_admin(client))
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 5  # seed users


def test_list_users_no_token_401(client: TestClient):
    resp = client.get(BASE)
    assert resp.status_code == 401


def test_list_users_officer_403(client: TestClient):
    resp = client.get(BASE, headers=_officer(client))
    assert resp.status_code == 403


def test_list_users_hr_manager_403(client: TestClient):
    # hr_manager không có users:view trong seed
    resp = client.get(BASE, headers=_hr_mgr(client))
    assert resp.status_code == 403


def test_list_users_search(client: TestClient):
    resp = client.get(BASE, params={"search": "admin"}, headers=_admin(client))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any("admin" in u["email"] for u in items)


def test_list_users_filter_active(client: TestClient):
    resp = client.get(BASE, params={"is_active": True}, headers=_admin(client))
    assert resp.status_code == 200
    assert all(u["is_active"] for u in resp.json()["items"])


def test_list_users_pagination(client: TestClient):
    resp = client.get(BASE, params={"skip": 0, "limit": 2}, headers=_admin(client))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) <= 2
    assert body["limit"] == 2


# ── POST /users ────────────────────────────────────────────────────────────────

def test_create_user_success(client: TestClient):
    suffix = uuid.uuid4().hex[:8]
    resp = client.post(BASE, json={
        "email": f"new{suffix}@test.local",
        "full_name": "New User",
        "password": "NewPass@1",
        "is_active": True,
        "is_superuser": False,
    }, headers=_admin(client))
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == f"new{suffix}@test.local"
    assert body["full_name"] == "New User"
    assert body["is_active"] is True
    assert body["is_superuser"] is False


def test_create_user_duplicate_email_409(client: TestClient):
    resp = client.post(BASE, json={
        "email": _ADMIN_EMAIL,
        "full_name": "Dup Admin",
        "password": "Dup@12345",
    }, headers=_admin(client))
    assert resp.status_code == 409


def test_create_user_weak_password_422(client: TestClient):
    resp = client.post(BASE, json={
        "email": "weakpass@test.local",
        "full_name": "Weak User",
        "password": "onlyletters",  # no digit
    }, headers=_admin(client))
    assert resp.status_code == 422


def test_create_user_short_password_422(client: TestClient):
    resp = client.post(BASE, json={
        "email": "short@test.local",
        "full_name": "Short User",
        "password": "Sh@1",  # too short
    }, headers=_admin(client))
    assert resp.status_code == 422


def test_create_user_requires_create_perm(client: TestClient):
    resp = client.post(BASE, json={
        "email": "blocked@test.local",
        "full_name": "Blocked",
        "password": "Block@123",
    }, headers=_officer(client))
    assert resp.status_code == 403


# ── GET /users/{id} ────────────────────────────────────────────────────────────

def test_get_user_by_id(client: TestClient):
    user = _create_test_user(client, suffix="get01")
    resp = client.get(f"{BASE}/{user['id']}", headers=_admin(client))
    assert resp.status_code == 200
    assert resp.json()["email"] == user["email"]


def test_get_user_not_found_404(client: TestClient):
    resp = client.get(f"{BASE}/999999", headers=_admin(client))
    assert resp.status_code == 404


# ── PUT /users/{id} ────────────────────────────────────────────────────────────

def test_update_user_name(client: TestClient):
    user = _create_test_user(client, suffix="upd01")
    resp = client.put(f"{BASE}/{user['id']}", json={"full_name": "Updated Name"}, headers=_admin(client))
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"


def test_update_user_deactivate(client: TestClient):
    user = _create_test_user(client, suffix="deact01")
    resp = client.put(f"{BASE}/{user['id']}", json={"is_active": False}, headers=_admin(client))
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_update_user_duplicate_email_409(client: TestClient):
    user = _create_test_user(client, suffix="dup02")
    resp = client.put(f"{BASE}/{user['id']}", json={"email": _ADMIN_EMAIL}, headers=_admin(client))
    assert resp.status_code == 409


def test_update_user_requires_edit_perm(client: TestClient):
    user = _create_test_user(client, suffix="perm02")
    resp = client.put(f"{BASE}/{user['id']}", json={"full_name": "Hacked"}, headers=_officer(client))
    assert resp.status_code == 403


# ── DELETE /users/{id} ─────────────────────────────────────────────────────────

def test_delete_user_deactivates(client: TestClient):
    user = _create_test_user(client, suffix="del01")
    resp = client.delete(f"{BASE}/{user['id']}", headers=_admin(client))
    assert resp.status_code == 204

    # Xác nhận bị vô hiệu hóa
    detail = client.get(f"{BASE}/{user['id']}", headers=_admin(client))
    assert detail.json()["is_active"] is False


def test_delete_self_400(client: TestClient):
    me = client.get("/api/v1/auth/me", headers=_admin(client)).json()
    resp = client.delete(f"{BASE}/{me['id']}", headers=_admin(client))
    assert resp.status_code == 400


def test_delete_not_found_404(client: TestClient):
    resp = client.delete(f"{BASE}/999999", headers=_admin(client))
    assert resp.status_code == 404


# ── POST /users/{id}/reset-password ───────────────────────────────────────────

def test_reset_password_success(client: TestClient):
    suffix = uuid.uuid4().hex[:8]
    email = f"rpw{suffix}@test.local"
    user = client.post(BASE, json={
        "email": email, "full_name": "RPW User", "password": "Init@1234",
    }, headers=_admin(client)).json()

    resp = client.post(f"{BASE}/{user['id']}/reset-password",
        json={"new_password": "NewPwd@9876"},
        headers=_admin(client))
    assert resp.status_code == 200

    # Đăng nhập với mật khẩu mới
    assert client.post("/api/v1/auth/login",
        json={"email": email, "password": "NewPwd@9876"}).status_code == 200


def test_reset_password_weak_422(client: TestClient):
    user = _create_test_user(client, suffix="rpwweak")
    resp = client.post(f"{BASE}/{user['id']}/reset-password",
        json={"new_password": "nouppernodigit"},
        headers=_admin(client))
    assert resp.status_code == 422


# ── GET /users/{id}/roles ──────────────────────────────────────────────────────

def test_get_user_roles(client: TestClient):
    resp = client.get("/api/v1/auth/me", headers=_admin(client))
    admin_id = resp.json()["id"]
    roles_resp = client.get(f"{BASE}/{admin_id}/roles", headers=_admin(client))
    assert roles_resp.status_code == 200
    codes = [r["code"] for r in roles_resp.json()]
    assert "admin" in codes


# ── POST /users/{id}/roles ─────────────────────────────────────────────────────

def test_assign_and_remove_role(client: TestClient):
    suffix = uuid.uuid4().hex[:8]
    user = client.post(BASE, json={
        "email": f"roletest{suffix}@test.local",
        "full_name": "Role Test",
        "password": "Role@1234",
    }, headers=_admin(client)).json()

    # Lấy role id của hr_officer từ seed
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.core.config import settings
    import asyncio

    async def _get_role_id():
        engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
        async with async_sessionmaker(engine)() as s:
            row = (await s.execute(text("SELECT id FROM roles WHERE code='hr_officer'"))).fetchone()
        await engine.dispose()
        return row[0]

    role_id = asyncio.get_event_loop().run_until_complete(_get_role_id())

    # Gán role
    resp = client.post(f"{BASE}/{user['id']}/roles",
        json={"role_id": role_id},
        headers=_admin(client))
    assert resp.status_code == 201
    assert resp.json()["code"] == "hr_officer"

    # Bỏ role
    resp2 = client.delete(f"{BASE}/{user['id']}/roles/{role_id}", headers=_admin(client))
    assert resp2.status_code == 204


def test_assign_role_not_found_404(client: TestClient):
    user = _create_test_user(client, suffix="rna")
    resp = client.post(f"{BASE}/{user['id']}/roles",
        json={"role_id": 999999},
        headers=_admin(client))
    assert resp.status_code == 404


def test_remove_role_not_assigned_404(client: TestClient):
    user = _create_test_user(client, suffix="rnr")
    resp = client.delete(f"{BASE}/{user['id']}/roles/999999", headers=_admin(client))
    assert resp.status_code == 404
