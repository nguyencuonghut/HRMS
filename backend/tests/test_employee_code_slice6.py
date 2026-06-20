import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.employee import Employee

BASE_EMP = "/api/v1/employees"
BASE_POS = "/api/v1/job-positions"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_PREFIX = "TESTS6"


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
        employee_ids = [e.id for e in (await s.execute(select(Employee))).scalars().all() if e.id_number.startswith(_PREFIX)]
        await s.execute(
            text(
                f"""
                DELETE FROM employee_code_sequence_rules
                WHERE note LIKE '{_PREFIX}%'
                """
            )
        )
        if employee_ids:
            await s.execute(text("DELETE FROM employee_job_records WHERE employee_id = ANY(:employee_ids)"), {"employee_ids": employee_ids})
            await s.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
        await s.execute(text(f"DELETE FROM job_positions WHERE code LIKE '{_PREFIX}%'"))
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await _cleanup()


def _get_department(client: TestClient, headers: dict, code: str) -> dict:
    resp = client.get("/api/v1/departments", headers=headers)
    payload = resp.json()
    items = payload["items"] if isinstance(payload, dict) else payload
    dept = next((item for item in items if item["code"] == code), None)
    assert dept is not None, f"Department '{code}' not found"
    return dept


def _create_position(client: TestClient, headers: dict, dept_id: int, suffix: str) -> dict:
    resp = client.post(
        BASE_POS,
        json={"code": f"{_PREFIX}POS{suffix}", "name": f"Slice6 Pos {suffix}", "department_id": dept_id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_employee(
    client: TestClient,
    headers: dict,
    suffix: str,
    *,
    department_id: int,
    job_position_id: int | None = None,
) -> dict:
    payload = {
        "full_name": f"Slice6 Employee {suffix}",
        "last_name": "Slice6",
        "first_name": suffix,
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": 1,
        "id_number": f"{_PREFIX}{suffix}",
        "id_issued_on": "2020-01-01",
        "id_issued_by": "Cuc Canh sat",
        "status": "probation",
        "start_date": "2026-01-01",
        "initial_department_id": department_id,
        "initial_job_effective_from": "2026-01-01",
    }
    if job_position_id is not None:
        payload["initial_job_position_id"] = job_position_id
    resp = client.post(BASE_EMP, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _set_sequence_min_digits(sequence_code: str, min_digits: int) -> None:
    async with _make_session()() as s:
        await s.execute(
            text(
                """
                UPDATE employee_code_sequences
                SET min_digits = :min_digits
                WHERE code = :sequence_code
                """
            ),
            {"sequence_code": sequence_code, "min_digits": min_digits},
        )
        await s.commit()


async def _get_sequence_min_digits(sequence_code: str) -> int:
    async with _make_session()() as s:
        return (
            await s.execute(
                text(
                    """
                    SELECT min_digits
                    FROM employee_code_sequences
                    WHERE code = :sequence_code
                    """
                ),
                {"sequence_code": sequence_code},
            )
        ).scalar_one()


async def _get_sequence_id(sequence_code: str) -> int:
    async with _make_session()() as s:
        return (
            await s.execute(
                text(
                    """
                    SELECT id
                    FROM employee_code_sequences
                    WHERE code = :sequence_code
                    """
                ),
                {"sequence_code": sequence_code},
            )
        ).scalar_one()


async def _get_employee_sequence_id(employee_id: int) -> int | None:
    async with _make_session()() as s:
        return (
            await s.execute(
                select(Employee.employee_code_sequence_id).where(Employee.id == employee_id)
            )
        ).scalar_one()


async def _insert_department_rule(department_id: int, sequence_code: str, *, note: str) -> None:
    async with _make_session()() as s:
        await s.execute(
            text(
                """
                INSERT INTO employee_code_sequence_rules (
                    scope_type,
                    department_id,
                    employee_code_sequence_id,
                    apply_to_descendants,
                    note,
                    is_active,
                    created_at
                )
                VALUES (
                    'department',
                    :department_id,
                    (SELECT id FROM employee_code_sequences WHERE code = :sequence_code),
                    FALSE,
                    :note,
                    TRUE,
                    now()
                )
                """
            ),
            {"department_id": department_id, "sequence_code": sequence_code, "note": note},
        )
        await s.commit()


async def _insert_job_position_rule(job_position_id: int, sequence_code: str, *, note: str) -> None:
    async with _make_session()() as s:
        await s.execute(
            text(
                """
                INSERT INTO employee_code_sequence_rules (
                    scope_type,
                    job_position_id,
                    employee_code_sequence_id,
                    apply_to_descendants,
                    note,
                    is_active,
                    created_at
                )
                VALUES (
                    'job_position',
                    :job_position_id,
                    (SELECT id FROM employee_code_sequences WHERE code = :sequence_code),
                    FALSE,
                    :note,
                    TRUE,
                    now()
                )
                """
            ),
            {"job_position_id": job_position_id, "sequence_code": sequence_code, "note": note},
        )
        await s.commit()


def _numeric_suffix(display_code: str, prefix: str | None) -> str:
    if prefix and display_code.startswith(prefix):
        return display_code[len(prefix):]
    return display_code


def test_job_position_rule_overrides_department_rule_for_new_employee(client: TestClient):
    headers = _login(client)
    hc = _get_department(client, headers, "HC")
    pos = _create_position(client, headers, hc["id"], "001")

    sys2_id = asyncio.run(_get_sequence_id("SYS2"))
    sys3_id = asyncio.run(_get_sequence_id("SYS3"))
    original_sys2 = asyncio.run(_get_sequence_min_digits("SYS2"))
    original_sys3 = asyncio.run(_get_sequence_min_digits("SYS3"))
    asyncio.run(_set_sequence_min_digits("SYS2", 6))
    asyncio.run(_set_sequence_min_digits("SYS3", 7))
    asyncio.run(_insert_department_rule(hc["id"], "SYS2", note=f"{_PREFIX}-DEPT-RULE"))
    asyncio.run(_insert_job_position_rule(pos["id"], "SYS3", note=f"{_PREFIX}-POS-RULE"))

    try:
        dept_only = _create_employee(client, headers, "EMP001", department_id=hc["id"])
        overridden = _create_employee(client, headers, "EMP002", department_id=hc["id"], job_position_id=pos["id"])

        assert asyncio.run(_get_employee_sequence_id(dept_only["id"])) == sys2_id
        assert asyncio.run(_get_employee_sequence_id(overridden["id"])) == sys3_id
    finally:
        asyncio.run(_set_sequence_min_digits("SYS2", original_sys2))
        asyncio.run(_set_sequence_min_digits("SYS3", original_sys3))


def test_update_job_position_rejects_move_when_active_rule(client: TestClient):
    headers = _login(client)
    hc = _get_department(client, headers, "HC")
    kd = _get_department(client, headers, "KD")
    pos = _create_position(client, headers, hc["id"], "002")
    asyncio.run(_insert_job_position_rule(pos["id"], "SYS2", note=f"{_PREFIX}-ACTIVE-RULE"))

    resp = client.put(f"{BASE_POS}/{pos['id']}", json={"department_id": kd["id"]}, headers=headers)
    assert resp.status_code == 409, resp.text
    assert "rule active" in resp.json()["detail"].lower()


def test_delete_job_position_rejects_when_active_rule(client: TestClient):
    headers = _login(client)
    hc = _get_department(client, headers, "HC")
    pos = _create_position(client, headers, hc["id"], "003")
    asyncio.run(_insert_job_position_rule(pos["id"], "SYS2", note=f"{_PREFIX}-DELETE-RULE"))

    resp = client.delete(f"{BASE_POS}/{pos['id']}", headers=headers)
    assert resp.status_code == 409, resp.text
    assert "rule active" in resp.json()["detail"].lower()


def test_update_job_position_rejects_move_when_current_assignee_exists(client: TestClient):
    headers = _login(client)
    hc = _get_department(client, headers, "HC")
    kd = _get_department(client, headers, "KD")
    pos = _create_position(client, headers, hc["id"], "004")
    _create_employee(client, headers, "EMP004", department_id=hc["id"], job_position_id=pos["id"])

    resp = client.put(f"{BASE_POS}/{pos['id']}", json={"department_id": kd["id"]}, headers=headers)
    assert resp.status_code == 409, resp.text
    assert "đang được gán" in resp.json()["detail"].lower()


def test_delete_job_position_rejects_when_current_assignee_exists(client: TestClient):
    headers = _login(client)
    hc = _get_department(client, headers, "HC")
    pos = _create_position(client, headers, hc["id"], "005")
    _create_employee(client, headers, "EMP005", department_id=hc["id"], job_position_id=pos["id"])

    resp = client.delete(f"{BASE_POS}/{pos['id']}", headers=headers)
    assert resp.status_code == 409, resp.text
    assert "đang được gán" in resp.json()["detail"].lower()
