"""Tests cho module thông tin công việc (3.2)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds import employees as employees_seed
from app.seeds import other_business_catalog
from app.seeds import employee_job_records as job_records_seed

BASE = "/api/v1/employees"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_OFFICER_EMAIL = "hrofficer@hrms.local"
_LINE_MANAGER_EMAIL = "linemanager@hrms.local"


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
        await s.execute(text(
            "DELETE FROM employee_job_records WHERE employee_id IN "
            "(SELECT id FROM employees WHERE id_number LIKE 'TESTJOB%')"
        ))
        await s.execute(text(
            "DELETE FROM employee_bank_accounts WHERE employee_id IN "
            "(SELECT id FROM employees WHERE id_number LIKE 'TESTJOB%')"
        ))
        await s.execute(text("DELETE FROM employees WHERE id_number LIKE 'TESTJOB%'"))
        await s.commit()


@pytest.fixture(scope="session", autouse=True)
async def seed_data():
    async with _make_session()() as session:
        await other_business_catalog.seed_required_other_business_catalog(session)
        await employees_seed.seed_sample_employees(session)
        await session.flush()
        await job_records_seed.seed_sample_job_records(session)
        await session.commit()
    yield


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await _cleanup_test_employees()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _create_employee(client: TestClient, headers: dict, id_number: str = "TESTJOB0000001") -> dict:
    payload = {
        "full_name": "Test Job Viên",
        "last_name": "Test",
        "first_name": "Job Viên",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": 1,
        "id_number": id_number,
        "id_issued_on": "2020-01-01",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ",
        "status": "probation",
        "start_date": "2026-01-01",
    }
    return client.post(BASE, json=payload, headers=headers).json()


def _get_dept_id(client: TestClient, headers: dict, code: str = "HC") -> int:
    r = client.get("/api/v1/departments", headers=headers)
    data = r.json()
    depts = data["items"] if isinstance(data, dict) else data
    for d in depts:
        if d["code"] == code:
            return d["id"]
    pytest.fail(f"Department '{code}' not found")


def _job_record_payload(dept_id: int, *, effective_from: str = "2026-01-01") -> dict:
    return {
        "department_id": dept_id,
        "effective_from": effective_from,
    }


# ── List job records ───────────────────────────────────────────────────────────

def test_list_job_records_empty(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000002")
    r = client.get(f"{BASE}/{emp['id']}/job-records", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


def test_list_job_records_history(client: TestClient):
    """Nhân viên mẫu seq=1 phải có 2 bản ghi (lịch sử KD + hiện tại HC)."""
    headers = _admin(client)
    r = client.get(f"{BASE}", headers=headers, params={"page_size": 100})
    emp_id = next(e["id"] for e in r.json()["items"] if e["display_code"].endswith("0001"))
    records = client.get(f"{BASE}/{emp_id}/job-records", headers=headers).json()
    assert len(records) >= 2
    assert records[0]["is_current"] is True


def test_list_job_records_requires_auth(client: TestClient):
    r = client.get(f"{BASE}/1/job-records")
    assert r.status_code == 401


# ── Create job record ──────────────────────────────────────────────────────────

def test_create_job_record_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000010")
    dept_id = _get_dept_id(client, headers, "HC")

    r = client.post(
        f"{BASE}/{emp['id']}/job-records",
        json=_job_record_payload(dept_id),
        headers=headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["is_current"] is True
    assert data["department"]["id"] == dept_id
    assert data["employee_id"] == emp["id"]


def test_create_job_record_updates_display_code(client: TestClient):
    """Sau khi gán phòng HC (prefix 'HC'), display_code phải có prefix."""
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000011")
    dept_id = _get_dept_id(client, headers, "HC")

    client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(dept_id), headers=headers)

    detail = client.get(f"{BASE}/{emp['id']}", headers=headers).json()
    assert detail["display_code"].startswith("HC")


def test_create_job_record_no_prefix_dept(client: TestClient):
    """Phòng không có display_prefix → display_code chỉ là số."""
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000012")

    # Tìm phòng không có prefix (ví dụ KS chưa được set)
    r = client.get("/api/v1/departments", headers=headers)
    data = r.json()
    depts = data["items"] if isinstance(data, dict) else data
    dept = next((d for d in depts if not d.get("display_prefix")), None)
    if not dept:
        pytest.skip("Tất cả phòng ban đều đã có display_prefix")

    client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(dept["id"]), headers=headers)
    detail = client.get(f"{BASE}/{emp['id']}", headers=headers).json()
    assert detail["display_code"].isdigit()


def test_create_job_record_duplicate_409(client: TestClient):
    """Tạo lần 2 khi đã có is_current → 409."""
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000013")
    dept_id = _get_dept_id(client, headers, "HC")

    client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(dept_id), headers=headers)
    r = client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(dept_id), headers=headers)
    assert r.status_code == 409


def test_create_job_record_official_date_syncs_status(client: TestClient):
    """Khi official_date được set → employees.status = 'official'."""
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000014")
    dept_id = _get_dept_id(client, headers, "HC")

    payload = _job_record_payload(dept_id)
    payload["official_date"] = "2026-04-01"
    client.post(f"{BASE}/{emp['id']}/job-records", json=payload, headers=headers)

    detail = client.get(f"{BASE}/{emp['id']}", headers=headers).json()
    assert detail["status"] == "official"


def test_create_job_record_requires_edit_perm(client: TestClient):
    """Viewer không được tạo job record."""
    headers_admin = _admin(client)
    emp = _create_employee(client, headers_admin, "TESTJOB0000015")
    dept_id = _get_dept_id(client, headers_admin, "HC")

    headers_viewer = _viewer(client)
    r = client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(dept_id), headers=headers_viewer)
    assert r.status_code == 403


def test_create_job_record_writes_audit_log(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000016")
    dept_id = _get_dept_id(client, headers, "HC")

    client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(dept_id), headers=headers)

    resp = client.get("/api/v1/audit-logs", headers=headers, params={"entity_type": "employee_job_record"}).json()
    logs = resp["items"] if isinstance(resp, dict) else resp
    assert any(log["action"] == "CREATE" and log["entity_id"] == emp["id"] for log in logs)


# ── Update current record ──────────────────────────────────────────────────────

def test_update_current_record_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000020")
    dept_id = _get_dept_id(client, headers, "HC")
    client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(dept_id), headers=headers)

    r = client.put(
        f"{BASE}/{emp['id']}/job-records/current",
        json={"notes": "Cập nhật ghi chú"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["notes"] == "Cập nhật ghi chú"
    assert r.json()["is_current"] is True


def test_update_current_record_not_found_404(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000021")
    r = client.put(f"{BASE}/{emp['id']}/job-records/current", json={"notes": "x"}, headers=headers)
    assert r.status_code == 404


def test_update_current_does_not_create_new_record(client: TestClient):
    """Sửa in-place không tạo bản ghi lịch sử mới."""
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000022")
    dept_id = _get_dept_id(client, headers, "HC")
    client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(dept_id), headers=headers)

    client.put(f"{BASE}/{emp['id']}/job-records/current", json={"notes": "sửa"}, headers=headers)
    records = client.get(f"{BASE}/{emp['id']}/job-records", headers=headers).json()
    assert len(records) == 1


# ── Transfer job record ────────────────────────────────────────────────────────

def test_transfer_creates_new_record(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000030")
    hc_id = _get_dept_id(client, headers, "HC")
    kd_id = _get_dept_id(client, headers, "KD")

    client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(hc_id, effective_from="2026-01-01"), headers=headers)
    r = client.post(
        f"{BASE}/{emp['id']}/job-records/transfer",
        json={"department_id": kd_id, "effective_from": "2026-06-01"},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["department"]["id"] == kd_id
    assert r.json()["is_current"] is True

    records = client.get(f"{BASE}/{emp['id']}/job-records", headers=headers).json()
    assert len(records) == 2
    current = next(r for r in records if r["is_current"])
    history = next(r for r in records if not r["is_current"])
    assert current["department"]["id"] == kd_id
    assert history["effective_to"] == "2026-05-31"


def test_transfer_updates_display_code(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000031")
    hc_id = _get_dept_id(client, headers, "HC")
    kd_id = _get_dept_id(client, headers, "KD")

    client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(hc_id), headers=headers)
    detail_before = client.get(f"{BASE}/{emp['id']}", headers=headers).json()
    assert detail_before["display_code"].startswith("HC")

    client.post(
        f"{BASE}/{emp['id']}/job-records/transfer",
        json={"department_id": kd_id, "effective_from": "2026-06-01"},
        headers=headers,
    )
    detail_after = client.get(f"{BASE}/{emp['id']}", headers=headers).json()
    assert detail_after["display_code"].startswith("KD")


def test_transfer_no_current_record_409(client: TestClient):
    """Transfer khi chưa có bản ghi nào → 409."""
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000032")
    kd_id = _get_dept_id(client, headers, "KD")
    r = client.post(
        f"{BASE}/{emp['id']}/job-records/transfer",
        json={"department_id": kd_id, "effective_from": "2026-06-01"},
        headers=headers,
    )
    assert r.status_code == 409


def test_transfer_writes_audit_log(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000033")
    hc_id = _get_dept_id(client, headers, "HC")
    kd_id = _get_dept_id(client, headers, "KD")

    client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(hc_id), headers=headers)
    client.post(
        f"{BASE}/{emp['id']}/job-records/transfer",
        json={"department_id": kd_id, "effective_from": "2026-06-01"},
        headers=headers,
    )

    resp = client.get("/api/v1/audit-logs", headers=headers, params={"entity_type": "employee_job_record"}).json()
    logs = resp["items"] if isinstance(resp, dict) else resp
    assert any(log["action"] == "TRANSFER_JOB_RECORD" and log["entity_id"] == emp["id"] for log in logs)


# ── GET /employees/{id} includes current_job ──────────────────────────────────

def test_employee_detail_includes_current_job(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000040")
    dept_id = _get_dept_id(client, headers, "HC")
    client.post(f"{BASE}/{emp['id']}/job-records", json=_job_record_payload(dept_id), headers=headers)

    detail = client.get(f"{BASE}/{emp['id']}", headers=headers).json()
    assert detail["current_job"] is not None
    assert detail["current_job"]["department"]["id"] == dept_id


def test_employee_detail_no_job_record(client: TestClient):
    """Nhân viên chưa có job record → current_job = null, display_code chỉ là số."""
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTJOB0000041")
    detail = client.get(f"{BASE}/{emp['id']}", headers=headers).json()
    assert detail["current_job"] is None
    assert detail["display_code"].isdigit()
