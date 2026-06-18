"""Integration tests cho CRUD rule hệ mã nhân viên."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

SEQ_BASE = "/api/v1/employee-code-sequences"
DEPT_BASE = "/api/v1/departments"
POS_BASE = "/api/v1/job-positions"

_DEPT_CODE = "TEST_RULE_DEPT"
_POS_CODE = "TEST_RULE_POS"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"


def _admin(client: TestClient) -> dict:
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
        await s.execute(text("DELETE FROM employee_code_sequence_rules WHERE note LIKE 'TEST_RULE_%'"))
        await s.execute(text("DELETE FROM job_positions WHERE code = :code"), {"code": _POS_CODE})
        await s.execute(text("DELETE FROM departments WHERE code = :code"), {"code": _DEPT_CODE})
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    await _cleanup()
    yield
    await _cleanup()


def _create_department(client: TestClient) -> int:
    resp = client.post(
        DEPT_BASE,
        json={"code": _DEPT_CODE, "name": "Test Rule Dept", "dept_type": "PHONG"},
        headers=_admin(client),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_position(client: TestClient, department_id: int) -> int:
    resp = client.post(
        POS_BASE,
        json={"code": _POS_CODE, "name": "Test Rule Pos", "department_id": department_id},
        headers=_admin(client),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_list_sequences_returns_seeded_systems(client: TestClient):
    resp = client.get(SEQ_BASE, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    codes = [item["code"] for item in resp.json()]
    assert codes == ["SYS1", "SYS2", "SYS3"]


def test_department_rule_crud(client: TestClient):
    headers = _admin(client)
    dept_id = _create_department(client)

    empty = client.get(f"{DEPT_BASE}/{dept_id}/employee-code-rule", headers=headers)
    assert empty.status_code == 200
    assert empty.json() is None

    upsert = client.put(
        f"{DEPT_BASE}/{dept_id}/employee-code-rule",
        json={
            "employee_code_sequence_id": 2,
            "apply_to_descendants": True,
            "note": "TEST_RULE_DEPT_NOTE",
        },
        headers=headers,
    )
    assert upsert.status_code == 200, upsert.text
    assert upsert.json()["employee_code_sequence_code"] == "SYS2"
    assert upsert.json()["apply_to_descendants"] is True

    fetched = client.get(f"{DEPT_BASE}/{dept_id}/employee-code-rule", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["employee_code_sequence_name"] == "Hệ 2"

    deleted = client.delete(f"{DEPT_BASE}/{dept_id}/employee-code-rule", headers=headers)
    assert deleted.status_code == 200
    assert client.get(f"{DEPT_BASE}/{dept_id}/employee-code-rule", headers=headers).json() is None


def test_job_position_rule_crud(client: TestClient):
    headers = _admin(client)
    dept_id = _create_department(client)
    pos_id = _create_position(client, dept_id)

    upsert = client.put(
        f"{POS_BASE}/{pos_id}/employee-code-rule",
        json={
            "employee_code_sequence_id": 3,
            "apply_to_descendants": True,
            "note": "TEST_RULE_POS_NOTE",
        },
        headers=headers,
    )
    assert upsert.status_code == 200, upsert.text
    body = upsert.json()
    assert body["employee_code_sequence_code"] == "SYS3"
    assert body["apply_to_descendants"] is False

    fetched = client.get(f"{POS_BASE}/{pos_id}/employee-code-rule", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["job_position_id"] == pos_id

    deleted = client.delete(f"{POS_BASE}/{pos_id}/employee-code-rule", headers=headers)
    assert deleted.status_code == 200
    assert client.get(f"{POS_BASE}/{pos_id}/employee-code-rule", headers=headers).json() is None


def test_department_rule_rejects_invalid_sequence(client: TestClient):
    dept_id = _create_department(client)
    resp = client.put(
        f"{DEPT_BASE}/{dept_id}/employee-code-rule",
        json={"employee_code_sequence_id": 999999},
        headers=_admin(client),
    )
    assert resp.status_code == 422
