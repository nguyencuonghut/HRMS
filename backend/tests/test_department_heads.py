import asyncio
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.auth import AuditLog
from app.models.catalog import Nationality
from app.models.employee import Employee
from app.models.employee_code import EmployeeCodeSequence
from app.models.org import DepartmentHead

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


async def _cleanup_department_head_test_data() -> None:
    async with _make_session()() as session:
        employee_ids = [
            e.id
            for e in (await session.execute(select(Employee))).scalars().all()
            if e.id_number.startswith("TESTDEPTHEAD")
        ]
        if employee_ids:
            await session.execute(
                delete(DepartmentHead).where(DepartmentHead.employee_id.in_(employee_ids))
            )
            await session.execute(
                text("DELETE FROM employee_job_records WHERE employee_id = ANY(:employee_ids)"),
                {"employee_ids": employee_ids},
            )
            await session.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
        await session.execute(
            text(
                """
                DELETE FROM department_heads
                WHERE department_id IN (
                    SELECT id FROM departments
                    WHERE code IN ('TESTHEADA', 'TESTHEADB', 'TESTHEADC')
                )
                """
            )
        )
        await session.execute(
            delete(AuditLog).where(AuditLog.entity_type == "department_head")
        )
        await session.execute(text("DELETE FROM job_positions WHERE code LIKE 'TESTHEADPOS%'"))
        await session.execute(text("DELETE FROM departments WHERE code IN ('TESTHEADA', 'TESTHEADB', 'TESTHEADC')"))
        await session.commit()


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


def _create_department(client: TestClient, *, code: str, name: str, dept_type: str = "PHONG") -> dict:
    resp = client.post(
        BASE,
        json={"code": code, "name": name, "dept_type": dept_type},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_department_head_unique_current_constraint_at_db_level():
    asyncio.run(_cleanup_department_head_test_data())

    async def _run():
        async with _make_session()() as session:
            await session.execute(
                text("INSERT INTO departments (code, name, dept_type, is_active) VALUES ('TESTHEADA', 'Test Head A', 'PHONG', true)")
            )
            await session.execute(
                text("INSERT INTO departments (code, name, dept_type, is_active) VALUES ('TESTHEADB', 'Test Head B', 'PHONG', true)")
            )
            await session.commit()

            dept_id = (
                await session.execute(text("SELECT id FROM departments WHERE code = 'TESTHEADA'"))
            ).scalar_one()
            employee_a = (
                await session.execute(
                    text(
                        """
                        INSERT INTO employees (
                            employee_seq, employee_code_sequence_id, full_name, normalized_name, last_name, first_name,
                            date_of_birth, gender, nationality_id, id_number, id_number_hash, id_issued_on, id_issued_by,
                            status, start_date, is_active
                        )
                        VALUES (
                            990001,
                            (SELECT id FROM employee_code_sequences WHERE code = 'SYS1'),
                            'Test Head Employee A', 'test head employee a', 'Test', 'A',
                            DATE '1990-01-01', 'male',
                            (SELECT id FROM nationalities WHERE code = 'VN'),
                            'TESTDEPTHEADDBA', repeat('a', 64), DATE '2020-01-01', 'CA',
                            'official', DATE '2026-01-01', true
                        )
                        RETURNING id
                        """
                    )
                )
            ).scalar_one()
            employee_b = (
                await session.execute(
                    text(
                        """
                        INSERT INTO employees (
                            employee_seq, employee_code_sequence_id, full_name, normalized_name, last_name, first_name,
                            date_of_birth, gender, nationality_id, id_number, id_number_hash, id_issued_on, id_issued_by,
                            status, start_date, is_active
                        )
                        VALUES (
                            990002,
                            (SELECT id FROM employee_code_sequences WHERE code = 'SYS1'),
                            'Test Head Employee B', 'test head employee b', 'Test', 'B',
                            DATE '1990-01-01', 'male',
                            (SELECT id FROM nationalities WHERE code = 'VN'),
                            'TESTDEPTHEADDBB', repeat('b', 64), DATE '2020-01-01', 'CA',
                            'official', DATE '2026-01-01', true
                        )
                        RETURNING id
                        """
                    )
                )
            ).scalar_one()
            await session.commit()

            session.add(DepartmentHead(
                department_id=dept_id,
                employee_id=employee_a,
                effective_from=date(2026, 1, 1),
                is_current=True,
            ))
            await session.commit()

            session.add(DepartmentHead(
                department_id=dept_id,
                employee_id=employee_b,
                effective_from=date(2026, 2, 1),
                is_current=True,
            ))
            try:
                await session.commit()
                raise AssertionError("expected partial unique index to reject second current head")
            except IntegrityError:
                await session.rollback()

    asyncio.run(_run())
    asyncio.run(_cleanup_department_head_test_data())


def test_department_head_api_supports_cross_department_assignment_and_audit(client: TestClient):
    asyncio.run(_cleanup_department_head_test_data())
    headers = _login(client)

    dept_a = _create_department(client, code="TESTHEADA", name="Test Head A")
    dept_b = _create_department(client, code="TESTHEADB", name="Test Head B")

    position = client.post(
        "/api/v1/job-positions",
        json={
            "code": "TESTHEADPOS1",
            "name": "Giám đốc khối kiểm soát",
            "department_id": dept_a["id"],
        },
    )
    assert position.status_code == 201, position.text

    emp_1 = _create_employee(
        client, headers,
        id_number="TESTDEPTHEAD0001",
        full_name="Test Head One",
    )
    root_job = client.post(
        f"{EMP_BASE}/{emp_1['id']}/job-records",
        json={
            "department_id": dept_a["id"],
            "job_position_id": position.json()["id"],
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert root_job.status_code == 201, root_job.text

    assign_a = client.put(
        f"{BASE}/{dept_a['id']}/head",
        json={
            "employee_id": emp_1["id"],
            "head_role_label": "Trưởng phòng",
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert assign_a.status_code == 200, assign_a.text
    assert assign_a.json()["employee"]["is_cross_department_assignment"] is False
    assert assign_a.json()["display_position_label"] == "Trưởng phòng"

    assign_b = client.put(
        f"{BASE}/{dept_b['id']}/head",
        json={
            "employee_id": emp_1["id"],
            "head_role_label": "Phụ trách",
            "effective_from": "2026-02-01",
        },
        headers=headers,
    )
    assert assign_b.status_code == 200, assign_b.text
    assert assign_b.json()["employee"]["id"] == emp_1["id"]
    assert assign_b.json()["employee"]["is_cross_department_assignment"] is True
    assert assign_b.json()["employee"]["current_department_id"] == dept_a["id"]
    assert assign_b.json()["employee"]["current_job_position_name"] == "Giám đốc khối kiểm soát"

    fetched_b = client.get(f"{BASE}/{dept_b['id']}/head", headers=headers)
    assert fetched_b.status_code == 200, fetched_b.text
    assert fetched_b.json()["employee"]["display_code"]
    assert fetched_b.json()["display_position_label"] == "Phụ trách"

    async def _verify_audit():
        async with _make_session()() as session:
            rows = (
                await session.execute(
                    select(AuditLog)
                    .where(AuditLog.entity_type == "department_head")
                    .order_by(AuditLog.id.asc())
                )
            ).scalars().all()
            assert len(rows) == 2
            assert [row.action for row in rows] == ["CREATE", "CREATE"]

    asyncio.run(_verify_audit())
    asyncio.run(_cleanup_department_head_test_data())


def test_department_head_replace_and_delete_close_current_record_and_log_audit(client: TestClient):
    asyncio.run(_cleanup_department_head_test_data())
    headers = _login(client)

    dept_a = _create_department(client, code="TESTHEADA", name="Test Head A")
    emp_1 = _create_employee(client, headers, id_number="TESTDEPTHEAD0001", full_name="Test Head One")
    emp_2 = _create_employee(client, headers, id_number="TESTDEPTHEAD0002", full_name="Test Head Two")

    first = client.put(
        f"{BASE}/{dept_a['id']}/head",
        json={
            "employee_id": emp_1["id"],
            "head_role_label": "Trưởng phòng",
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert first.status_code == 200, first.text

    second = client.put(
        f"{BASE}/{dept_a['id']}/head",
        json={
            "employee_id": emp_2["id"],
            "head_role_label": "Phụ trách",
            "effective_from": "2026-02-01",
        },
        headers=headers,
    )
    assert second.status_code == 200, second.text

    delete_resp = client.delete(f"{BASE}/{dept_a['id']}/head", headers=headers)
    assert delete_resp.status_code == 200, delete_resp.text

    after_delete = client.get(f"{BASE}/{dept_a['id']}/head", headers=headers)
    assert after_delete.status_code == 200, after_delete.text
    assert after_delete.json() is None

    async def _verify_history():
        async with _make_session()() as session:
            rows = (
                await session.execute(
                    select(DepartmentHead)
                    .where(DepartmentHead.department_id == dept_a["id"])
                    .order_by(DepartmentHead.effective_from.asc(), DepartmentHead.id.asc())
                )
            ).scalars().all()
            assert len(rows) == 2
            assert rows[0].employee_id == emp_1["id"]
            assert rows[0].is_current is False
            assert rows[0].effective_to == date(2026, 1, 31)
            assert rows[1].employee_id == emp_2["id"]
            assert rows[1].is_current is False
            assert rows[1].effective_to == date.today()

            logs = (
                await session.execute(
                    select(AuditLog)
                    .where(AuditLog.entity_type == "department_head")
                    .order_by(AuditLog.id.asc())
                )
            ).scalars().all()
            assert [row.action for row in logs] == ["CREATE", "UPDATE", "DELETE"]

    asyncio.run(_verify_history())
    asyncio.run(_cleanup_department_head_test_data())
