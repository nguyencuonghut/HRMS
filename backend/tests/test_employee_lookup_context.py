import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.catalog import Nationality
from app.models.employee import Employee
from app.models.employee_code import EmployeeCodeSequence

BASE = "/api/v1/employees"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"


def _login(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _get_vn_nationality_id() -> int:
    async with _make_session()() as session:
        nationality = (
            await session.execute(select(Nationality).where(Nationality.code == "VN"))
        ).scalar_one()
        return nationality.id


async def _get_sys1_sequence_id() -> int:
    async with _make_session()() as session:
        sequence = (
            await session.execute(
                select(EmployeeCodeSequence).where(EmployeeCodeSequence.code == "SYS1")
            )
        ).scalar_one()
        return sequence.id


async def _cleanup_lookup_test_data() -> None:
    async with _make_session()() as session:
        employee_ids = [
            e.id
            for e in (await session.execute(select(Employee))).scalars().all()
            if e.id_number.startswith("TESTLOOKUPCTX")
        ]
        if employee_ids:
            await session.execute(
                text("DELETE FROM employee_job_records WHERE employee_id = ANY(:employee_ids)"),
                {"employee_ids": employee_ids},
            )
            await session.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
        await session.commit()


def _get_seeded_job_position(client: TestClient, headers: dict) -> dict:
    resp = client.get("/api/v1/job-positions", params={"is_active": True}, headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert items, "No active job positions in seeded baseline"
    return items[0]


def test_lookup_returns_current_job_context(client: TestClient):
    asyncio.run(_cleanup_lookup_test_data())
    headers = _login(client)
    job_position = _get_seeded_job_position(client, headers)

    dept_resp = client.get("/api/v1/departments", headers=headers)
    assert dept_resp.status_code == 200, dept_resp.text
    dept_payload = dept_resp.json()
    departments = dept_payload["items"] if isinstance(dept_payload, dict) else dept_payload
    department = next((x for x in departments if x["id"] == job_position["department_id"]), None)
    assert department is not None, f"Department '{job_position['department_id']}' not found"

    created = client.post(
        BASE,
        json={
            "employee_code_sequence_id": asyncio.run(_get_sys1_sequence_id()),
            "full_name": "Lookup Context Test",
            "last_name": "Lookup",
            "first_name": "Context Test",
            "date_of_birth": "1990-01-01",
            "gender": "male",
            "nationality_id": asyncio.run(_get_vn_nationality_id()),
            "id_number": "TESTLOOKUPCTX0001",
            "id_issued_on": "2020-01-01",
            "id_issued_by": "Cục Cảnh sát ĐKQLCƯ",
            "status": "official",
            "start_date": "2026-01-01",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    employee_id = created.json()["id"]

    job_resp = client.post(
        f"{BASE}/{employee_id}/job-records",
        json={
            "department_id": department["id"],
            "job_position_id": job_position["id"],
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert job_resp.status_code == 201, job_resp.text

    lookup_resp = client.get(f"{BASE}/lookup?keyword=TESTLOOKUPCTX0001", headers=headers)
    assert lookup_resp.status_code == 200, lookup_resp.text
    found = next(item for item in lookup_resp.json() if item["id"] == employee_id)
    assert found["current_department_id"] == department["id"]
    assert found["current_department_name"] == department["name"]
    assert found["current_job_position_id"] == job_position["id"]
    assert found["current_job_position_name"] == job_position["name"]

    asyncio.run(_cleanup_lookup_test_data())
