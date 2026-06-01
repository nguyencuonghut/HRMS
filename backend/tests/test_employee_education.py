"""Tests cho module học vấn & kinh nghiệm (3.4)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.employee import Employee
from app.seeds import employees as employees_seed
from app.seeds import other_business_catalog
from app.seeds import employee_education as education_seed

BASE = "/api/v1/employees"

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
        prefix = "TESTEDU"
        employee_ids = [e.id for e in (await s.execute(select(Employee))).scalars().all() if e.id_number.startswith(prefix)]
        if employee_ids:
            await s.execute(text("DELETE FROM employee_education_histories WHERE employee_id = ANY(:employee_ids)"), {"employee_ids": employee_ids})
            await s.execute(text("DELETE FROM employee_work_experiences WHERE employee_id = ANY(:employee_ids)"), {"employee_ids": employee_ids})
            await s.execute(text("DELETE FROM employee_skills WHERE employee_id = ANY(:employee_ids)"), {"employee_ids": employee_ids})
            await s.execute(text("DELETE FROM employee_certificates WHERE employee_id = ANY(:employee_ids)"), {"employee_ids": employee_ids})
            await s.execute(text("DELETE FROM employee_languages WHERE employee_id = ANY(:employee_ids)"), {"employee_ids": employee_ids})
            await s.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
        await s.commit()


@pytest.fixture(scope="session", autouse=True)
async def seed_data():
    async with _make_session()() as session:
        await other_business_catalog.seed_required_other_business_catalog(session)
        await employees_seed.seed_sample_employees(session)
        await session.flush()
        await education_seed.seed_sample_education(session)
        await session.commit()
    yield


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await _cleanup_test_employees()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _create_employee(client: TestClient, headers: dict, id_number: str = "TESTEDU0000001") -> dict:
    payload = {
        "employee_code_sequence_id": 1,
        "full_name": "Test Education Viên",
        "last_name": "Test",
        "first_name": "Education Viên",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": 1,
        "id_number": id_number,
        "id_issued_on": "2020-01-01",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ",
        "status": "probation",
        "start_date": "2026-01-01",
    }
    resp = client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Education Histories ────────────────────────────────────────────────────────

def test_list_education_empty(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = client.get(f"{BASE}/{emp['id']}/education-histories", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_education_with_institution_fk(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    payload = {
        "institution_id": 1,
        "education_level_id": 6,
        "graduation_year": 2015,
        "is_main_education": True,
    }
    resp = client.post(f"{BASE}/{emp['id']}/education-histories", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["institution_id"] == 1
    assert data["education_level_id"] == 6
    assert data["education_level_name"] == "Đại học"
    assert data["is_main_education"] is True


def test_create_education_no_institution_422(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    payload = {"education_level_id": 6}
    resp = client.post(f"{BASE}/{emp['id']}/education-histories", json=payload, headers=headers)
    assert resp.status_code == 422


def test_update_education_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    edu = client.post(
        f"{BASE}/{emp['id']}/education-histories",
        json={"institution_id": 1, "education_level_id": 6},
        headers=headers,
    ).json()
    resp = client.put(
        f"{BASE}/{emp['id']}/education-histories/{edu['id']}",
        json={"graduation_year": 2018},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["graduation_year"] == 2018


def test_delete_education_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    edu = client.post(
        f"{BASE}/{emp['id']}/education-histories",
        json={"institution_id": 1, "education_level_id": 6},
        headers=headers,
    ).json()
    resp = client.delete(f"{BASE}/{emp['id']}/education-histories/{edu['id']}", headers=headers)
    assert resp.status_code == 204
    listed = client.get(f"{BASE}/{emp['id']}/education-histories", headers=headers).json()
    assert all(e["id"] != edu["id"] for e in listed)


def test_delete_education_wrong_employee_404(client: TestClient):
    headers = _admin(client)
    emp1 = _create_employee(client, headers, "TESTEDU0000001")
    emp2 = _create_employee(client, headers, "TESTEDU0000002")
    edu = client.post(
        f"{BASE}/{emp1['id']}/education-histories",
        json={"institution_id": 1, "education_level_id": 6},
        headers=headers,
    ).json()
    resp = client.delete(f"{BASE}/{emp2['id']}/education-histories/{edu['id']}", headers=headers)
    assert resp.status_code == 404


def test_education_audit_log(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    client.post(
        f"{BASE}/{emp['id']}/education-histories",
        json={"institution_id": 1, "education_level_id": 6},
        headers=headers,
    )
    resp = client.get("/api/v1/audit-logs", headers=headers, params={"entity_type": "employee_education"}).json()
    logs = resp["items"] if isinstance(resp, dict) else resp
    assert any(log["action"] == "CREATE_EDUCATION_HISTORY" and log["entity_id"] == emp["id"] for log in logs)


# ── Work Experiences ───────────────────────────────────────────────────────────

def test_create_work_experience_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    payload = {
        "company_name": "Cty Test ABC",
        "position_name": "Kỹ sư",
        "start_date": "2020-01-01",
        "end_date": "2022-12-31",
    }
    resp = client.post(f"{BASE}/{emp['id']}/work-experiences", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["company_name"] == "Cty Test ABC"
    assert data["end_date"] == "2022-12-31"


def test_create_work_experience_no_end_date(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = client.post(
        f"{BASE}/{emp['id']}/work-experiences",
        json={"company_name": "Cty Hiện Tại", "start_date": "2023-01-01"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["end_date"] is None


def test_update_work_experience_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    exp = client.post(
        f"{BASE}/{emp['id']}/work-experiences",
        json={"company_name": "Cty Test", "start_date": "2020-01-01"},
        headers=headers,
    ).json()
    resp = client.put(
        f"{BASE}/{emp['id']}/work-experiences/{exp['id']}",
        json={"company_name": "Cty Test Updated"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["company_name"] == "Cty Test Updated"


def test_delete_work_experience_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    exp = client.post(
        f"{BASE}/{emp['id']}/work-experiences",
        json={"company_name": "Cty Xóa", "start_date": "2020-01-01"},
        headers=headers,
    ).json()
    resp = client.delete(f"{BASE}/{emp['id']}/work-experiences/{exp['id']}", headers=headers)
    assert resp.status_code == 204


# ── Skills ─────────────────────────────────────────────────────────────────────

def test_create_skill_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = client.post(
        f"{BASE}/{emp['id']}/skills",
        json={"skill_id": 1, "proficiency_level": "advanced"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["skill_id"] == 1
    assert data["proficiency_level"] == "advanced"
    assert data["skill_name"] != ""


def test_create_skill_invalid_proficiency_422(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = client.post(
        f"{BASE}/{emp['id']}/skills",
        json={"skill_id": 1, "proficiency_level": "god_mode"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_create_skill_duplicate_409(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    client.post(
        f"{BASE}/{emp['id']}/skills",
        json={"skill_id": 1, "proficiency_level": "beginner"},
        headers=headers,
    )
    resp = client.post(
        f"{BASE}/{emp['id']}/skills",
        json={"skill_id": 1, "proficiency_level": "expert"},
        headers=headers,
    )
    assert resp.status_code == 409


def test_update_skill_proficiency(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    sk = client.post(
        f"{BASE}/{emp['id']}/skills",
        json={"skill_id": 2, "proficiency_level": "beginner"},
        headers=headers,
    ).json()
    resp = client.put(
        f"{BASE}/{emp['id']}/skills/{sk['id']}",
        json={"proficiency_level": "expert"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["proficiency_level"] == "expert"


# ── Certificates ───────────────────────────────────────────────────────────────

def test_create_certificate_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = client.post(
        f"{BASE}/{emp['id']}/certificates",
        json={"certificate_id": 1},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["certificate_id"] == 1
    assert data["certificate_name"] != ""


def test_create_certificate_with_expiry(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = client.post(
        f"{BASE}/{emp['id']}/certificates",
        json={"certificate_id": 2, "issued_date": "2024-01-01", "expires_on": "2027-01-01"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["issued_date"] == "2024-01-01"
    assert data["expires_on"] == "2027-01-01"


def test_update_certificate_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    cert = client.post(
        f"{BASE}/{emp['id']}/certificates",
        json={"certificate_id": 3},
        headers=headers,
    ).json()
    resp = client.put(
        f"{BASE}/{emp['id']}/certificates/{cert['id']}",
        json={"certificate_number": "CERT-2024-001"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["certificate_number"] == "CERT-2024-001"


# ── Languages ──────────────────────────────────────────────────────────────────

def test_create_language_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = client.post(
        f"{BASE}/{emp['id']}/languages",
        json={"language_name": "Tiếng Anh", "proficiency_level": "B2"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["language_name"] == "Tiếng Anh"
    assert data["proficiency_level"] == "B2"


def test_create_language_invalid_level_422(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = client.post(
        f"{BASE}/{emp['id']}/languages",
        json={"language_name": "Tiếng Anh", "proficiency_level": "D1"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_create_language_duplicate_409(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    client.post(
        f"{BASE}/{emp['id']}/languages",
        json={"language_name": "Tiếng Nhật", "proficiency_level": "A1"},
        headers=headers,
    )
    resp = client.post(
        f"{BASE}/{emp['id']}/languages",
        json={"language_name": "Tiếng Nhật", "proficiency_level": "B1"},
        headers=headers,
    )
    assert resp.status_code == 409


def test_update_language_level(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    lang = client.post(
        f"{BASE}/{emp['id']}/languages",
        json={"language_name": "Tiếng Pháp", "proficiency_level": "A2"},
        headers=headers,
    ).json()
    resp = client.put(
        f"{BASE}/{emp['id']}/languages/{lang['id']}",
        json={"proficiency_level": "B1"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["proficiency_level"] == "B1"


# ── Permissions ────────────────────────────────────────────────────────────────

def test_all_creates_require_edit_perm(client: TestClient):
    admin_headers = _admin(client)
    viewer_headers = _viewer(client)
    emp = _create_employee(client, admin_headers)

    endpoints_and_payloads = [
        (f"{BASE}/{emp['id']}/education-histories", {"institution_id": 1, "education_level_id": 6}),
        (f"{BASE}/{emp['id']}/work-experiences", {"company_name": "Cty", "start_date": "2020-01-01"}),
        (f"{BASE}/{emp['id']}/skills", {"skill_id": 1, "proficiency_level": "beginner"}),
        (f"{BASE}/{emp['id']}/certificates", {"certificate_id": 1}),
        (f"{BASE}/{emp['id']}/languages", {"language_name": "Tiếng Anh", "proficiency_level": "A1"}),
    ]
    for url, payload in endpoints_and_payloads:
        resp = client.post(url, json=payload, headers=viewer_headers)
        assert resp.status_code == 403, f"Expected 403 for {url}, got {resp.status_code}"


# ── Employee detail ────────────────────────────────────────────────────────────

def test_employee_detail_includes_all_education_fields(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)

    client.post(f"{BASE}/{emp['id']}/education-histories",
                json={"institution_id": 1, "education_level_id": 6}, headers=headers)
    client.post(f"{BASE}/{emp['id']}/work-experiences",
                json={"company_name": "Cty ABC", "start_date": "2020-01-01"}, headers=headers)
    client.post(f"{BASE}/{emp['id']}/skills",
                json={"skill_id": 1, "proficiency_level": "advanced"}, headers=headers)
    client.post(f"{BASE}/{emp['id']}/certificates",
                json={"certificate_id": 1}, headers=headers)
    client.post(f"{BASE}/{emp['id']}/languages",
                json={"language_name": "Tiếng Anh", "proficiency_level": "B2"}, headers=headers)

    detail = client.get(f"{BASE}/{emp['id']}", headers=headers).json()
    assert len(detail["education_histories"]) == 1
    assert len(detail["work_experiences"]) == 1
    assert len(detail["skills"]) == 1
    assert len(detail["certificates"]) == 1
    assert len(detail["languages"]) == 1
