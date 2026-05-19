"""Tests cho 5.3 — Ghi nhận nghỉ phép (LeaveRecord)."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/leave-records"
ENT_BASE = "/api/v1/leave-entitlements"
EMP_BASE = "/api/v1/employees"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_OFFICER_EMAIL  = "hrofficer@hrms.local"

_EMP_ID  = 1   # seed employee — is_active irrelevant for leave_records
_EMP_ID2 = 2
_LT_ID   = 1   # annual_leave (allow_half_day=True)
_LT_SICK = 2   # sick_leave — phải verify allow_half_day

# Năm đủ xa để không đụng dữ liệu thật
_YEAR     = 2091
_ENT_YEAR = _YEAR


def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup_async():
    async with _make_session()() as s:
        await s.execute(text(f"DELETE FROM leave_records WHERE EXTRACT(year FROM start_date) = {_YEAR}"))
        await s.execute(text(f"DELETE FROM leave_entitlements WHERE year = {_ENT_YEAR}"))
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    await _cleanup_async()
    yield
    await _cleanup_async()


def _create_entitlement(client: TestClient, headers: dict, *, allocated: float = 12.0) -> int:
    """Tạo entitlement cho _EMP_ID/_LT_ID/_ENT_YEAR, trả về entitlement id."""
    r = client.post(ENT_BASE, json={
        "employee_id": _EMP_ID,
        "leave_type_id": _LT_ID,
        "year": _ENT_YEAR,
        "allocated_days": allocated,
    }, headers=headers)
    assert r.status_code == 201, f"create entitlement: {r.text}"
    return r.json()["id"]


def _create_record(client: TestClient, headers: dict, **kwargs) -> dict:
    body = {
        "employee_id": _EMP_ID,
        "leave_type_id": _LT_ID,
        "start_date": str(date(_YEAR, 6, 1)),
        "end_date": str(date(_YEAR, 6, 1)),
    }
    body.update(kwargs)
    r = client.post(BASE, json=body, headers=headers)
    return r


def _employee_display_code(client: TestClient, headers: dict, employee_id: int) -> str:
    resp = client.get(f"{EMP_BASE}/{employee_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["display_code"]


# ── Tạo bản ghi ───────────────────────────────────────────────────────────────

def test_create_full_day(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers)
    r = _create_record(client, headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total_days"] == 1.0
    assert body["status"] == "active"
    assert body["warning"] is None


def test_create_half_day_start(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers)
    r = _create_record(client, headers, start_half="PM")
    assert r.status_code == 201, r.text
    assert r.json()["total_days"] == 0.5


def test_create_multi_day_with_halfs(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers)
    r = _create_record(client, headers,
        start_date=str(date(_YEAR, 6, 1)),
        end_date=str(date(_YEAR, 6, 5)),
        start_half="PM",
        end_half="AM",
    )
    assert r.status_code == 201, r.text
    assert r.json()["total_days"] == 4.0


def test_create_updates_used_days(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, allocated=12.0)
    _create_record(client, headers,
        start_date=str(date(_YEAR, 6, 1)),
        end_date=str(date(_YEAR, 6, 3)),
    )
    ent = client.get(ENT_BASE, params={"employee_id": _EMP_ID, "year": _ENT_YEAR}, headers=headers).json()
    assert ent["items"][0]["used_days"] == 3.0
    assert ent["items"][0]["remaining_days"] == 9.0


def test_create_warns_if_no_entitlement(client: TestClient):
    """Không có entitlement → 201 nhưng warning khác null."""
    headers = _login(client)
    # Không tạo entitlement
    r = _create_record(client, headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["warning"] is not None
    assert "phân bổ" in body["warning"].lower()


def test_create_warns_if_overspend(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, allocated=1.0)
    # Nghỉ 3 ngày khi chỉ có 1 ngày
    r = _create_record(client, headers,
        start_date=str(date(_YEAR, 6, 1)),
        end_date=str(date(_YEAR, 6, 3)),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["warning"] is not None
    assert body["remaining_days_after"] < 0


def test_list_records_employee_code_matches_employee_display_code(client: TestClient):
    headers = _login(client)
    expected_code = _employee_display_code(client, headers, _EMP_ID)
    _create_entitlement(client, headers)
    created = _create_record(client, headers)
    assert created.status_code == 201, created.text

    listed = client.get(BASE, params={"employee_id": _EMP_ID, "year": _YEAR}, headers=headers)
    assert listed.status_code == 200, listed.text
    item = next(i for i in listed.json()["items"] if i["id"] == created.json()["id"])
    assert item["employee_code"] == expected_code


def test_create_cross_year_rejected(client: TestClient):
    headers = _login(client)
    r = client.post(BASE, json={
        "employee_id": _EMP_ID,
        "leave_type_id": _LT_ID,
        "start_date": "2025-12-28",
        "end_date": "2026-01-03",
    }, headers=headers)
    assert r.status_code == 422, r.text


def test_create_start_after_end_rejected(client: TestClient):
    headers = _login(client)
    r = client.post(BASE, json={
        "employee_id": _EMP_ID,
        "leave_type_id": _LT_ID,
        "start_date": str(date(_YEAR, 6, 5)),
        "end_date": str(date(_YEAR, 6, 1)),
    }, headers=headers)
    assert r.status_code == 422, r.text


def test_create_half_day_on_no_half_day_type(client: TestClient):
    """leave_type.allow_half_day=False + start_half='PM' → 400."""
    headers = _login(client)
    # Tìm loại phép không cho nửa ngày — kiểm tra sick_leave hoặc tìm cái phù hợp
    lt_list = client.get("/api/v1/leave-types", headers=headers).json()["items"]
    no_half = next((lt for lt in lt_list if not lt["allow_half_day"]), None)
    if no_half is None:
        pytest.skip("Không có loại phép nào có allow_half_day=False trong seed data")

    r = client.post(BASE, json={
        "employee_id": _EMP_ID,
        "leave_type_id": no_half["id"],
        "start_date": str(date(_YEAR, 6, 1)),
        "end_date": str(date(_YEAR, 6, 1)),
        "start_half": "PM",
    }, headers=headers)
    assert r.status_code == 400, r.text


# ── Hủy bản ghi ───────────────────────────────────────────────────────────────

def test_cancel_restores_used_days(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, allocated=12.0)
    record_id = _create_record(client, headers,
        start_date=str(date(_YEAR, 6, 1)),
        end_date=str(date(_YEAR, 6, 3)),
    ).json()["id"]

    # used_days phải = 3.0 sau khi tạo
    ent_before = client.get(ENT_BASE, params={"employee_id": _EMP_ID, "year": _ENT_YEAR}, headers=headers).json()
    assert ent_before["items"][0]["used_days"] == 3.0

    r = client.post(f"{BASE}/{record_id}/cancel", json={"cancel_reason": "Test"}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"

    # used_days phải trở về 0 sau khi hủy
    ent_after = client.get(ENT_BASE, params={"employee_id": _EMP_ID, "year": _ENT_YEAR}, headers=headers).json()
    assert ent_after["items"][0]["used_days"] == 0.0


def test_cancel_already_cancelled(client: TestClient):
    headers = _login(client)
    record_id = _create_record(client, headers).json()["id"]
    client.post(f"{BASE}/{record_id}/cancel", json={}, headers=headers)
    r = client.post(f"{BASE}/{record_id}/cancel", json={}, headers=headers)
    assert r.status_code == 409, r.text


# ── Cập nhật ──────────────────────────────────────────────────────────────────

def test_update_dates_adjusts_used_days(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, allocated=12.0)
    record_id = _create_record(client, headers,
        start_date=str(date(_YEAR, 6, 1)),
        end_date=str(date(_YEAR, 6, 2)),  # 2 ngày
    ).json()["id"]

    # Sửa end_date → 3 ngày
    r = client.put(f"{BASE}/{record_id}", json={
        "end_date": str(date(_YEAR, 6, 3)),
    }, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["total_days"] == 3.0

    ent = client.get(ENT_BASE, params={"employee_id": _EMP_ID, "year": _ENT_YEAR}, headers=headers).json()
    assert ent["items"][0]["used_days"] == 3.0


def test_update_cancelled_record_rejected(client: TestClient):
    headers = _login(client)
    record_id = _create_record(client, headers).json()["id"]
    client.post(f"{BASE}/{record_id}/cancel", json={}, headers=headers)
    r = client.put(f"{BASE}/{record_id}", json={"end_date": str(date(_YEAR, 6, 2))}, headers=headers)
    assert r.status_code == 409, r.text


# ── Xóa ───────────────────────────────────────────────────────────────────────

def test_delete_active_record(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, allocated=12.0)
    record_id = _create_record(client, headers,
        start_date=str(date(_YEAR, 6, 1)),
        end_date=str(date(_YEAR, 6, 2)),
    ).json()["id"]

    r = client.delete(f"{BASE}/{record_id}", headers=headers)
    assert r.status_code == 204, r.text

    # used_days phải về 0
    ent = client.get(ENT_BASE, params={"employee_id": _EMP_ID, "year": _ENT_YEAR}, headers=headers).json()
    assert ent["items"][0]["used_days"] == 0.0


# ── List & Filter ─────────────────────────────────────────────────────────────

def test_list_by_employee(client: TestClient):
    headers = _login(client)
    _create_record(client, headers)
    r = client.get(BASE, params={"employee_id": _EMP_ID}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    assert all(item["employee_id"] == _EMP_ID for item in body["items"])


def test_list_by_year(client: TestClient):
    headers = _login(client)
    _create_record(client, headers)
    r = client.get(BASE, params={"year": _YEAR}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    assert all(item["start_date"].startswith(str(_YEAR)) for item in body["items"])


def test_list_by_status_cancelled(client: TestClient):
    headers = _login(client)
    record_id = _create_record(client, headers).json()["id"]
    client.post(f"{BASE}/{record_id}/cancel", json={}, headers=headers)
    r = client.get(BASE, params={"status": "cancelled", "year": _YEAR}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    assert all(item["status"] == "cancelled" for item in body["items"])


# ── RBAC ──────────────────────────────────────────────────────────────────────

def test_officer_can_create(client: TestClient):
    headers = _login(client, email=_OFFICER_EMAIL, password=_ADMIN_PASSWORD)
    r = _create_record(client, headers)
    assert r.status_code == 201, r.text


def test_unauthenticated_rejected(client: TestClient):
    r = client.get(BASE)
    assert r.status_code == 401, r.text
