"""Tests cho module thông tin người thân (3.3)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.employee import Employee
from app.seeds import employees as employees_seed
from app.seeds import other_business_catalog
from app.seeds import employee_relatives as relatives_seed

BASE = "/api/v1/employees"
INSURANCE_BASE = "/api/v1/insurance"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
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
        employee_ids = [e.id for e in (await s.execute(select(Employee))).scalars().all() if e.id_number.startswith("TESTREL")]
        if employee_ids:
            await s.execute(text("DELETE FROM employee_relatives WHERE employee_id = ANY(:employee_ids)"), {"employee_ids": employee_ids})
            await s.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
        await s.commit()


@pytest.fixture(scope="session", autouse=True)
async def seed_data():
    async with _make_session()() as session:
        await other_business_catalog.seed_required_other_business_catalog(session)
        await employees_seed.seed_sample_employees(session)
        await session.flush()
        await relatives_seed.seed_sample_relatives(session)
        await session.commit()
    yield


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await _cleanup_test_employees()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _create_employee(client: TestClient, headers: dict, id_number: str = "TESTREL0000001") -> dict:
    payload = {
        "employee_code_sequence_id": 1,
        "full_name": "Test Relative Viên",
        "last_name": "Test",
        "first_name": "Relative Viên",
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


def _relative_payload(**overrides) -> dict:
    base = {
        "full_name": "Nguyễn Thị Mẫu",
        "relationship_type": "me",
        "phone_number": "0901234567",
        "is_emergency_contact": True,
    }
    return {**base, **overrides}


def _enable_family_health_care(client: TestClient, employee_id: int, headers: dict) -> None:
    response = client.put(
        f"{INSURANCE_BASE}/employees/{employee_id}",
        json={
            "participation_status": "active",
            "insurance_basis_source": "contract",
            "health_care_insurance_code": "CSSK-RELATIVE-TEST",
            "health_care_family_participation": True,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text


# ── List relatives ─────────────────────────────────────────────────────────────

def test_list_relatives_empty(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000002")
    r = client.get(f"{BASE}/{emp['id']}/relatives", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


def test_list_relatives_returns_seed_data(client: TestClient):
    """NV mẫu seq=1 có 2 người thân từ seed."""
    headers = _admin(client)
    r = client.get(BASE, headers=headers, params={"page_size": 100})
    emp_id = next(e["id"] for e in r.json()["items"] if e["display_code"].endswith("0001"))
    relatives = client.get(f"{BASE}/{emp_id}/relatives", headers=headers).json()
    assert len(relatives) >= 2


def test_list_relatives_emergency_contact_first(client: TestClient):
    """is_emergency_contact=True xuất hiện đầu danh sách."""
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000003")
    client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(full_name="Cha", relationship_type="cha", is_emergency_contact=False), headers=headers)
    client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(full_name="Vợ", relationship_type="vo", is_emergency_contact=True), headers=headers)
    relatives = client.get(f"{BASE}/{emp['id']}/relatives", headers=headers).json()
    assert relatives[0]["is_emergency_contact"] is True


def test_list_requires_auth(client: TestClient):
    r = client.get(f"{BASE}/1/relatives")
    assert r.status_code == 401


# ── Create relative ────────────────────────────────────────────────────────────

def test_create_relative_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000010")
    r = client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(), headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["full_name"] == "Nguyễn Thị Mẫu"
    assert data["relationship_type"] == "me"
    assert data["is_emergency_contact"] is True
    assert data["employee_id"] == emp["id"]


def test_create_relative_can_mark_health_care_participation_when_employee_allows(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000010A")
    _enable_family_health_care(client, emp["id"], headers)

    r = client.post(
        f"{BASE}/{emp['id']}/relatives",
        json=_relative_payload(
            relationship_type="con",
            participates_in_health_care_insurance=True,
        ),
        headers=headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["participates_in_health_care_insurance"] is True


def test_create_relative_rejects_health_care_participation_when_employee_not_allowed(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000010B")

    r = client.post(
        f"{BASE}/{emp['id']}/relatives",
        json=_relative_payload(
            relationship_type="con",
            participates_in_health_care_insurance=True,
        ),
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert "CSSK" in r.json()["detail"]


def test_create_relative_invalid_relationship_type(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000011")
    r = client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(relationship_type="ban_than"), headers=headers)
    assert r.status_code == 422


def test_create_relative_multiple_allowed(client: TestClient):
    """Có thể thêm nhiều người thân — không có unique constraint."""
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000012")
    client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(full_name="Con 1", relationship_type="con"), headers=headers)
    client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(full_name="Con 2", relationship_type="con"), headers=headers)
    relatives = client.get(f"{BASE}/{emp['id']}/relatives", headers=headers).json()
    assert len(relatives) == 2


def test_create_relative_requires_edit_perm(client: TestClient):
    headers_admin = _admin(client)
    emp = _create_employee(client, headers_admin, "TESTREL0000013")
    headers_viewer = _viewer(client)
    r = client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(), headers=headers_viewer)
    assert r.status_code == 403


def test_create_relative_writes_audit_log(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000014")
    client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(), headers=headers)
    resp = client.get("/api/v1/audit-logs", headers=headers, params={"entity_type": "employee_relative"}).json()
    logs = resp["items"] if isinstance(resp, dict) else resp
    assert any(log["action"] == "CREATE_RELATIVE" and log["entity_id"] == emp["id"] for log in logs)


# ── Update relative ────────────────────────────────────────────────────────────

def test_update_relative_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000020")
    rel = client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(), headers=headers).json()

    r = client.put(
        f"{BASE}/{emp['id']}/relatives/{rel['id']}",
        json={"full_name": "Tên mới", "occupation": "Bác sĩ"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "Tên mới"
    assert r.json()["occupation"] == "Bác sĩ"
    assert r.json()["relationship_type"] == "me"  # giữ nguyên field không gửi


def test_update_relative_can_toggle_health_care_participation(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000020A")
    _enable_family_health_care(client, emp["id"], headers)
    rel = client.post(
        f"{BASE}/{emp['id']}/relatives",
        json=_relative_payload(
            relationship_type="con",
            participates_in_health_care_insurance=False,
        ),
        headers=headers,
    ).json()

    r = client.put(
        f"{BASE}/{emp['id']}/relatives/{rel['id']}",
        json={"participates_in_health_care_insurance": True},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["participates_in_health_care_insurance"] is True


def test_update_relative_full_payload_with_date_writes_audit_log(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000020B")
    _enable_family_health_care(client, emp["id"], headers)
    rel = client.post(
        f"{BASE}/{emp['id']}/relatives",
        json=_relative_payload(
            full_name="Nguyễn Thị Hồng",
            relationship_type="vo",
            phone_number="0908111222",
            participates_in_health_care_insurance=False,
        ),
        headers=headers,
    ).json()

    payload = {
        "full_name": "Nguyễn Thị Hồng",
        "relationship_type": "vo",
        "date_of_birth": "1988-03-12",
        "occupation": "Kế toán nội bộ",
        "phone_number": "0908111222",
        "participates_in_health_care_insurance": True,
        "is_emergency_contact": True,
        "note": None,
    }
    r = client.put(
        f"{BASE}/{emp['id']}/relatives/{rel['id']}",
        json=payload,
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["participates_in_health_care_insurance"] is True
    assert data["date_of_birth"] == "1988-03-12"

    resp = client.get("/api/v1/audit-logs", headers=headers, params={"entity_type": "employee_relative"}).json()
    logs = resp["items"] if isinstance(resp, dict) else resp
    assert any(
        log["action"] == "UPDATE_RELATIVE"
        and log["entity_id"] == emp["id"]
        and log.get("new_data", {}).get("relative_id") == rel["id"]
        and log.get("new_data", {}).get("date_of_birth") == "1988-03-12"
        for log in logs
    )


def test_update_relative_wrong_employee_404(client: TestClient):
    """PUT với rel_id thuộc nhân viên khác → 404 (IDOR protection)."""
    headers = _admin(client)
    emp1 = _create_employee(client, headers, "TESTREL0000021")
    emp2 = _create_employee(client, headers, "TESTREL0000022")
    rel = client.post(f"{BASE}/{emp1['id']}/relatives", json=_relative_payload(), headers=headers).json()

    r = client.put(
        f"{BASE}/{emp2['id']}/relatives/{rel['id']}",
        json={"full_name": "Hack"},
        headers=headers,
    )
    assert r.status_code == 404


def test_update_relative_writes_audit_log(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000023")
    rel = client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(), headers=headers).json()
    client.put(f"{BASE}/{emp['id']}/relatives/{rel['id']}", json={"full_name": "Cập nhật"}, headers=headers)
    resp = client.get("/api/v1/audit-logs", headers=headers, params={"entity_type": "employee_relative"}).json()
    logs = resp["items"] if isinstance(resp, dict) else resp
    assert any(log["action"] == "UPDATE_RELATIVE" and log["entity_id"] == emp["id"] for log in logs)


# ── Delete relative ────────────────────────────────────────────────────────────

def test_delete_relative_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000030")
    rel = client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(), headers=headers).json()

    r = client.delete(f"{BASE}/{emp['id']}/relatives/{rel['id']}", headers=headers)
    assert r.status_code == 204

    relatives = client.get(f"{BASE}/{emp['id']}/relatives", headers=headers).json()
    assert relatives == []


def test_delete_relative_wrong_employee_404(client: TestClient):
    """DELETE với rel_id thuộc nhân viên khác → 404 (IDOR protection)."""
    headers = _admin(client)
    emp1 = _create_employee(client, headers, "TESTREL0000031")
    emp2 = _create_employee(client, headers, "TESTREL0000032")
    rel = client.post(f"{BASE}/{emp1['id']}/relatives", json=_relative_payload(), headers=headers).json()

    r = client.delete(f"{BASE}/{emp2['id']}/relatives/{rel['id']}", headers=headers)
    assert r.status_code == 404


def test_delete_relative_writes_audit_log(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000033")
    rel = client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(), headers=headers).json()
    client.delete(f"{BASE}/{emp['id']}/relatives/{rel['id']}", headers=headers)
    resp = client.get("/api/v1/audit-logs", headers=headers, params={"entity_type": "employee_relative"}).json()
    logs = resp["items"] if isinstance(resp, dict) else resp
    assert any(log["action"] == "DELETE_RELATIVE" and log["entity_id"] == emp["id"] for log in logs)


# ── GET /employees/{id} includes relatives ─────────────────────────────────────

def test_employee_detail_includes_relatives(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000040")
    client.post(f"{BASE}/{emp['id']}/relatives", json=_relative_payload(), headers=headers)

    detail = client.get(f"{BASE}/{emp['id']}", headers=headers).json()
    assert "relatives" in detail
    assert len(detail["relatives"]) == 1
    assert detail["relatives"][0]["full_name"] == "Nguyễn Thị Mẫu"


def test_employee_detail_no_relatives(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers, "TESTREL0000041")
    detail = client.get(f"{BASE}/{emp['id']}", headers=headers).json()
    assert detail["relatives"] == []
