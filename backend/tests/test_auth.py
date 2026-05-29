"""Integration tests cho Auth endpoints."""
import uuid
from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password

BASE = "/api/v1/auth"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_WRONG_PASSWORD = "wrongpassword"
_OFFICER_EMAIL  = "hrofficer@hrms.local"
_FINANCE_EMAIL  = "finance@hrms.local"
_IP_COUNTER = count(50)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
async def reset_officer_password():
    """Reset mật khẩu hrofficer về giá trị ban đầu trước mỗi test dùng fixture này."""
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        await s.execute(
            text("UPDATE users SET hashed_password = :hp WHERE email = :email"),
            {"hp": hash_password(_ADMIN_PASSWORD), "email": _OFFICER_EMAIL},
        )
        await s.commit()
    await engine.dispose()
    yield


# ── Helpers ────────────────────────────────────────────────────────────────────

def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD):
    return client.post(
        f"{BASE}/login",
        json={"email": email, "password": password},
        headers={"X-Forwarded-For": f"198.18.0.{next(_IP_COUNTER)}"},
    )


def _bearer(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict:
    token = _login(client, email, password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _refresh(client: TestClient, refresh_token: str):
    return client.post(
        f"{BASE}/refresh",
        json={"refresh_token": refresh_token},
        headers={"X-Forwarded-For": f"198.18.1.{next(_IP_COUNTER)}"},
    )


# ── Login ──────────────────────────────────────────────────────────────────────

def test_login_success(client: TestClient):
    resp = _login(client)
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient):
    resp = _login(client, password=_WRONG_PASSWORD)
    assert resp.status_code == 401


def test_login_unknown_email(client: TestClient):
    resp = _login(client, email=f"nobody-{uuid.uuid4().hex[:8]}@hrms.local")
    assert resp.status_code == 401


def test_login_invalid_email_returns_401(client: TestClient):
    # email không tồn tại → 401 (login dùng str, không validate format)
    resp = client.post(
        f"{BASE}/login",
        json={"email": f"not-an-email-{uuid.uuid4().hex[:8]}", "password": "x"},
        headers={"X-Forwarded-For": f"198.18.2.{next(_IP_COUNTER)}"},
    )
    assert resp.status_code == 401


# ── /me ────────────────────────────────────────────────────────────────────────

def test_me_returns_user_info(client: TestClient):
    resp = client.get(f"{BASE}/me", headers=_bearer(client))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == _ADMIN_EMAIL
    assert body["is_superuser"] is True
    assert "admin" in body["roles"]
    assert "*" in body["permissions"]


def test_me_no_token_returns_401(client: TestClient):
    resp = client.get(f"{BASE}/me")
    assert resp.status_code == 401


def test_me_invalid_token_returns_401(client: TestClient):
    resp = client.get(f"{BASE}/me", headers={"Authorization": "Bearer bad.token.here"})
    assert resp.status_code == 401


def test_me_hr_manager_has_correct_roles(client: TestClient):
    headers = _bearer(client, "hrmanager@hrms.local")
    resp = client.get(f"{BASE}/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["roles"] == ["hr_manager"]
    assert body["is_superuser"] is False
    assert "employees:view" in body["permissions"]
    assert "users:delete" not in body["permissions"]


def test_me_line_manager_limited_permissions(client: TestClient):
    headers = _bearer(client, "linemanager@hrms.local")
    resp = client.get(f"{BASE}/me", headers=headers)
    body = resp.json()
    assert "org:view" in body["permissions"]
    assert "employees:delete" not in body["permissions"]
    assert "users:view" not in body["permissions"]


# ── Refresh ────────────────────────────────────────────────────────────────────

def test_refresh_returns_new_tokens(client: TestClient):
    login_data = _login(client).json()
    resp = _refresh(client, login_data["refresh_token"])
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    me = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200


def test_refresh_with_access_token_fails(client: TestClient):
    login_data = _login(client).json()
    resp = _refresh(client, login_data["access_token"])
    assert resp.status_code == 401


def test_refresh_with_invalid_token_fails(client: TestClient):
    resp = _refresh(client, "invalid.token.here")
    assert resp.status_code == 401


# ── Change Password ────────────────────────────────────────────────────────────

def test_change_password_success(client: TestClient, reset_officer_password):
    headers = _bearer(client, "hrofficer@hrms.local")
    resp = client.post(
        f"{BASE}/change-password",
        json={"old_password": _ADMIN_PASSWORD, "new_password": "NewPass@2026"},
        headers=headers,
    )
    assert resp.status_code == 200

    # Đăng nhập lại với mật khẩu mới
    assert _login(client, "hrofficer@hrms.local", "NewPass@2026").status_code == 200

    # Khôi phục mật khẩu cũ để test khác không bị ảnh hưởng
    headers2 = _bearer(client, "hrofficer@hrms.local", "NewPass@2026")
    client.post(
        f"{BASE}/change-password",
        json={"old_password": "NewPass@2026", "new_password": _ADMIN_PASSWORD},
        headers=headers2,
    )


def test_change_password_wrong_old(client: TestClient):
    headers = _bearer(client, "finance@hrms.local")
    resp = client.post(
        f"{BASE}/change-password",
        json={"old_password": "wrong", "new_password": "Anything@1"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_change_password_too_short(client: TestClient):
    headers = _bearer(client, "finance@hrms.local")
    resp = client.post(
        f"{BASE}/change-password",
        json={"old_password": _ADMIN_PASSWORD, "new_password": "short"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_change_password_requires_auth(client: TestClient):
    resp = client.post(
        f"{BASE}/change-password",
        json={"old_password": "x", "new_password": "y"},
    )
    assert resp.status_code == 401
