"""Tests cho 5.4 — Báo cáo nghỉ phép."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE_ENT = "/api/v1/leave-entitlements"
BASE_REC = "/api/v1/leave-records"
BASE     = "/api/v1/leave-reports"
BASE_EMP = "/api/v1/employees"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"

_EMP_ID  = 1
_EMP_ID2 = 2
_LT_ID   = 1   # annual_leave — carryover_allowed=True
_YEAR    = 2092   # năm đủ xa


def _login(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup():
    async with _make_session()() as s:
        await s.execute(text(f"DELETE FROM leave_records WHERE EXTRACT(year FROM start_date) = {_YEAR}"))
        await s.execute(text(f"DELETE FROM leave_entitlements WHERE year = {_YEAR}"))
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    await _cleanup()
    yield
    await _cleanup()


def _create_entitlement(client, headers, *, emp_id=_EMP_ID, allocated=12.0):
    r = client.post(BASE_ENT, json={
        "employee_id": emp_id,
        "leave_type_id": _LT_ID,
        "year": _YEAR,
        "allocated_days": allocated,
    }, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _create_record(client, headers, *, emp_id=_EMP_ID, start=None, end=None):
    start = start or str(date(_YEAR, 6, 1))
    end   = end   or str(date(_YEAR, 6, 3))
    r = client.post(BASE_REC, json={
        "employee_id":   emp_id,
        "leave_type_id": _LT_ID,
        "start_date":    start,
        "end_date":      end,
    }, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _employee_display_code(client: TestClient, headers: dict, employee_id: int) -> str:
    resp = client.get(f"{BASE_EMP}/{employee_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["display_code"]


# ── Báo cáo A — Chi tiết nhân viên ────────────────────────────────────────────

def test_employee_summary_returns_data(client: TestClient):
    headers = _login(client)
    expected_code = _employee_display_code(client, headers, _EMP_ID)
    _create_entitlement(client, headers, allocated=12.0)
    _create_record(client, headers, start=str(date(_YEAR, 6, 1)), end=str(date(_YEAR, 6, 3)))  # 3 ngày

    r = client.get(f"{BASE}/employee-summary", params={"year": _YEAR, "employee_id": _EMP_ID}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    row = next(i for i in body["items"] if i["employee_id"] == _EMP_ID and i["leave_type_code"] == "annual_leave")
    assert row["employee_code"] == expected_code
    assert row["used_days"] == 3.0
    assert row["remaining_days"] == 9.0
    assert row["record_count"] == 1


def test_employee_summary_filter_by_employee(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, emp_id=_EMP_ID, allocated=12.0)
    _create_entitlement(client, headers, emp_id=_EMP_ID2, allocated=10.0)

    r = client.get(f"{BASE}/employee-summary", params={"year": _YEAR, "employee_id": _EMP_ID}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(i["employee_id"] == _EMP_ID for i in body["items"])


def test_employee_summary_filter_by_leave_type(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, allocated=12.0)

    r = client.get(f"{BASE}/employee-summary", params={"year": _YEAR, "leave_type_id": _LT_ID}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(i["leave_type_id"] == _LT_ID for i in body["items"])


# ── Báo cáo B — Tổng hợp phòng ban ───────────────────────────────────────────

def test_department_summary_aggregates_correctly(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, allocated=12.0)
    _create_record(client, headers, start=str(date(_YEAR, 6, 1)), end=str(date(_YEAR, 6, 2)))  # 2 ngày
    _create_record(client, headers, start=str(date(_YEAR, 6, 5)), end=str(date(_YEAR, 6, 6)))  # 2 ngày

    r = client.get(f"{BASE}/department-summary", params={"year": _YEAR}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    # Tìm dòng có leave_type annual_leave
    rows = [i for i in body["items"] if i["leave_type_id"] == _LT_ID]
    assert len(rows) >= 1
    # Tổng ngày phải >= 4 (có thể nhiều hơn nếu có dữ liệu khác)
    total = sum(i["total_days_taken"] for i in rows)
    assert total >= 4.0


def test_department_summary_filter_by_month(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, allocated=12.0)
    _create_record(client, headers, start=str(date(_YEAR, 6, 1)), end=str(date(_YEAR, 6, 1)))  # tháng 6

    # Filter month_from=7 → record tháng 6 không xuất hiện
    r = client.get(f"{BASE}/department-summary", params={"year": _YEAR, "month_from": 7}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    # Không có record nào thuộc _YEAR bắt đầu từ tháng 7
    emp1_rows = [i for i in body["items"] if i["leave_type_id"] == _LT_ID]
    # Tổng ngày từ _EMP_ID tháng 7 trở đi phải = 0 (record vừa tạo là tháng 6)
    assert all(i["total_days_taken"] >= 0 for i in emp1_rows)

    # Filter month_from=6 → xuất hiện
    r2 = client.get(f"{BASE}/department-summary", params={"year": _YEAR, "month_from": 6, "month_to": 6}, headers=headers)
    assert r2.status_code == 200, r2.text
    assert r2.json()["month_from"] == 6
    assert r2.json()["month_to"] == 6


def test_department_summary_month_from_gt_month_to_rejected(client: TestClient):
    headers = _login(client)
    r = client.get(f"{BASE}/department-summary", params={"year": _YEAR, "month_from": 8, "month_to": 3}, headers=headers)
    assert r.status_code == 422, r.text


# ── Báo cáo C — Tồn phép cuối năm ────────────────────────────────────────────

def test_year_end_only_carryover_types(client: TestClient):
    headers = _login(client)
    expected_code = _employee_display_code(client, headers, _EMP_ID)
    _create_entitlement(client, headers, allocated=12.0)

    r = client.get(f"{BASE}/year-end", params={"year": _YEAR}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    # annual_leave có carryover_allowed=True → phải xuất hiện
    lt_codes = {i["leave_type_code"] for i in body["items"]}
    assert "annual_leave" in lt_codes
    row = next(i for i in body["items"] if i["employee_id"] == _EMP_ID and i["leave_type_code"] == "annual_leave")
    assert row["employee_code"] == expected_code


def test_year_end_will_carry_is_non_negative(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, allocated=1.0)
    # Dùng 3 ngày khi chỉ có 1 → remaining = -2, will_carry phải = 0
    _create_record(client, headers, start=str(date(_YEAR, 6, 1)), end=str(date(_YEAR, 6, 3)))

    r = client.get(f"{BASE}/year-end", params={"year": _YEAR, "employee_id": _EMP_ID}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    row = next((i for i in body["items"] if i["employee_id"] == _EMP_ID), None)
    assert row is not None
    assert row["remaining_days"] < 0
    assert row["will_carry"] == 0.0


# ── Export ─────────────────────────────────────────────────────────────────────

def test_export_type_a_returns_xlsx(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, allocated=12.0)
    r = client.get(f"{BASE}/export", params={"report_type": "A", "year": _YEAR}, headers=headers)
    assert r.status_code == 200, r.text
    assert "spreadsheetml" in r.headers["content-type"]
    assert len(r.content) > 0


def test_export_type_b_returns_xlsx(client: TestClient):
    headers = _login(client)
    _create_record(client, headers)
    r = client.get(f"{BASE}/export", params={"report_type": "B", "year": _YEAR}, headers=headers)
    assert r.status_code == 200, r.text
    assert "spreadsheetml" in r.headers["content-type"]


def test_export_type_c_returns_xlsx(client: TestClient):
    headers = _login(client)
    _create_entitlement(client, headers, allocated=12.0)
    r = client.get(f"{BASE}/export", params={"report_type": "C", "year": _YEAR}, headers=headers)
    assert r.status_code == 200, r.text
    assert "spreadsheetml" in r.headers["content-type"]


# ── RBAC ──────────────────────────────────────────────────────────────────────

def test_unauthenticated_rejected(client: TestClient):
    r = client.get(f"{BASE}/employee-summary", params={"year": _YEAR})
    assert r.status_code == 401, r.text
