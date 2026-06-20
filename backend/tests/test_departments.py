import asyncio
import io

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
                text("DELETE FROM department_heads WHERE employee_id = ANY(:employee_ids)"),
                {"employee_ids": employee_ids},
            )
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


def _delete_by_code(client: TestClient, headers: dict, code: str) -> None:
    resp = client.get(BASE, headers=headers)
    assert resp.status_code == 200, resp.text
    for item in resp.json():
        if item["code"] == code:
            delete_resp = client.delete(f"{BASE}/{item['id']}", headers=headers)
            assert delete_resp.status_code == 200, delete_resp.text


def test_create_department_persists_display_prefix(client: TestClient):
    code = "TEST_DEPT_PREFIX_1"
    headers = _login(client)
    _delete_by_code(client, headers, code)

    resp = client.post(
        BASE,
        json={
            "code": code,
            "name": "Test Department Prefix",
            "dept_type": "PHONG",
            "display_prefix": " cnt ",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["display_prefix"] == "CNT"

    _delete_by_code(client, headers, code)


def test_update_department_display_prefix_can_be_changed_and_cleared(client: TestClient):
    code = "TEST_DEPT_PREFIX_2"
    headers = _login(client)
    _delete_by_code(client, headers, code)

    created = client.post(
        BASE,
        json={
            "code": code,
            "name": "Test Department Prefix 2",
            "dept_type": "PHONG",
            "display_prefix": "abc",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    dept_id = created.json()["id"]
    assert created.json()["display_prefix"] == "ABC"

    updated = client.put(
        f"{BASE}/{dept_id}",
        json={"display_prefix": " pk "},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["display_prefix"] == "PK"

    cleared = client.put(
        f"{BASE}/{dept_id}",
        json={"display_prefix": "   "},
        headers=headers,
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["display_prefix"] is None

    _delete_by_code(client, headers, code)


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


def _upload_avatar(client: TestClient, headers: dict, employee_id: int, *, filename: str, content: bytes) -> dict:
    resp = client.post(
        f"{EMP_BASE}/{employee_id}/attachments",
        data={"document_type": "avatar"},
        files={"file": (filename, io.BytesIO(content), "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_department_detail_returns_summary_and_subtree_employees(client: TestClient):
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
        headers=headers,
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
        headers=headers,
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
        headers=headers,
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

    root_head = client.put(
        f"{BASE}/{root_id}/head",
        json={
            "employee_id": root_employee["id"],
            "head_role_label": "Trưởng phòng",
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert root_head.status_code == 200, root_head.text

    child_job = client.post(
        f"{EMP_BASE}/{child_employee['id']}/job-records",
        json={
            "department_id": child_id,
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert child_job.status_code == 201, child_job.text

    detail = client.get(f"{BASE}/{root_id}/detail", headers=headers)
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
    assert len(body["direct_employees"]) == 2
    employees_by_id = {item["id"]: item for item in body["direct_employees"]}

    root_employee_row = employees_by_id[root_employee["id"]]
    assert root_employee_row["full_name"] == "Test Detail Root"
    assert root_employee_row["job_position_name"] == "Test Root Position"
    assert root_employee_row["display_code"].startswith("TR")
    assert root_employee_row["department_id"] == root_id
    assert root_employee_row["department_name"] == "Test Department Root"
    assert root_employee_row["department_dept_type_label"] == "Phòng"

    child_employee_row = employees_by_id[child_employee["id"]]
    assert child_employee_row["full_name"] == "Test Detail Child"
    assert child_employee_row["department_id"] == child_id
    assert child_employee_row["department_name"] == "Test Department Child"
    assert child_employee_row["department_parent_id"] == root_id
    assert child_employee_row["department_dept_type_label"] == "Tổ"

    org_chart = body["org_chart"]
    assert org_chart["department_id"] == root_id
    assert org_chart["department_name"] == "Test Department Root"
    assert org_chart["direct_headcount"] == 1
    assert org_chart["total_headcount"] == 2
    assert org_chart["head"]["employee_id"] == root_employee["id"]
    assert org_chart["head"]["full_name"] == "Test Detail Root"
    assert org_chart["head"]["display_position_label"] == "Trưởng phòng"
    assert org_chart["head"]["avatar_preview_url"] is None
    assert org_chart["head"]["avatar_initials"] == "TR"
    assert len(org_chart["children"]) == 1
    child_node = org_chart["children"][0]
    assert child_node["department_id"] == child_id
    assert child_node["direct_headcount"] == 1
    assert child_node["total_headcount"] == 1
    assert child_node["head"] is None

    asyncio.run(_cleanup_detail_test_data())


def test_department_detail_org_chart_uses_latest_avatar_attachment(client: TestClient):
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
        headers=headers,
    )
    assert root.status_code == 201, root.text
    root_id = root.json()["id"]

    root_employee = _create_employee(
        client,
        headers,
        id_number="TESTDEPTDETAIL0003",
        full_name="Test Detail Avatar",
    )

    root_job = client.post(
        f"{EMP_BASE}/{root_employee['id']}/job-records",
        json={
            "department_id": root_id,
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert root_job.status_code == 201, root_job.text

    root_head = client.put(
        f"{BASE}/{root_id}/head",
        json={
            "employee_id": root_employee["id"],
            "head_role_label": "Trưởng phòng",
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert root_head.status_code == 200, root_head.text

    first_avatar = _upload_avatar(
        client,
        headers,
        root_employee["id"],
        filename="avatar-1.jpg",
        content=b"avatar-1",
    )
    second_avatar = _upload_avatar(
        client,
        headers,
        root_employee["id"],
        filename="avatar-2.jpg",
        content=b"avatar-2",
    )
    assert second_avatar["id"] > first_avatar["id"]

    detail = client.get(f"{BASE}/{root_id}/detail", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()

    avatar_preview_url = body["org_chart"]["head"]["avatar_preview_url"]
    assert avatar_preview_url is not None
    assert f"/api/v1/employees/{root_employee['id']}/attachments/{second_avatar['id']}/preview?token=" in avatar_preview_url

    asyncio.run(_cleanup_detail_test_data())
