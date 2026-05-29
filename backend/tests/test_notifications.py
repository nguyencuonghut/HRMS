"""Integration & unit tests cho Plan 12.3 — Thông báo & Nhắc việc tự động."""
from __future__ import annotations

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services.notification_service import _render_template

BASE = "/api/v1/notifications"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _bearer(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── Templates ────────────────────────────────────────────────────────────────

def test_list_templates(client: TestClient):
    resp = client.get(f"{BASE}/templates", headers=_bearer(client))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_template_detail(client: TestClient):
    resp = client.get(f"{BASE}/templates/contract_expiry_30d", headers=_bearer(client))
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "contract_expiry_30d"
    assert data["event_type"] == "contract_expiry"


def test_get_template_not_found(client: TestClient):
    resp = client.get(f"{BASE}/templates/nonexistent_template_xyz", headers=_bearer(client))
    assert resp.status_code == 404


def test_update_template(client: TestClient):
    new_subject = "[TEST] Updated subject for contract_expiry_30d"
    resp = client.put(
        f"{BASE}/templates/contract_expiry_30d",
        json={"subject": new_subject},
        headers=_bearer(client),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["subject"] == new_subject
    # Restore original
    client.put(
        f"{BASE}/templates/contract_expiry_30d",
        json={"subject": "[HRMS] Hợp đồng {{employee_name}} sắp hết hạn"},
        headers=_bearer(client),
    )


def test_preview_template(client: TestClient):
    resp = client.post(
        f"{BASE}/templates/contract_expiry_30d/preview",
        json={"sample_data": {"employee_name": "Nguyễn Văn Test", "company_name": "Test Co"}},
        headers=_bearer(client),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "html" in data
    assert "Nguyễn Văn Test" in data["html"]


# ─── Unit test: _render_template ──────────────────────────────────────────────

def test_render_merge_fields_basic():
    result = _render_template("{{name}}", {"name": "X"})
    assert result == "X"


def test_render_merge_fields_multiple():
    result = _render_template("{{a}} và {{b}}", {"a": "foo", "b": "bar"})
    assert result == "foo và bar"


def test_render_merge_fields_missing_key():
    """Nếu key không có trong merge_data, giữ nguyên placeholder."""
    result = _render_template("{{missing}}", {})
    assert result == "{{missing}}"


# ─── Config ───────────────────────────────────────────────────────────────────

def test_list_config(client: TestClient):
    resp = client.get(f"{BASE}/config", headers=_bearer(client))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_update_config(client: TestClient):
    resp = client.put(
        f"{BASE}/config/birthday",
        json={"is_enabled": False},
        headers=_bearer(client),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_enabled"] is False
    # Restore
    client.put(
        f"{BASE}/config/birthday",
        json={"is_enabled": True},
        headers=_bearer(client),
    )


def test_update_config_not_found(client: TestClient):
    resp = client.put(
        f"{BASE}/config/nonexistent_event_xyz",
        json={"is_enabled": False},
        headers=_bearer(client),
    )
    assert resp.status_code == 404


# ─── Logs ─────────────────────────────────────────────────────────────────────

def test_logs_empty_or_list(client: TestClient):
    resp = client.get(f"{BASE}/logs", headers=_bearer(client))
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data


def test_logs_with_filter(client: TestClient):
    resp = client.get(
        f"{BASE}/logs?event_type=birthday&status=sent",
        headers=_bearer(client),
    )
    assert resp.status_code == 200


# ─── Test-send ────────────────────────────────────────────────────────────────

def test_test_send_skipped(client: TestClient):
    """Khi SMTP chưa config (localhost), phải trả 200 với message skipped."""
    resp = client.post(
        f"{BASE}/test-send",
        json={"template_code": "birthday", "recipient_email": "test@example.com"},
        headers=_bearer(client),
    )
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_test_send_missing_template(client: TestClient):
    resp = client.post(
        f"{BASE}/test-send",
        json={"template_code": "nonexistent_xyz", "recipient_email": "test@example.com"},
        headers=_bearer(client),
    )
    assert resp.status_code == 500


# ─── Async helpers for DB-level tests ─────────────────────────────────────────

async def _get_async_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    Session = async_sessionmaker(engine, expire_on_commit=False)
    return engine, Session


# ─── get_pending_notifications — birthday ────────────────────────────────────

@pytest.mark.asyncio
async def test_pending_notifications_birthday():
    """Seed employee sinh nhật hôm nay → get_pending_notifications trả về birthday task."""
    from app.services.notification_service import get_pending_notifications

    engine, Session = await _get_async_session()
    today = date.today()
    emp_id = None
    try:
        async with Session() as session:
            # Tạo employee tạm với ngày sinh = hôm nay — phải điền đủ các cột NOT NULL
            result = await session.execute(
                text("""
                    INSERT INTO employees
                        (employee_seq, employee_code_sequence_id, full_name, normalized_name,
                         last_name, first_name, date_of_birth, is_active, gender,
                         nationality_id, id_number, id_issued_on, id_issued_by,
                         start_date, created_at)
                    VALUES
                        (99999, (SELECT id FROM employee_code_sequences LIMIT 1),
                         'Test Birthday Employee', 'test birthday employee',
                         'Test', 'Birthday', :dob, true, 'male',
                         (SELECT id FROM nationalities LIMIT 1),
                         'ID-TEST-99999', :dob, 'Test',
                         :dob, now())
                    RETURNING id
                """),
                {"dob": today},
            )
            emp_id = result.scalar_one()
            await session.commit()

        async with Session() as session:
            tasks = await get_pending_notifications(session, reference_date=today)
            birthday_tasks = [t for t in tasks if t.event_type == "birthday" and t.employee_id == emp_id]
            assert len(birthday_tasks) >= 1
            assert birthday_tasks[0].template_code == "birthday"
            assert birthday_tasks[0].merge_data["employee_name"] == "Test Birthday Employee"

    finally:
        if emp_id:
            async with Session() as session:
                await session.execute(text("DELETE FROM employees WHERE id = :id"), {"id": emp_id})
                await session.commit()
        await engine.dispose()


# ─── _already_sent_today dedup ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_already_sent_dedup():
    """Insert email_log sent today → _already_sent_today trả True."""
    from app.services.notification_service import _already_sent_today

    engine, Session = await _get_async_session()
    log_id = None
    try:
        async with Session() as session:
            result = await session.execute(
                text("""
                    INSERT INTO email_logs
                        (template_code, event_type, employee_id, recipient_email,
                         recipient_name, subject, status, sent_at)
                    VALUES
                        ('birthday', 'birthday', NULL, 'dedup-test@example.com',
                         'Dedup Test', 'Subject', 'sent', now())
                    RETURNING id
                """)
            )
            log_id = result.scalar_one()
            await session.commit()

        async with Session() as session:
            result = await _already_sent_today(session, "birthday", None)
            assert result is True

    finally:
        if log_id:
            async with Session() as session:
                await session.execute(text("DELETE FROM email_logs WHERE id = :id"), {"id": log_id})
                await session.commit()
        await engine.dispose()


# ─── Unauthenticated → 401 ────────────────────────────────────────────────────

def test_unauthenticated_401(client: TestClient):
    resp = client.get(f"{BASE}/templates")
    assert resp.status_code == 401
