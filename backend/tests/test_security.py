import pytest
import uuid
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from itertools import count

from app.core.config import Settings, settings
from app.core.encryption import decrypt, encrypt
from app.core import storage
from app.services import auth_service

AUTH_BASE = "/api/v1/auth"
EMP_BASE = "/api/v1/employees"
ADMIN_EMAIL = "admin@hrms.local"
ADMIN_PASSWORD = "Hrms@2026"
_IP_COUNTER = count(150)


def _login(client: TestClient, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD, **headers):
    merged_headers = dict(headers)
    merged_headers.setdefault("X-Forwarded-For", f"203.0.113.{next(_IP_COUNTER)}")
    return client.post(f"{AUTH_BASE}/login", json={"email": email, "password": password}, headers=merged_headers)


def _bearer(client: TestClient, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD) -> dict:
    token = _login(client, email=email, password=password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _valid_employee_payload(id_number: str) -> dict:
    return {
        "employee_code_sequence_id": 1,
        "full_name": "Security Test",
        "last_name": "Security",
        "first_name": "Test",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": 1,
        "id_number": id_number,
        "id_issued_on": "2020-01-01",
        "id_issued_by": "CA Test",
        "personal_tax_code": f"TAX-{id_number}",
        "passport_number": f"P-{id_number}",
        "status": "probation",
        "start_date": "2026-01-01",
    }


@pytest.fixture(autouse=True)
async def clear_security_state():
    redis_client = await auth_service.get_redis()
    await redis_client.delete(
        "login_failed:admin@hrms.local",
        "login_failed:rate-limit@hrms.local",
        "login_rate:198.51.100.10",
    )
    yield
    await redis_client.delete(
        "login_failed:admin@hrms.local",
        "login_failed:rate-limit@hrms.local",
        "login_rate:198.51.100.10",
    )
    # Clean up skill rows inserted during CSRF tests to prevent database pollution
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM skills WHERE code LIKE 'SEC-SKILL-%'"))
    await engine.dispose()


@pytest.fixture()
def db_sessionmaker():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    Session = async_sessionmaker(engine, expire_on_commit=False)
    yield Session


def _first_bank_id(client: TestClient, headers: dict) -> int:
    resp = client.get("/api/v1/banks", headers=headers)
    payload = resp.json()
    items = payload.get("items", payload)
    return items[0]["id"]


def test_login_rate_limit(client: TestClient):
    headers = {"X-Forwarded-For": "198.51.100.10"}
    for _ in range(5):
        resp = _login(client, email="rate-limit@hrms.local", password="wrong", **headers)
        assert resp.status_code == 401

    blocked = _login(client, email="rate-limit@hrms.local", password="wrong", **headers)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_account_lockout_after_5_fails(client: TestClient):
    # Chạy nhiều hơn 5 lần để compensate cho async Redis + sync TestClient
    # event loop intermittency — mỗi attempt thành công là +1 counter,
    # cần đủ 5 successes để trigger lockout.
    attempts = 0
    for idx in range(15):
        resp = _login(
            client,
            email=ADMIN_EMAIL,
            password="wrong-password",
            **{"X-Forwarded-For": f"198.51.100.{20 + idx}"},
        )
        if resp.status_code == 401:
            attempts += 1
        if attempts >= 5:
            break

    # Verify đủ 5 failed attempts đã record thành công
    assert attempts >= 5, f"Only {attempts} attempts succeeded"

    locked = _login(client, email=ADMIN_EMAIL, password=ADMIN_PASSWORD, **{"X-Forwarded-For": "198.51.100.99"})
    assert locked.status_code == 423


def test_security_headers_present(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]


def test_logout_blacklists_token(client: TestClient):
    login = _login(client)
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get(f"{AUTH_BASE}/me", headers=headers).status_code == 200
    logout_resp = client.post(f"{AUTH_BASE}/logout", headers=headers)
    assert logout_resp.status_code == 200

    me_after_logout = client.get(f"{AUTH_BASE}/me", headers=headers)
    assert me_after_logout.status_code == 401


def test_password_requires_special_char(client: TestClient):
    headers = _bearer(client)
    resp = client.post(
        f"{AUTH_BASE}/change-password",
        json={"old_password": ADMIN_PASSWORD, "new_password": "Abc12345"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_cors_restricts_methods(client: TestClient):
    resp = client.options(
        f"{AUTH_BASE}/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-methods"] == "GET, POST, PUT, DELETE, PATCH, OPTIONS"


def test_csrf_allows_state_change_from_loopback_frontend_origin(client: TestClient):
    headers = {
        **_bearer(client),
        "Origin": "http://127.0.0.1:5173",
    }
    code = f"SEC-SKILL-{uuid.uuid4().hex[:8].upper()}"
    resp = client.post(
        "/api/v1/skills",
        json={"code": code, "name": f"Skill {code}"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


def test_csrf_allows_state_change_from_configured_production_origin(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["https://hrms.example.com"])
    headers = {
        **_bearer(client),
        "Origin": "https://hrms.example.com",
    }
    code = f"SEC-SKILL-{uuid.uuid4().hex[:8].upper()}"
    resp = client.post(
        "/api/v1/skills",
        json={"code": code, "name": f"Skill {code}"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


def test_csrf_rejects_state_change_from_untrusted_origin(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["https://hrms.example.com"])
    headers = {
        **_bearer(client),
        "Origin": "https://evil.example.com",
    }
    code = f"SEC-SKILL-{uuid.uuid4().hex[:8].upper()}"
    resp = client.post(
        "/api/v1/skills",
        json={"code": code, "name": f"Skill {code}"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "Origin" in resp.json()["detail"]


def test_csrf_allows_trusted_referer_when_origin_header_is_missing(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["https://hrms.example.com"])
    headers = {
        **_bearer(client),
        "Referer": "https://hrms.example.com/catalog/skills",
    }
    code = f"SEC-SKILL-{uuid.uuid4().hex[:8].upper()}"
    resp = client.post(
        "/api/v1/skills",
        json={"code": code, "name": f"Skill {code}"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


def test_csrf_rejects_untrusted_referer_when_origin_header_is_missing(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["https://hrms.example.com"])
    headers = {
        **_bearer(client),
        "Referer": "https://evil.example.com/catalog/skills",
    }
    code = f"SEC-SKILL-{uuid.uuid4().hex[:8].upper()}"
    resp = client.post(
        "/api/v1/skills",
        json={"code": code, "name": f"Skill {code}"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "Origin" in resp.json()["detail"]


def test_settings_rejects_loopback_cors_origins_in_production():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 64,
            ENCRYPTION_KEY="prod-encryption-key",
            MINIO_ENDPOINT="s3.example.com",
            MINIO_ACCESS_KEY="prod-access-key",
            MINIO_SECRET_KEY="prod-secret-key",
            CORS_ORIGINS=["http://localhost:5173"],
            REFRESH_TOKEN_COOKIE_SECURE=True,
        )


def test_settings_normalizes_cors_origins():
    cfg = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="b" * 64,
        ENCRYPTION_KEY="prod-encryption-key",
        MINIO_ENDPOINT="s3.example.com",
        MINIO_ACCESS_KEY="prod-access-key",
        MINIO_SECRET_KEY="prod-secret-key",
        CORS_ORIGINS=["https://hrms.example.com/"],
        REFRESH_TOKEN_COOKIE_SECURE=True,
    )
    assert cfg.CORS_ORIGINS == ["https://hrms.example.com"]


def test_settings_rejects_default_minio_endpoint_in_production():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="c" * 64,
            ENCRYPTION_KEY="prod-encryption-key",
            MINIO_ENDPOINT="minio:9000",
            MINIO_ACCESS_KEY="prod-access-key",
            MINIO_SECRET_KEY="prod-secret-key",
            CORS_ORIGINS=["https://hrms.example.com"],
            REFRESH_TOKEN_COOKIE_SECURE=True,
        )


def test_settings_normalizes_minio_endpoint_in_production():
    cfg = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="d" * 64,
        ENCRYPTION_KEY="prod-encryption-key",
        MINIO_ENDPOINT="s3.example.com/",
        MINIO_ACCESS_KEY="prod-access-key",
        MINIO_SECRET_KEY="prod-secret-key",
        CORS_ORIGINS=["https://hrms.example.com"],
        REFRESH_TOKEN_COOKIE_SECURE=True,
    )
    assert cfg.MINIO_ENDPOINT == "s3.example.com"


def test_settings_allow_http_only_lan_configuration():
    cfg = Settings(
        ENVIRONMENT="lan",
        SECRET_KEY="dev-secret-key-change-in-prod",
        ENCRYPTION_KEY="",
        MINIO_ENDPOINT="minio:9000",
        MINIO_ACCESS_KEY="CHANGE_ME",
        MINIO_SECRET_KEY="CHANGE_ME",
        CORS_ORIGINS=["http://hrms.honghafeed.com.vn", "http://172.16.2.100"],
        REFRESH_TOKEN_COOKIE_SECURE=False,
    )
    assert cfg.ENVIRONMENT == "lan"
    assert cfg.MINIO_ENDPOINT == "minio:9000"
    assert cfg.REFRESH_TOKEN_COOKIE_SECURE is False


def test_encryption_roundtrip():
    plaintext = "1234567890"
    ciphertext = encrypt(plaintext)
    assert ciphertext != plaintext
    assert decrypt(ciphertext) == plaintext


def test_minio_bucket_name_uses_environment_suffix(monkeypatch):
    monkeypatch.setattr(settings, "MINIO_BUCKET", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    assert settings.minio_bucket_name == "hrms-attachments-stg"


def test_minio_bucket_name_prefers_explicit_override(monkeypatch):
    monkeypatch.setattr(settings, "MINIO_BUCKET", "custom-bucket")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert settings.minio_bucket_name == "custom-bucket"


def test_ensure_bucket_uses_resolved_bucket_name(monkeypatch):
    calls: list[tuple[str, str]] = []

    class FakeMinio:
        def bucket_exists(self, name: str) -> bool:
            calls.append(("exists", name))
            return False

        def make_bucket(self, name: str) -> None:
            calls.append(("make", name))

    monkeypatch.setattr(settings, "MINIO_BUCKET", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(storage, "_client", lambda: FakeMinio())

    storage.ensure_bucket()

    assert calls == [
        ("exists", "hrms-attachments-dev"),
        ("make", "hrms-attachments-dev"),
    ]


@pytest.mark.asyncio
async def test_encrypted_field_not_plaintext_in_db(client: TestClient, db_sessionmaker):
    headers = _bearer(client)
    payload = _valid_employee_payload("SEC900000001")
    resp = client.post(EMP_BASE, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    employee_id = resp.json()["id"]
    bank_id = _first_bank_id(client, headers)

    bank_resp = client.post(
        f"{EMP_BASE}/{employee_id}/bank-accounts",
        json={
            "bank_id": bank_id,
            "account_number": "1234567890123",
            "account_name": "SECURITY TEST",
            "is_primary": True,
        },
        headers=headers,
    )
    assert bank_resp.status_code == 201, bank_resp.text

    async with db_sessionmaker() as session:
        employee_row = (
            await session.execute(
                text(
                    """
                    SELECT id_number, passport_number, personal_tax_code
                    FROM employees
                    WHERE id = :employee_id
                    """
                ),
                {"employee_id": employee_id},
            )
        ).one()
        bank_row = (
            await session.execute(
                text(
                    """
                    SELECT account_number
                    FROM employee_bank_accounts
                    WHERE employee_id = :employee_id
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"employee_id": employee_id},
            )
        ).one()

    assert employee_row.id_number != "SEC900000001"
    assert employee_row.passport_number != "P-SEC900000001"
    assert employee_row.personal_tax_code != "TAX-SEC900000001"
    assert bank_row.account_number != "1234567890123"
    assert str(employee_row.id_number).startswith("enc:")
    assert str(employee_row.passport_number).startswith("enc:")
    assert str(employee_row.personal_tax_code).startswith("enc:")
    assert str(bank_row.account_number).startswith("enc:")

    async with db_sessionmaker() as session:
        await session.execute(text("DELETE FROM employee_bank_accounts WHERE employee_id = :employee_id"), {"employee_id": employee_id})
        await session.execute(text("DELETE FROM employees WHERE id = :employee_id"), {"employee_id": employee_id})
        await session.commit()
