"""Integration tests cho Auth endpoints."""
import uuid
from itertools import count

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.requests import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.endpoints import auth as auth_endpoint
from app.core.config import Settings, settings
from app.core.rate_limit import limiter
from app.core.security import create_refresh_token, hash_password

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


@pytest.fixture(autouse=True)
def reset_rate_limit_storage():
    limiter._storage.reset()
    yield
    limiter._storage.reset()


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


def _refresh_via_cookie(client: TestClient):
    """Refresh dùng cookie (cách mới — cookie tự động gửi bởi TestClient session)."""
    return client.post(
        f"{BASE}/refresh",
        headers={"X-Forwarded-For": f"198.18.1.{next(_IP_COUNTER)}"},
    )


def _refresh(client: TestClient, refresh_token: str):
    """Backward-compat: refresh qua body (vẫn được hỗ trợ)."""
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
    assert body["token_type"] == "bearer"
    assert resp.headers.get("content-length") != "0"
    # refresh_token không còn trong body — được set qua HttpOnly cookie
    assert "refresh_token" not in body
    # Cookie được set bởi backend
    assert "refresh_token" in resp.cookies or "Set-Cookie" in str(resp.headers)


def test_login_sets_secure_refresh_cookie_when_enabled(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "REFRESH_TOKEN_COOKIE_SECURE", True)
    resp = _login(client)
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    assert "Secure" in set_cookie


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
    assert "rewards:view" in body["permissions"]
    assert "disciplines:view" in body["permissions"]
    assert "reports:export" in body["permissions"]
    assert "employees:delete" not in body["permissions"]
    assert "users:view" not in body["permissions"]


# ── Refresh ────────────────────────────────────────────────────────────────────

def test_refresh_returns_new_tokens(client: TestClient):
    # Login → cookie được set trong TestClient session
    _login(client)
    # Refresh dùng cookie (browser gửi tự động)
    resp = _refresh_via_cookie(client)
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert resp.headers.get("content-length") != "0"
    me = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200


def test_refresh_rejects_rotated_refresh_token_reuse(client: TestClient):
    login_resp = _login(client)
    refresh_token = login_resp.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    assert refresh_token
    first_refresh = _refresh(client, refresh_token)
    assert first_refresh.status_code == 200
    client.cookies.clear()
    replay_refresh = _refresh(client, refresh_token)
    assert replay_refresh.status_code == 401


def test_refresh_sets_secure_refresh_cookie_when_enabled(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "REFRESH_TOKEN_COOKIE_SECURE", True)
    login_resp = _login(client)
    refresh_token = login_resp.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    assert refresh_token
    resp = _refresh(client, refresh_token)
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    assert "Secure" in set_cookie


def test_refresh_rate_limit_key_uses_refresh_subject_over_proxy_ip():
    refresh_token = create_refresh_token(_ADMIN_EMAIL)
    request = Request(
        {
            "type": "http",
            "headers": [
                (b"cookie", f"{settings.REFRESH_TOKEN_COOKIE_NAME}={refresh_token}".encode()),
                (b"x-forwarded-for", b"172.19.0.4"),
            ],
            "client": ("172.19.0.4", 12345),
        }
    )
    assert auth_endpoint._refresh_rate_limit_key(request) == f"refresh:{_ADMIN_EMAIL}"


def test_refresh_rate_limit_key_falls_back_to_proxy_ip_without_cookie():
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-forwarded-for", b"172.19.0.4, 10.0.0.1")],
            "client": ("172.19.0.4", 12345),
        }
    )
    assert auth_endpoint._refresh_rate_limit_key(request) == "ip:172.19.0.4"


def test_refresh_with_invalid_token_body_fails(client: TestClient):
    # Xóa cookie trước để test body-only path
    client.cookies.clear()
    resp = _refresh(client, "invalid.token.here")
    assert resp.status_code == 401
    # Re-login để các tests sau không bị ảnh hưởng
    _login(client)


def test_refresh_with_no_token_fails(client: TestClient):
    # Không có cookie + không có body → 401
    client.cookies.clear()
    resp = client.post(f"{BASE}/refresh")
    assert resp.status_code == 401
    _login(client)


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


def test_logout_revokes_current_refresh_token(client: TestClient):
    login_resp = _login(client)
    access_token = login_resp.json()["access_token"]
    refresh_token = login_resp.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    assert refresh_token

    logout_resp = client.post(
        f"{BASE}/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 200

    client.cookies.clear()
    refresh_resp = _refresh(client, refresh_token)
    assert refresh_resp.status_code == 401


def test_change_password_revokes_existing_refresh_sessions(
    client: TestClient, reset_officer_password
):
    login_resp = _login(client, _OFFICER_EMAIL, _ADMIN_PASSWORD)
    refresh_token = login_resp.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    assert refresh_token
    access_token = login_resp.json()["access_token"]

    change_resp = client.post(
        f"{BASE}/change-password",
        json={"old_password": _ADMIN_PASSWORD, "new_password": "NewPass@2026"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert change_resp.status_code == 200

    client.cookies.clear()
    refresh_resp = _refresh(client, refresh_token)
    assert refresh_resp.status_code == 401
    assert _login(client, _OFFICER_EMAIL, "NewPass@2026").status_code == 200

    headers2 = _bearer(client, _OFFICER_EMAIL, "NewPass@2026")
    restore_resp = client.post(
        f"{BASE}/change-password",
        json={"old_password": "NewPass@2026", "new_password": _ADMIN_PASSWORD},
        headers=headers2,
    )
    assert restore_resp.status_code == 200


def test_settings_rejects_insecure_refresh_cookie_in_production():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="e" * 64,
            ENCRYPTION_KEY="prod-encryption-key",
            REFRESH_TOKEN_COOKIE_SECURE=False,
            MINIO_ENDPOINT="s3.example.com",
            MINIO_ACCESS_KEY="prod-access-key",
            MINIO_SECRET_KEY="prod-secret-key",
            CORS_ORIGINS=["https://hrms.example.com"],
        )
