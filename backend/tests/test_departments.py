import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.catalog import Nationality
from app.models.employee import Employee
from app.models.employee_code import EmployeeCodeSequence

BASE = "/api/v1/departments"
EMP_BASE = "/api/v1/employees"

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


async def _cleanup_detail_test_data() -> None:
    async with _make_session()() as session:
        employee_ids = [
            e.id
            for e in (await session.execute(select(Employee))).scalars().all()
            if e.id_number.startswith("TESTDEPTDETAIL")
        ]
        if employee_ids:
            await session.execute(
                text("DELETE FROM employee_job_records WHERE employee_id = ANY(:employee_ids)"),
                {"employee_ids": employee_ids},
            )
            await session.execute(
                delete(Employee).where(Employee.id.in_(employee_ids))
            )
        await session.execute(text("DELETE FROM job_positions WHERE code LIKE 'TESTDETPOS%'"))
        await session.execute(text("DELETE FROM departments WHERE code IN ('TESTDEPTROOT', 'TESTDEPTCHILD')"))
        await session.commit()


def _delete_by_code(client: TestClient, code: str) -> None:
    resp = client.get(BASE)
    assert resp.status_code == 200, resp.text
    for item in resp.json():
        if item["code"] == code:
            client.delete(f"{BASE}/{item['id']}")


def test_create_department_persists_display_prefix(client: TestClient):
    code = "TEST_DEPT_PREFIX_1"
    _delete_by_code(client, code)

    resp = client.post(
        BASE,
        json={
            "code": code,
            "name": "Test Department Prefix",
            "dept_type": "PHONG",
            "display_prefix": " cnt ",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["display_prefix"] == "CNT"

    _delete_by_code(client, code)


def test_update_department_display_prefix_can_be_changed_and_cleared(client: TestClient):
    code = "TEST_DEPT_PREFIX_2"
    _delete_by_code(client, code)

    created = client.post(
        BASE,
        json={
            "code": code,
            "name": "Test Department Prefix 2",
            "dept_type": "PHONG",
            "display_prefix": "abc",
        },
    )
    assert created.status_code == 201, created.text
    dept_id = created.json()["id"]
    assert created.json()["display_prefix"] == "ABC"

    updated = client.put(
        f"{BASE}/{dept_id}",
        json={"display_prefix": " pk "},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["display_prefix"] == "PK"

    cleared = client.put(
        f"{BASE}/{dept_id}",
        json={"display_prefix": "   "},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["display_prefix"] is None

    _delete_by_code(client, code)


def _create_employee(client: TestClient, headers: dict, *, id_number: str, full_name: str) -> dict:
    payload = {
        "employee_code_sequence_id": asyncio.run(_get_sys1_sequence_id()),
        "full_name": full_name,
        "last_name": full_name.split()[0],
        "first_name": full_name.split()[-1],
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": asyncio.run(_get_vn_nationality_id()),
        "id_number": id_number,
        "id_issued_on": "2020-01-01",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ",
        "status": "official",
        "start_date": "2026-01-01",
    }
    resp = client.post(EMP_BASE, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_department_detail_returns_summary_and_direct_employees(client: TestClient):
    asyncio.run(_cleanup_detail_test_data())
    headers = _login(client)

    root = client.post(
        BASE,
        json={
            "code": "TESTDEPTROOT",
            "name": "Test Department Root",
            "dept_type": "PHONG",
            "display_prefix": "tr",
        },
    )
    assert root.status_code == 201, root.text
    root_id = root.json()["id"]

    child = client.post(
        BASE,
        json={
            "code": "TESTDEPTCHILD",
            "name": "Test Department Child",
            "dept_type": "TO",
            "parent_id": root_id,
        },
    )
    assert child.status_code == 201, child.text
    child_id = child.json()["id"]

    root_position = client.post(
        "/api/v1/job-positions",
        json={
            "code": "TESTDETPOS1",
            "name": "Test Root Position",
            "department_id": root_id,
        },
    )
    assert root_position.status_code == 201, root_position.text
    root_position_id = root_position.json()["id"]

    root_employee = _create_employee(
        client,
        headers,
        id_number="TESTDEPTDETAIL0001",
        full_name="Test Detail Root",
    )
    child_employee = _create_employee(
        client,
        headers,
        id_number="TESTDEPTDETAIL0002",
        full_name="Test Detail Child",
    )

    root_job = client.post(
        f"{EMP_BASE}/{root_employee['id']}/job-records",
        json={
            "department_id": root_id,
            "job_position_id": root_position_id,
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert root_job.status_code == 201, root_job.text

    child_job = client.post(
        f"{EMP_BASE}/{child_employee['id']}/job-records",
        json={
            "department_id": child_id,
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert child_job.status_code == 201, child_job.text

    detail = client.get(f"{BASE}/{root_id}/detail")
    assert detail.status_code == 200, detail.text
    body = detail.json()

    assert body["department"]["id"] == root_id
    assert body["parent"] is None
    assert body["summary"] == {
        "direct_headcount": 1,
        "total_headcount": 2,
        "direct_child_count": 1,
        "job_position_count": 1,
    }
    assert len(body["direct_employees"]) == 1
    direct_employee = body["direct_employees"][0]
    assert direct_employee["id"] == root_employee["id"]
    assert direct_employee["full_name"] == "Test Detail Root"
    assert direct_employee["job_position_name"] == "Test Root Position"
    assert direct_employee["display_code"].startswith("TR")

    asyncio.run(_cleanup_detail_test_data())
