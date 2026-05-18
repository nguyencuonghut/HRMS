"""Tests cho 4.3 — Nhắc tái ký: auto-expire task + employee_name trong global list."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.workers.tasks import _expire_overdue_contracts_async

BASE_EMP      = "/api/v1/employees"
BASE_CON      = "/api/v1/contracts"
BASE_REMINDER = "/api/v1/reminders"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_PREFIX         = "TESTRENEWAL"

CAT_LABOR_INDEFINITE = 1
CAT_LABOR_DEFINITE   = 2


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _login(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Session helper ────────────────────────────────────────────────────────────

def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup():
    async with _make_session()() as s:
        await s.execute(text(
            f"DELETE FROM employee_contracts WHERE contract_number LIKE '{_PREFIX}%'"
        ))
        await s.execute(text(
            f"DELETE FROM employees WHERE id_number LIKE '{_PREFIX}%'"
        ))
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await _cleanup()


# ── Setup helpers ──────────────────────────────────────────────────────────────

def _create_employee(client: TestClient, headers: dict, suffix: str) -> int:
    resp = client.post(BASE_EMP, json={
        "full_name": f"Test Renewal {suffix}",
        "last_name": "Test",
        "first_name": f"Renewal {suffix}",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": 1,
        "id_number": f"{_PREFIX}{suffix}",
        "id_issued_on": "2020-01-01",
        "id_issued_by": "Cục CA",
        "status": "official",
        "start_date": "2020-01-01",
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_contract(
    client: TestClient, headers: dict, emp_id: int, suffix: str,
    effective_from: str, effective_to: str | None,
    category_id: int = CAT_LABOR_DEFINITE,
    status: str = "active",
) -> dict:
    resp = client.post(f"{BASE_EMP}/{emp_id}/contracts", json={
        "contract_category_id": category_id,
        "contract_number": f"{_PREFIX}-{suffix}",
        "signed_date": effective_from,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "insurance_salary": "5000000",
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    # Nếu cần set status khác active, cập nhật trực tiếp qua DB
    if status != "active":
        asyncio.run(_set_contract_status(resp.json()["id"], status))
    return resp.json()


async def _set_contract_status(contract_id: int, new_status: str) -> None:
    async with _make_session()() as s:
        await s.execute(text(
            f"UPDATE employee_contracts SET status = '{new_status}' WHERE id = {contract_id}"
        ))
        await s.commit()


async def _get_contract_status(contract_id: int) -> str:
    async with _make_session()() as s:
        result = await s.execute(text(
            f"SELECT status FROM employee_contracts WHERE id = {contract_id}"
        ))
        return result.scalar_one()


# ── Unit tests: Celery expire task ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_expire_overdue_task_marks_status(client: TestClient):
    """HĐ quá hạn (effective_to < today) status=active → bị đổi thành expired."""
    headers = _login(client)
    emp_id = _create_employee(client, headers, "EXP01")
    past = (date.today() - timedelta(days=5)).isoformat()
    c = _create_contract(client, headers, emp_id, "EXP01", past, past)

    assert await _get_contract_status(c["id"]) == "active"

    count = await _expire_overdue_contracts_async()
    assert count >= 1
    assert await _get_contract_status(c["id"]) == "expired"


@pytest.mark.asyncio
async def test_expire_overdue_task_marks_draft(client: TestClient):
    """HĐ quá hạn status=draft cũng bị đổi thành expired."""
    headers = _login(client)
    emp_id = _create_employee(client, headers, "EXP02")
    past = (date.today() - timedelta(days=3)).isoformat()
    c = _create_contract(client, headers, emp_id, "EXP02", past, past)
    await _set_contract_status(c["id"], "draft")

    count = await _expire_overdue_contracts_async()
    assert count >= 1
    assert await _get_contract_status(c["id"]) == "expired"


@pytest.mark.asyncio
async def test_expire_overdue_task_skips_terminated(client: TestClient):
    """HĐ terminated không bị task thay đổi status."""
    headers = _login(client)
    emp_id = _create_employee(client, headers, "EXP03")
    past = (date.today() - timedelta(days=5)).isoformat()
    c = _create_contract(client, headers, emp_id, "EXP03", past, past)
    # Terminate thủ công
    client.delete(f"{BASE_EMP}/{emp_id}/contracts/{c['id']}", headers=headers)

    await _expire_overdue_contracts_async()
    assert await _get_contract_status(c["id"]) == "terminated"


@pytest.mark.asyncio
async def test_expire_overdue_task_skips_indefinite(client: TestClient):
    """HĐ vô thời hạn (effective_to=NULL) không bị ảnh hưởng."""
    headers = _login(client)
    emp_id = _create_employee(client, headers, "EXP04")
    today = date.today().isoformat()
    c = _create_contract(
        client, headers, emp_id, "EXP04", today, None,
        category_id=CAT_LABOR_INDEFINITE,
    )

    await _expire_overdue_contracts_async()
    assert await _get_contract_status(c["id"]) == "active"


@pytest.mark.asyncio
async def test_expire_overdue_task_skips_future_contracts(client: TestClient):
    """HĐ chưa hết hạn (effective_to >= today) không bị ảnh hưởng."""
    headers = _login(client)
    emp_id = _create_employee(client, headers, "EXP05")
    today = date.today().isoformat()
    future = (date.today() + timedelta(days=10)).isoformat()
    c = _create_contract(client, headers, emp_id, "EXP05", today, future)

    await _expire_overdue_contracts_async()
    assert await _get_contract_status(c["id"]) == "active"


@pytest.mark.asyncio
async def test_expire_overdue_task_idempotent(client: TestClient):
    """Chạy task nhiều lần liên tiếp — chạy lần 2 count = 0 (không bị mark lại)."""
    headers = _login(client)
    emp_id = _create_employee(client, headers, "EXP06")
    past = (date.today() - timedelta(days=1)).isoformat()
    _create_contract(client, headers, emp_id, "EXP06", past, past)

    first_run = await _expire_overdue_contracts_async()
    assert first_run >= 1

    second_run = await _expire_overdue_contracts_async()
    assert second_run == 0


# ── Tests: employee_name trong global list ────────────────────────────────────

def test_global_list_includes_employee_name(client: TestClient):
    """GET /contracts trả employee_name và employee_code trong mỗi item."""
    headers = _login(client)
    emp_id = _create_employee(client, headers, "NAME01")
    today = date.today().isoformat()
    _create_contract(client, headers, emp_id, "NAME01", today, None,
                     category_id=CAT_LABOR_INDEFINITE)

    resp = client.get(BASE_CON, params={"keyword": f"{_PREFIX}-NAME01"}, headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) >= 1
    item = items[0]
    assert item["employee_name"] == "Test Renewal NAME01"
    assert item["employee_code"] is not None


def test_global_list_expiring_filter_returns_employee_name(client: TestClient):
    """expiring_within filter vẫn trả employee_name."""
    headers = _login(client)
    emp_id = _create_employee(client, headers, "NAME02")
    today = date.today().isoformat()
    future = (date.today() + timedelta(days=15)).isoformat()
    _create_contract(client, headers, emp_id, "NAME02", today, future)

    resp = client.get(BASE_CON, params={"expiring_within": 30}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    our = next((i for i in items if i["contract_number"] == f"{_PREFIX}-NAME02"), None)
    assert our is not None
    assert our["employee_name"] == "Test Renewal NAME02"
    assert our["days_until_expiry"] is not None
    assert 0 < our["days_until_expiry"] <= 30


# ── Tests: /reminders?types=contract_expiry ───────────────────────────────────

def test_reminder_contract_expiry_in_30d(client: TestClient):
    """GET /reminders?types=contract_expiry&days=30 trả HĐ sắp hết hạn trong 30 ngày."""
    headers = _login(client)
    emp_id = _create_employee(client, headers, "REM01")
    today = date.today().isoformat()
    future = (date.today() + timedelta(days=20)).isoformat()
    _create_contract(client, headers, emp_id, "REM01", today, future)

    resp = client.get(BASE_REMINDER, params={"days": 30, "types": "contract_expiry"}, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    items = body["contract_expiry"]
    our = next((i for i in items if i["employee_name"] == "Test Renewal REM01"), None)
    assert our is not None
    assert our["event_type"] == "contract_expiry"
    assert 0 < our["days_until"] <= 30


def test_reminder_contract_expiry_extra_fields(client: TestClient):
    """Mỗi item trong contract_expiry có extra.contract_number và extra.contract_id."""
    headers = _login(client)
    emp_id = _create_employee(client, headers, "REM02")
    today = date.today().isoformat()
    future = (date.today() + timedelta(days=10)).isoformat()
    con = _create_contract(client, headers, emp_id, "REM02", today, future)

    resp = client.get(BASE_REMINDER, params={"days": 30, "types": "contract_expiry"}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["contract_expiry"]
    our = next((i for i in items if i["employee_name"] == "Test Renewal REM02"), None)
    assert our is not None
    assert our["extra"]["contract_number"] == f"{_PREFIX}-REM02"
    assert our["extra"]["contract_id"] == con["id"]
