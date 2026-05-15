"""Integration tests cho Role & Permission Management endpoints."""
import uuid
from fastapi.testclient import TestClient

BASE       = "/api/v1/roles"
PERM_BASE  = "/api/v1/roles/permissions"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_OFFICER_EMAIL  = "hrofficer@hrms.local"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _admin(client: TestClient) -> dict:
    token = client.post("/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _officer(client: TestClient) -> dict:
    token = client.post("/api/v1/auth/login",
        json={"email": _OFFICER_EMAIL, "password": _ADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_role(client: TestClient, code: str = None) -> dict:
    code = code or f"testrole_{uuid.uuid4().hex[:6]}"
    resp = client.post(BASE, json={
        "code": code,
        "name": f"Test Role {code}",
        "description": "For testing",
    }, headers=_admin(client))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── GET /permissions ───────────────────────────────────────────────────────────

def test_list_permissions_admin_200(client: TestClient):
    resp = client.get(PERM_BASE, headers=_admin(client))
    assert resp.status_code == 200
    perms = resp.json()
    assert len(perms) == 70  # 14 modules × 5 actions
    assert all("code" in p and "module" in p and "action" in p for p in perms)


def test_list_permissions_no_token_401(client: TestClient):
    resp = client.get(PERM_BASE)
    assert resp.status_code == 401


def test_list_permissions_officer_403(client: TestClient):
    resp = client.get(PERM_BASE, headers=_officer(client))
    assert resp.status_code == 403


def test_permissions_format(client: TestClient):
    perms = client.get(PERM_BASE, headers=_admin(client)).json()
    for p in perms:
        module, action = p["code"].split(":")
        assert module == p["module"]
        assert action == p["action"]


# ── GET /roles ─────────────────────────────────────────────────────────────────

def test_list_roles_admin_200(client: TestClient):
    resp = client.get(BASE, headers=_admin(client))
    assert resp.status_code == 200
    roles = resp.json()
    codes = [r["code"] for r in roles]
    assert "admin" in codes
    assert "hr_manager" in codes
    assert "hr_officer" in codes
    assert "line_manager" in codes
    assert "finance" in codes


def test_list_roles_no_token_401(client: TestClient):
    resp = client.get(BASE)
    assert resp.status_code == 401


def test_list_roles_officer_403(client: TestClient):
    resp = client.get(BASE, headers=_officer(client))
    assert resp.status_code == 403


def test_list_roles_has_permission_count(client: TestClient):
    roles = client.get(BASE, headers=_admin(client)).json()
    admin_role = next(r for r in roles if r["code"] == "admin")
    assert admin_role["permission_count"] == 70  # 14 modules × 5 actions


def test_list_roles_system_flag(client: TestClient):
    roles = client.get(BASE, headers=_admin(client)).json()
    for r in roles:
        if r["code"] in ("admin", "hr_manager", "hr_officer", "line_manager", "finance"):
            assert r["is_system"] is True


# ── POST /roles ────────────────────────────────────────────────────────────────

def test_create_role_success(client: TestClient):
    role = _create_role(client)
    assert role["is_system"] is False
    assert role["permissions"] == []


def test_create_role_duplicate_code_409(client: TestClient):
    resp = client.post(BASE, json={
        "code": "admin",
        "name": "Dup Admin",
    }, headers=_admin(client))
    assert resp.status_code == 409


def test_create_role_no_token_401(client: TestClient):
    resp = client.post(BASE, json={"code": "x", "name": "X"})
    assert resp.status_code == 401


def test_create_role_officer_403(client: TestClient):
    resp = client.post(BASE, json={"code": "blocked", "name": "Blocked"},
        headers=_officer(client))
    assert resp.status_code == 403


# ── GET /roles/{id} ────────────────────────────────────────────────────────────

def test_get_role_by_id(client: TestClient):
    roles = client.get(BASE, headers=_admin(client)).json()
    hr_mgr = next(r for r in roles if r["code"] == "hr_manager")
    resp = client.get(f"{BASE}/{hr_mgr['id']}", headers=_admin(client))
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "hr_manager"
    assert len(body["permissions"]) > 0


def test_get_role_not_found_404(client: TestClient):
    resp = client.get(f"{BASE}/999999", headers=_admin(client))
    assert resp.status_code == 404


def test_get_role_includes_permissions(client: TestClient):
    roles = client.get(BASE, headers=_admin(client)).json()
    admin_role = next(r for r in roles if r["code"] == "admin")
    body = client.get(f"{BASE}/{admin_role['id']}", headers=_admin(client)).json()
    assert len(body["permissions"]) == 70  # 14 modules × 5 actions


# ── PUT /roles/{id} ────────────────────────────────────────────────────────────

def test_update_role_name(client: TestClient):
    role = _create_role(client)
    resp = client.put(f"{BASE}/{role['id']}", json={"name": "Updated Name"},
        headers=_admin(client))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


def test_update_role_not_found_404(client: TestClient):
    resp = client.put(f"{BASE}/999999", json={"name": "X"}, headers=_admin(client))
    assert resp.status_code == 404


def test_update_role_requires_edit_perm(client: TestClient):
    role = _create_role(client)
    resp = client.put(f"{BASE}/{role['id']}", json={"name": "Hacked"},
        headers=_officer(client))
    assert resp.status_code == 403


# ── DELETE /roles/{id} ─────────────────────────────────────────────────────────

def test_delete_role_success(client: TestClient):
    role = _create_role(client)
    resp = client.delete(f"{BASE}/{role['id']}", headers=_admin(client))
    assert resp.status_code == 204

    resp2 = client.get(f"{BASE}/{role['id']}", headers=_admin(client))
    assert resp2.status_code == 404


def test_delete_system_role_400(client: TestClient):
    roles = client.get(BASE, headers=_admin(client)).json()
    admin_role = next(r for r in roles if r["code"] == "admin")
    resp = client.delete(f"{BASE}/{admin_role['id']}", headers=_admin(client))
    assert resp.status_code == 400


def test_delete_role_not_found_404(client: TestClient):
    resp = client.delete(f"{BASE}/999999", headers=_admin(client))
    assert resp.status_code == 404


# ── GET /roles/{id}/permissions ────────────────────────────────────────────────

def test_get_role_permissions(client: TestClient):
    roles = client.get(BASE, headers=_admin(client)).json()
    finance = next(r for r in roles if r["code"] == "finance")
    resp = client.get(f"{BASE}/{finance['id']}/permissions", headers=_admin(client))
    assert resp.status_code == 200
    codes = {p["code"] for p in resp.json()}
    assert "insurance:view" in codes
    assert "salary:view" in codes
    assert "org:delete" not in codes


def test_get_role_permissions_not_found_404(client: TestClient):
    resp = client.get(f"{BASE}/999999/permissions", headers=_admin(client))
    assert resp.status_code == 404


# ── PUT /roles/{id}/permissions ────────────────────────────────────────────────

def test_replace_permissions_success(client: TestClient):
    role = _create_role(client)

    # Lấy id của 2 permissions bất kỳ
    all_perms = client.get(PERM_BASE, headers=_admin(client)).json()
    pids = [all_perms[0]["id"], all_perms[1]["id"]]

    resp = client.put(f"{BASE}/{role['id']}/permissions",
        json={"permission_ids": pids},
        headers=_admin(client))
    assert resp.status_code == 200
    returned_ids = {p["id"] for p in resp.json()}
    assert returned_ids == set(pids)


def test_replace_permissions_clears_existing(client: TestClient):
    role = _create_role(client)
    all_perms = client.get(PERM_BASE, headers=_admin(client)).json()

    # Gán 3 permissions
    pids3 = [p["id"] for p in all_perms[:3]]
    client.put(f"{BASE}/{role['id']}/permissions",
        json={"permission_ids": pids3}, headers=_admin(client))

    # Thay bằng 1 permission khác
    pid1 = [all_perms[10]["id"]]
    resp = client.put(f"{BASE}/{role['id']}/permissions",
        json={"permission_ids": pid1}, headers=_admin(client))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == all_perms[10]["id"]


def test_replace_permissions_empty_clears_all(client: TestClient):
    role = _create_role(client)
    all_perms = client.get(PERM_BASE, headers=_admin(client)).json()
    client.put(f"{BASE}/{role['id']}/permissions",
        json={"permission_ids": [all_perms[0]["id"]]}, headers=_admin(client))

    resp = client.put(f"{BASE}/{role['id']}/permissions",
        json={"permission_ids": []}, headers=_admin(client))
    assert resp.status_code == 200
    assert resp.json() == []


def test_replace_permissions_requires_edit_perm(client: TestClient):
    role = _create_role(client)
    resp = client.put(f"{BASE}/{role['id']}/permissions",
        json={"permission_ids": []}, headers=_officer(client))
    assert resp.status_code == 403


def test_replace_permissions_not_found_404(client: TestClient):
    resp = client.put(f"{BASE}/999999/permissions",
        json={"permission_ids": []}, headers=_admin(client))
    assert resp.status_code == 404
