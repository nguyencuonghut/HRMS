"""Tests cho module Sự kiện & Nhắc nhở (3.6)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.employee import Employee
from app.seeds import employees as employees_seed

BASE_EMP = "/api/v1/employees"
BASE = "/api/v1/reminders"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_LINE_MANAGER_EMAIL = "linemanager@hrms.local"
_PREFIX = "TESTREM"


def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict:
    token = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient) -> dict:
    return _login(client)


def _viewer(client: TestClient) -> dict:
    return _login(client, _LINE_MANAGER_EMAIL)


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup_test_employees():
    async with _make_session()() as s:
        employee_ids = [e.id for e in (await s.execute(select(Employee))).scalars().all() if e.id_number.startswith(_PREFIX)]
        if employee_ids:
            await s.execute(text("DELETE FROM employee_job_records WHERE employee_id = ANY(:employee_ids)"), {"employee_ids": employee_ids})
            await s.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
        await s.commit()


@pytest.fixture(scope="session", autouse=True)
async def seed_data():
    async with _make_session()() as session:
        await employees_seed.seed_sample_employees(session)
        await session.commit()
    yield


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await _cleanup_test_employees()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_dept_id(client: TestClient, headers: dict) -> int:
    depts = client.get("/api/v1/departments", headers=headers).json()
    items = depts["items"] if isinstance(depts, dict) else depts
    return items[0]["id"]


def _create_employee(
    client: TestClient,
    headers: dict,
    suffix: str,
    *,
    date_of_birth: str = "1990-01-01",
    start_date: str = "2020-01-01",
    status: str = "probation",
) -> dict:
    resp = client.post(BASE_EMP, json={
        "employee_code_sequence_id": 1,
        "full_name":    "Test Reminder",
        "last_name":    "Test",
        "first_name":   "Reminder",
        "date_of_birth": date_of_birth,
        "gender":       "male",
        "nationality_id": 1,
        "id_number":    f"{_PREFIX}{suffix}",
        "id_issued_on": "2020-01-01",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ",
        "status":       status,
        "start_date":   start_date,
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_job_record(
    client: TestClient,
    headers: dict,
    employee_id: int,
    dept_id: int,
    *,
    probation_end_date: str | None = None,
    effective_from: str = "2024-01-01",
) -> dict:
    payload: dict = {
        "department_id":  dept_id,
        "effective_from": effective_from,
    }
    if probation_end_date:
        payload["probation_end_date"] = probation_end_date
    resp = client.post(f"{BASE_EMP}/{employee_id}/job-records", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _isodate(d: date) -> str:
    return d.isoformat()


# ── Auth ───────────────────────────────────────────────────────────────────────

def test_unauthenticated_401(client: TestClient):
    assert client.get(BASE).status_code == 401


def test_viewer_can_access_200(client: TestClient):
    resp = client.get(BASE, headers=_viewer(client))
    assert resp.status_code == 200


# ── Birthday ───────────────────────────────────────────────────────────────────

def test_birthday_today(client: TestClient):
    today = date.today()
    dob = date(today.year - 30, today.month, today.day)
    headers = _admin(client)
    emp = _create_employee(client, headers, "0001", date_of_birth=_isodate(dob))

    data = client.get(BASE, params={"days": 30, "types": "birthday"}, headers=headers).json()
    matches = [e for e in data["birthday"] if e["employee_code"] == emp["display_code"]]
    assert len(matches) == 1
    assert matches[0]["days_until"] == 0


def test_birthday_within_window(client: TestClient):
    today = date.today()
    target = today + timedelta(days=15)
    dob = date(today.year - 25, target.month, target.day)
    headers = _admin(client)
    emp = _create_employee(client, headers, "0002", date_of_birth=_isodate(dob))

    data = client.get(BASE, params={"days": 30, "types": "birthday"}, headers=headers).json()
    matches = [e for e in data["birthday"] if e["employee_code"] == emp["display_code"]]
    assert len(matches) == 1
    assert matches[0]["days_until"] == 15


def test_birthday_outside_window(client: TestClient):
    today = date.today()
    target = today + timedelta(days=31)
    dob = date(today.year - 25, target.month, target.day)
    headers = _admin(client)
    emp = _create_employee(client, headers, "0003", date_of_birth=_isodate(dob))

    data = client.get(BASE, params={"days": 30, "types": "birthday"}, headers=headers).json()
    matches = [e for e in data["birthday"] if e["employee_code"] == emp["display_code"]]
    assert len(matches) == 0


def test_birthday_resigned_excluded(client: TestClient):
    today = date.today()
    dob = date(today.year - 30, today.month, today.day)
    headers = _admin(client)
    emp = _create_employee(client, headers, "0004", date_of_birth=_isodate(dob), status="resigned")

    data = client.get(BASE, params={"days": 30, "types": "birthday"}, headers=headers).json()
    matches = [e for e in data["birthday"] if e["employee_code"] == emp["display_code"]]
    assert len(matches) == 0


# ── Anniversary ────────────────────────────────────────────────────────────────

def test_anniversary_1_year(client: TestClient):
    today = date.today()
    start = date(today.year - 1, today.month, today.day)
    headers = _admin(client)
    emp = _create_employee(client, headers, "0010", start_date=_isodate(start), status="official")

    data = client.get(BASE, params={"days": 30, "types": "anniversary"}, headers=headers).json()
    matches = [e for e in data["anniversary"] if e["employee_code"] == emp["display_code"]]
    assert len(matches) == 1
    assert matches[0]["extra"]["years"] == 1
    assert matches[0]["days_until"] == 0


def test_anniversary_multiple_milestones(client: TestClient):
    """Nhân viên 3 năm và nhân viên 5 năm — mỗi người 1 item."""
    today = date.today()
    headers = _admin(client)
    start3 = date(today.year - 3, today.month, today.day)
    start5 = date(today.year - 5, today.month, today.day)
    emp3 = _create_employee(client, headers, "0011", start_date=_isodate(start3), status="official")
    emp5 = _create_employee(client, headers, "0012", start_date=_isodate(start5), status="official")

    data = client.get(BASE, params={"days": 30, "types": "anniversary"}, headers=headers).json()
    codes = {e["employee_code"]: e["extra"]["years"] for e in data["anniversary"]}
    assert codes.get(emp3["display_code"]) == 3
    assert codes.get(emp5["display_code"]) == 5


def test_anniversary_not_a_milestone(client: TestClient):
    """2 năm không phải mốc → không xuất hiện."""
    today = date.today()
    start = date(today.year - 2, today.month, today.day)
    headers = _admin(client)
    emp = _create_employee(client, headers, "0013", start_date=_isodate(start), status="official")

    data = client.get(BASE, params={"days": 30, "types": "anniversary"}, headers=headers).json()
    matches = [e for e in data["anniversary"] if e["employee_code"] == emp["display_code"]]
    assert len(matches) == 0


def test_anniversary_outside_window(client: TestClient):
    today = date.today()
    target = today + timedelta(days=31)
    start = date(today.year - 1, target.month, target.day)
    headers = _admin(client)
    emp = _create_employee(client, headers, "0014", start_date=_isodate(start), status="official")

    data = client.get(BASE, params={"days": 30, "types": "anniversary"}, headers=headers).json()
    matches = [e for e in data["anniversary"] if e["employee_code"] == emp["display_code"]]
    assert len(matches) == 0


# ── Probation end ──────────────────────────────────────────────────────────────

def test_probation_end_within_window(client: TestClient):
    today = date.today()
    end_date = today + timedelta(days=7)
    headers = _admin(client)
    emp = _create_employee(client, headers, "0020", status="probation")
    dept_id = _get_dept_id(client, headers)
    _create_job_record(client, headers, emp["id"], dept_id, probation_end_date=_isodate(end_date))

    data = client.get(BASE, params={"days": 30, "types": "probation_end"}, headers=headers).json()
    matches = [e for e in data["probation_end"] if e["employee_id"] == emp["id"]]
    assert len(matches) == 1
    assert matches[0]["days_until"] == 7


def test_probation_end_today(client: TestClient):
    today = date.today()
    headers = _admin(client)
    emp = _create_employee(client, headers, "0021", status="probation")
    dept_id = _get_dept_id(client, headers)
    _create_job_record(client, headers, emp["id"], dept_id, probation_end_date=_isodate(today))

    data = client.get(BASE, params={"days": 30, "types": "probation_end"}, headers=headers).json()
    matches = [e for e in data["probation_end"] if e["employee_id"] == emp["id"]]
    assert len(matches) == 1
    assert matches[0]["days_until"] == 0


def test_probation_end_outside_window(client: TestClient):
    today = date.today()
    end_date = today + timedelta(days=31)
    headers = _admin(client)
    emp = _create_employee(client, headers, "0022", status="probation")
    dept_id = _get_dept_id(client, headers)
    _create_job_record(client, headers, emp["id"], dept_id, probation_end_date=_isodate(end_date))

    data = client.get(BASE, params={"days": 30, "types": "probation_end"}, headers=headers).json()
    matches = [e for e in data["probation_end"] if e["employee_id"] == emp["id"]]
    assert len(matches) == 0


def test_probation_end_official_excluded(client: TestClient):
    """Nhân viên đã chính thức (status=official) không xuất hiện dù có probation_end_date."""
    today = date.today()
    end_date = today + timedelta(days=5)
    headers = _admin(client)
    emp = _create_employee(client, headers, "0023", status="official")
    dept_id = _get_dept_id(client, headers)
    _create_job_record(client, headers, emp["id"], dept_id, probation_end_date=_isodate(end_date))

    data = client.get(BASE, params={"days": 30, "types": "probation_end"}, headers=headers).json()
    matches = [e for e in data["probation_end"] if e["employee_id"] == emp["id"]]
    assert len(matches) == 0


# ── Filter by type ─────────────────────────────────────────────────────────────

def test_filter_birthday_only(client: TestClient):
    headers = _admin(client)
    data = client.get(BASE, params={"days": 30, "types": "birthday"}, headers=headers).json()
    assert "birthday"      in data
    assert "anniversary"   in data
    assert "probation_end" in data
    assert len(data["anniversary"])   == 0
    assert len(data["probation_end"]) == 0


def test_filter_multiple_types(client: TestClient):
    headers = _admin(client)
    data = client.get(BASE, params={"days": 30, "types": "birthday,probation_end"}, headers=headers).json()
    assert len(data["anniversary"]) == 0


def test_invalid_type_ignored_returns_all(client: TestClient):
    """Loại không hợp lệ bị bỏ qua → fallback trả tất cả."""
    headers = _admin(client)
    data = client.get(BASE, params={"days": 30, "types": "invalid_type"}, headers=headers).json()
    assert "birthday"      in data
    assert "anniversary"   in data
    assert "probation_end" in data


# ── Days param ────────────────────────────────────────────────────────────────

def test_days_param_7_excludes_15_day_event(client: TestClient):
    today = date.today()
    target = today + timedelta(days=15)
    dob = date(today.year - 25, target.month, target.day)
    headers = _admin(client)
    emp = _create_employee(client, headers, "0030", date_of_birth=_isodate(dob))

    data = client.get(BASE, params={"days": 7, "types": "birthday"}, headers=headers).json()
    matches = [e for e in data["birthday"] if e["employee_code"] == emp["display_code"]]
    assert len(matches) == 0


def test_days_param_out_of_range(client: TestClient):
    headers = _admin(client)
    assert client.get(BASE, params={"days": 0},  headers=headers).status_code == 422
    assert client.get(BASE, params={"days": 91}, headers=headers).status_code == 422


# ── Response structure ────────────────────────────────────────────────────────

def test_response_has_total(client: TestClient):
    headers = _admin(client)
    data = client.get(BASE, headers=headers).json()
    assert "total" in data
    total = data["total"]
    computed = (
        len(data["birthday"])
        + len(data["anniversary"])
        + len(data["probation_end"])
        + len(data["contract_expiry"])
    )
    assert total == computed


def test_sorted_by_days_until(client: TestClient):
    today = date.today()
    headers = _admin(client)
    # Tạo 2 nhân viên: birthday sau 10 ngày và 5 ngày
    t1 = today + timedelta(days=10)
    t2 = today + timedelta(days=5)
    emp1 = _create_employee(client, headers, "0040", date_of_birth=_isodate(date(today.year - 25, t1.month, t1.day)))
    emp2 = _create_employee(client, headers, "0041", date_of_birth=_isodate(date(today.year - 25, t2.month, t2.day)))

    data = client.get(BASE, params={"days": 30, "types": "birthday"}, headers=headers).json()
    expected_codes = {emp1["display_code"], emp2["display_code"]}
    test_items = [e for e in data["birthday"] if e["employee_code"] in expected_codes]
    if len(test_items) >= 2:
        assert test_items[0]["days_until"] <= test_items[1]["days_until"]
