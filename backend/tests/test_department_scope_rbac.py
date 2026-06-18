from __future__ import annotations

from datetime import date
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.auth import User, UserRole
from app.models.employee import Employee
from app.models.org import Department

BASE_EMP = "/api/v1/employees"
BASE_DEPT = "/api/v1/departments"
BASE_USERS = "/api/v1/users"
BASE_ROLES = "/api/v1/roles"
BASE_LEAVE_ENT = "/api/v1/leave-entitlements"
BASE_LEAVE_REC = "/api/v1/leave-records"
BASE_KPI = "/api/v1/performance/kpi"
BASE_REVIEWS = "/api/v1/performance/yearly-reviews"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_PREFIX = f"SCRB{uuid.uuid4().hex[:6].upper()}"


def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict[str, str]:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    async with _make_session()() as s:
        employee_ids = list(
            (
                await s.execute(
                    select(Employee.id).where(
                        Employee.personal_email.like(f"{_PREFIX.lower()}%@example.com")
                    )
                )
            )
            .scalars()
            .all()
        )
        if employee_ids:
            await s.execute(
                text("DELETE FROM leave_records WHERE employee_id = ANY(:employee_ids)"),
                {"employee_ids": employee_ids},
            )
            await s.execute(
                text("DELETE FROM leave_entitlements WHERE employee_id = ANY(:employee_ids)"),
                {"employee_ids": employee_ids},
            )
            await s.execute(
                text("DELETE FROM employee_kpi_monthly WHERE employee_id = ANY(:employee_ids)"),
                {"employee_ids": employee_ids},
            )
            await s.execute(
                text("DELETE FROM employee_yearly_reviews WHERE employee_id = ANY(:employee_ids)"),
                {"employee_ids": employee_ids},
            )
            await s.execute(
                text("DELETE FROM employee_job_records WHERE employee_id = ANY(:employee_ids)"),
                {"employee_ids": employee_ids},
            )
            await s.execute(delete(Employee).where(Employee.id.in_(employee_ids)))

        user_ids = list(
            (
                await s.execute(
                    select(User.id).where(User.email.like(f"{_PREFIX.lower()}%@example.com"))
                )
            )
            .scalars()
            .all()
        )
        if user_ids:
            await s.execute(
                delete(UserRole).where(UserRole.user_id.in_(user_ids))
            )
            await s.execute(delete(User).where(User.id.in_(user_ids)))

        dept_ids = list(
            (
                await s.execute(
                    select(Department.id).where(Department.code.like(f"{_PREFIX}%"))
                )
            )
            .scalars()
            .all()
        )
        if dept_ids:
            await s.execute(
                text("DELETE FROM employee_job_records WHERE department_id = ANY(:dept_ids)"),
                {"dept_ids": dept_ids},
            )
            await s.execute(delete(Department).where(Department.id.in_(dept_ids)))

        await s.commit()


def _create_department(client: TestClient, headers: dict[str, str], *, code: str, name: str, parent_id: int | None = None) -> dict:
    payload = {"code": code, "name": name, "dept_type": "PHONG"}
    if parent_id is not None:
        payload["parent_id"] = parent_id
        payload["dept_type"] = "BO_PHAN"
    resp = client.post(BASE_DEPT, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_employee(
    client: TestClient,
    headers: dict[str, str],
    *,
    suffix: str,
    full_name: str,
    department_id: int,
) -> dict:
    resp = client.post(
        BASE_EMP,
        json={
            "employee_code_sequence_id": 1,
            "full_name": full_name,
            "last_name": full_name.split()[0],
            "first_name": full_name.split()[-1],
            "date_of_birth": "1990-01-01",
            "gender": "male",
            "nationality_id": 1,
            "id_number": f"{_PREFIX}{suffix}",
            "id_issued_on": "2020-01-01",
            "id_issued_by": "CA Test",
            "status": "official",
            "start_date": "2026-01-01",
            "personal_email": f"{_PREFIX.lower()}{suffix}@example.com",
            "initial_department_id": department_id,
            "initial_job_effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_scoped_line_manager(
    client: TestClient,
    admin_headers: dict[str, str],
    *,
    department_ids: list[int],
) -> dict[str, str]:
    email = f"{_PREFIX.lower()}lm@example.com"
    user_resp = client.post(
        BASE_USERS,
        json={
            "email": email,
            "full_name": f"{_PREFIX} Line Manager",
            "password": "LineMgr@1234",
        },
        headers=admin_headers,
    )
    assert user_resp.status_code == 201, user_resp.text
    user = user_resp.json()

    roles_resp = client.get(BASE_ROLES, headers=admin_headers)
    assert roles_resp.status_code == 200, roles_resp.text
    line_manager_role = next(role for role in roles_resp.json() if role["code"] == "line_manager")

    assign_resp = client.post(
        f"{BASE_USERS}/{user['id']}/roles",
        json={
            "role_id": line_manager_role["id"],
            "scope_type": "department",
            "department_ids": department_ids,
        },
        headers=admin_headers,
    )
    assert assign_resp.status_code == 201, assign_resp.text
    return _login(client, email, "LineMgr@1234")


def _create_leave_entitlement(
    client: TestClient,
    headers: dict[str, str],
    *,
    employee_id: int,
    year: int,
    allocated_days: float = 12.0,
) -> dict:
    resp = client.post(
        BASE_LEAVE_ENT,
        json={
            "employee_id": employee_id,
            "leave_type_id": 1,
            "year": year,
            "allocated_days": allocated_days,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_leave_record(
    client: TestClient,
    headers: dict[str, str],
    *,
    employee_id: int,
    year: int,
) -> dict:
    resp = client.post(
        BASE_LEAVE_REC,
        json={
            "employee_id": employee_id,
            "leave_type_id": 1,
            "start_date": str(date(year, 6, 1)),
            "end_date": str(date(year, 6, 1)),
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_kpi(
    client: TestClient,
    headers: dict[str, str],
    *,
    employee_id: int,
    year: int,
    month: int,
    score: float,
) -> dict:
    resp = client.post(
        BASE_KPI,
        json={
            "employee_id": employee_id,
            "year": year,
            "month": month,
            "score": score,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_yearly_review(
    client: TestClient,
    headers: dict[str, str],
    *,
    employee_id: int,
    year: int,
    rating: str = "tot",
) -> dict:
    resp = client.post(
        BASE_REVIEWS,
        json={
            "employee_id": employee_id,
            "year": year,
            "rating": rating,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_scoped_line_manager_only_sees_assigned_departments_and_employees(client: TestClient):
    admin_headers = _login(client)
    root = _create_department(client, admin_headers, code=f"{_PREFIX}_ROOT", name=f"{_PREFIX} Root")
    child = _create_department(
        client,
        admin_headers,
        code=f"{_PREFIX}_CHILD",
        name=f"{_PREFIX} Child",
        parent_id=root["id"],
    )
    outside = _create_department(client, admin_headers, code=f"{_PREFIX}_OUT", name=f"{_PREFIX} Outside")

    visible_emp = _create_employee(
        client,
        admin_headers,
        suffix="001",
        full_name=f"{_PREFIX} Visible",
        department_id=child["id"],
    )
    hidden_emp = _create_employee(
        client,
        admin_headers,
        suffix="002",
        full_name=f"{_PREFIX} Hidden",
        department_id=outside["id"],
    )

    manager_headers = _create_scoped_line_manager(
        client,
        admin_headers,
        department_ids=[root["id"]],
    )

    dept_resp = client.get(BASE_DEPT, headers=manager_headers)
    assert dept_resp.status_code == 200, dept_resp.text
    dept_codes = {item["code"] for item in dept_resp.json()}
    assert dept_codes == {root["code"], child["code"]}

    tree_resp = client.get(f"{BASE_DEPT}/tree", headers=manager_headers)
    assert tree_resp.status_code == 200, tree_resp.text
    tree = tree_resp.json()
    assert len(tree) == 1
    assert tree[0]["id"] == root["id"]
    assert [node["id"] for node in tree[0]["children"]] == [child["id"]]

    employees_resp = client.get(
        BASE_EMP,
        params={"keyword": _PREFIX},
        headers=manager_headers,
    )
    assert employees_resp.status_code == 200, employees_resp.text
    employee_names = {item["full_name"] for item in employees_resp.json()["items"]}
    assert employee_names == {visible_emp["full_name"]}

    assert client.get(f"{BASE_EMP}/{visible_emp['id']}", headers=manager_headers).status_code == 200
    assert client.get(f"{BASE_EMP}/{hidden_emp['id']}", headers=manager_headers).status_code == 403
    assert client.get(f"{BASE_DEPT}/{outside['id']}", headers=manager_headers).status_code == 403


def test_scoped_line_manager_nested_employee_view_is_blocked_outside_scope(client: TestClient):
    admin_headers = _login(client)
    root = _create_department(client, admin_headers, code=f"{_PREFIX}_R2", name=f"{_PREFIX} Root 2")
    outside = _create_department(client, admin_headers, code=f"{_PREFIX}_O2", name=f"{_PREFIX} Outside 2")
    hidden_emp = _create_employee(
        client,
        admin_headers,
        suffix="003",
        full_name=f"{_PREFIX} Hidden Nested",
        department_id=outside["id"],
    )

    manager_headers = _create_scoped_line_manager(
        client,
        admin_headers,
        department_ids=[root["id"]],
    )

    resp = client.get(f"{BASE_EMP}/{hidden_emp['id']}/attachments", headers=manager_headers)
    assert resp.status_code == 403


def test_scoped_line_manager_leave_actions_are_limited_to_assigned_departments(client: TestClient):
    admin_headers = _login(client)
    root = _create_department(client, admin_headers, code=f"{_PREFIX}_LR", name=f"{_PREFIX} Leave Root")
    outside = _create_department(client, admin_headers, code=f"{_PREFIX}_LO", name=f"{_PREFIX} Leave Outside")
    visible_emp = _create_employee(
        client,
        admin_headers,
        suffix="004",
        full_name=f"{_PREFIX} Leave Visible",
        department_id=root["id"],
    )
    hidden_emp = _create_employee(
        client,
        admin_headers,
        suffix="005",
        full_name=f"{_PREFIX} Leave Hidden",
        department_id=outside["id"],
    )
    year = 2096
    _create_leave_entitlement(client, admin_headers, employee_id=visible_emp["id"], year=year)
    _create_leave_entitlement(client, admin_headers, employee_id=hidden_emp["id"], year=year)
    hidden_record = _create_leave_record(client, admin_headers, employee_id=hidden_emp["id"], year=year)

    manager_headers = _create_scoped_line_manager(client, admin_headers, department_ids=[root["id"]])

    visible_create = client.post(
        BASE_LEAVE_REC,
        json={
            "employee_id": visible_emp["id"],
            "leave_type_id": 1,
            "start_date": str(date(year, 6, 2)),
            "end_date": str(date(year, 6, 2)),
        },
        headers=manager_headers,
    )
    assert visible_create.status_code == 201, visible_create.text

    hidden_create = client.post(
        BASE_LEAVE_REC,
        json={
            "employee_id": hidden_emp["id"],
            "leave_type_id": 1,
            "start_date": str(date(year, 6, 3)),
            "end_date": str(date(year, 6, 3)),
        },
        headers=manager_headers,
    )
    assert hidden_create.status_code == 403, hidden_create.text

    hidden_cancel = client.post(
        f"{BASE_LEAVE_REC}/{hidden_record['id']}/cancel",
        json={"cancel_reason": "scope test"},
        headers=manager_headers,
    )
    assert hidden_cancel.status_code == 403, hidden_cancel.text

    visible_list = client.get(
        BASE_LEAVE_REC,
        params={"employee_id": visible_emp["id"], "year": year},
        headers=manager_headers,
    )
    assert visible_list.status_code == 200, visible_list.text


def test_scoped_line_manager_performance_views_and_reports_are_limited_to_assigned_departments(client: TestClient):
    admin_headers = _login(client)
    root = _create_department(client, admin_headers, code=f"{_PREFIX}_PR", name=f"{_PREFIX} Perf Root")
    child = _create_department(
        client,
        admin_headers,
        code=f"{_PREFIX}_PC",
        name=f"{_PREFIX} Perf Child",
        parent_id=root["id"],
    )
    outside = _create_department(client, admin_headers, code=f"{_PREFIX}_PO", name=f"{_PREFIX} Perf Outside")
    visible_emp = _create_employee(
        client,
        admin_headers,
        suffix="006",
        full_name=f"{_PREFIX} Perf Visible",
        department_id=child["id"],
    )
    hidden_emp = _create_employee(
        client,
        admin_headers,
        suffix="007",
        full_name=f"{_PREFIX} Perf Hidden",
        department_id=outside["id"],
    )
    year = 2097
    visible_kpi = _create_kpi(
        client,
        admin_headers,
        employee_id=visible_emp["id"],
        year=year,
        month=6,
        score=88.0,
    )
    hidden_kpi = _create_kpi(
        client,
        admin_headers,
        employee_id=hidden_emp["id"],
        year=year,
        month=6,
        score=91.0,
    )
    _create_yearly_review(client, admin_headers, employee_id=visible_emp["id"], year=year)
    _create_yearly_review(client, admin_headers, employee_id=hidden_emp["id"], year=year)

    manager_headers = _create_scoped_line_manager(client, admin_headers, department_ids=[root["id"]])

    list_resp = client.get(BASE_KPI, params={"year": year, "search": _PREFIX}, headers=manager_headers)
    assert list_resp.status_code == 200, list_resp.text
    listed_ids = {item["id"] for item in list_resp.json()["items"]}
    assert visible_kpi["id"] in listed_ids
    assert hidden_kpi["id"] not in listed_ids

    hidden_detail = client.get(f"{BASE_KPI}/{hidden_kpi['id']}", headers=manager_headers)
    assert hidden_detail.status_code == 403, hidden_detail.text

    hidden_history = client.get(
        f"{BASE_EMP}/{hidden_emp['id']}/performance/kpi",
        headers=manager_headers,
    )
    assert hidden_history.status_code == 403, hidden_history.text

    report_resp = client.get(
        "/api/v1/performance/report/rating-distribution",
        params={"year": year},
        headers=manager_headers,
    )
    assert report_resp.status_code == 200, report_resp.text
    assert report_resp.json()["total_reviewed"] == 1


def test_scoped_line_manager_can_create_kpi_and_review_within_scope(client: TestClient):
    admin_headers = _login(client)
    root = _create_department(client, admin_headers, code=f"{_PREFIX}_PK", name=f"{_PREFIX} Perf Create Root")
    child = _create_department(
        client,
        admin_headers,
        code=f"{_PREFIX}_PKC",
        name=f"{_PREFIX} Perf Create Child",
        parent_id=root["id"],
    )
    outside = _create_department(client, admin_headers, code=f"{_PREFIX}_PKO", name=f"{_PREFIX} Perf Create Outside")
    visible_emp = _create_employee(
        client,
        admin_headers,
        suffix="008",
        full_name=f"{_PREFIX} Perf Create Visible",
        department_id=child["id"],
    )
    hidden_emp = _create_employee(
        client,
        admin_headers,
        suffix="009",
        full_name=f"{_PREFIX} Perf Create Hidden",
        department_id=outside["id"],
    )
    year = 2098
    manager_headers = _create_scoped_line_manager(client, admin_headers, department_ids=[root["id"]])

    visible_kpi = client.post(
        BASE_KPI,
        json={"employee_id": visible_emp["id"], "year": year, "month": 6, "score": 85.0},
        headers=manager_headers,
    )
    assert visible_kpi.status_code == 201, visible_kpi.text

    hidden_kpi = client.post(
        BASE_KPI,
        json={"employee_id": hidden_emp["id"], "year": year, "month": 6, "score": 91.0},
        headers=manager_headers,
    )
    assert hidden_kpi.status_code == 403, hidden_kpi.text

    visible_review = client.post(
        BASE_REVIEWS,
        json={"employee_id": visible_emp["id"], "year": year, "rating": "tot"},
        headers=manager_headers,
    )
    assert visible_review.status_code == 201, visible_review.text

    hidden_review = client.post(
        BASE_REVIEWS,
        json={"employee_id": hidden_emp["id"], "year": year, "rating": "tot"},
        headers=manager_headers,
    )
    assert hidden_review.status_code == 403, hidden_review.text
