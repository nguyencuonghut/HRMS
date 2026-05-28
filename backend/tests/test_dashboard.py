"""Integration tests cho dashboard tổng quan nhân sự (11.1)."""
from __future__ import annotations

import asyncio
from datetime import date
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/reports/dashboard"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_PREFIX = f"T11DASH_{uuid.uuid4().hex[:8]}"


def _engine():
    return create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})


async def _cleanup() -> None:
    engine = _engine()
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        await s.execute(text("""
            DELETE FROM employee_education_histories
            WHERE employee_id IN (
                SELECT id FROM employees WHERE id_number LIKE :prefix
            )
        """), {"prefix": f"{_PREFIX}%"})
        await s.execute(text("""
            DELETE FROM employee_job_records
            WHERE employee_id IN (
                SELECT id FROM employees WHERE id_number LIKE :prefix
            )
        """), {"prefix": f"{_PREFIX}%"})
        await s.execute(text("DELETE FROM employees WHERE id_number LIKE :prefix"), {"prefix": f"{_PREFIX}%"})
        await s.execute(text("DELETE FROM departments WHERE code LIKE :prefix"), {"prefix": f"{_PREFIX}%"})
        await s.commit()
    await engine.dispose()


async def _seed_dashboard_data() -> dict[str, int]:
    await _cleanup()
    engine = _engine()
    Session = async_sessionmaker(engine, expire_on_commit=False)
    today = date.today()
    month_start = date(today.year, today.month, 1)
    prev_month = 12 if today.month == 1 else today.month - 1
    prev_month_year = today.year - 1 if today.month == 1 else today.year
    prev_month_date = date(prev_month_year, prev_month, 15)

    async with Session() as s:
        nationality_id = (await s.execute(text("SELECT id FROM nationalities ORDER BY id LIMIT 1"))).scalar_one()
        education_ids = (await s.execute(text("SELECT id FROM education_levels ORDER BY id LIMIT 2"))).scalars().all()
        sequence_id = (await s.execute(text("SELECT id FROM employee_code_sequences ORDER BY id LIMIT 1"))).scalar_one()
        max_seq = (await s.execute(text("SELECT COALESCE(MAX(employee_seq), 0) FROM employees"))).scalar_one()

        dept_a = (await s.execute(text("""
            INSERT INTO departments (code, name, short_name, dept_type, order_no, is_active, created_at)
            VALUES (:code, :name, :short_name, 'PHONG', 0, TRUE, NOW())
            RETURNING id
        """), {"code": f"{_PREFIX}_A", "name": f"{_PREFIX} Dept A", "short_name": "DA"})).scalar_one()
        dept_a_child = (await s.execute(text("""
            INSERT INTO departments (code, name, short_name, parent_id, dept_type, order_no, is_active, created_at)
            VALUES (:code, :name, :short_name, :parent_id, 'BO_PHAN', 0, TRUE, NOW())
            RETURNING id
        """), {
            "code": f"{_PREFIX}_A1",
            "name": f"{_PREFIX} Dept A Child",
            "short_name": "DA1",
            "parent_id": dept_a,
        })).scalar_one()
        dept_b = (await s.execute(text("""
            INSERT INTO departments (code, name, short_name, dept_type, order_no, is_active, created_at)
            VALUES (:code, :name, :short_name, 'PHONG', 1, TRUE, NOW())
            RETURNING id
        """), {"code": f"{_PREFIX}_B", "name": f"{_PREFIX} Dept B", "short_name": "DB"})).scalar_one()
        dept_zero = (await s.execute(text("""
            INSERT INTO departments (code, name, short_name, dept_type, order_no, is_active, created_at)
            VALUES (:code, :name, :short_name, 'PHONG', 2, TRUE, NOW())
            RETURNING id
        """), {"code": f"{_PREFIX}_Z", "name": f"{_PREFIX} Dept Zero", "short_name": "DZ"})).scalar_one()

        employees = [
            {
                "full_name": f"{_PREFIX} Alpha",
                "normalized_name": f"{_PREFIX.lower()} alpha",
                "last_name": "Alpha",
                "first_name": _PREFIX,
                "gender": "male",
                "status": "official",
                "start_date": today.replace(day=min(5, today.day)),
                "resigned_date": None,
                "is_active": True,
                "department_id": dept_a,
                "dob": date(today.year - 28, 1, 1),
                "education_id": education_ids[0],
            },
            {
                "full_name": f"{_PREFIX} Beta",
                "normalized_name": f"{_PREFIX.lower()} beta",
                "last_name": "Beta",
                "first_name": _PREFIX,
                "gender": "female",
                "status": "official",
                "start_date": date(today.year - 2, 1, 15),
                "resigned_date": None,
                "is_active": True,
                "department_id": dept_a_child,
                "dob": date(today.year - 39, 1, 1),
                "education_id": education_ids[1],
            },
            {
                "full_name": f"{_PREFIX} Gamma",
                "normalized_name": f"{_PREFIX.lower()} gamma",
                "last_name": "Gamma",
                "first_name": _PREFIX,
                "gender": "male",
                "status": "resigned",
                "start_date": date(today.year - 1, 6, 1),
                "resigned_date": today.replace(day=min(10, today.day)),
                "is_active": False,
                "department_id": dept_a,
                "dob": date(today.year - 32, 1, 1),
                "education_id": None,
            },
            {
                "full_name": f"{_PREFIX} Delta",
                "normalized_name": f"{_PREFIX.lower()} delta",
                "last_name": "Delta",
                "first_name": _PREFIX,
                "gender": "other",
                "status": "official",
                "start_date": prev_month_date,
                "resigned_date": None,
                "is_active": True,
                "department_id": dept_b,
                "dob": date(today.year - 24, 1, 1),
                "education_id": None,
            },
        ]

        inserted_ids: list[int] = []
        for idx, employee in enumerate(employees, start=1):
            employee_id = (await s.execute(text("""
                INSERT INTO employees (
                    employee_seq, employee_code_sequence_id, full_name, normalized_name,
                    last_name, first_name, date_of_birth, gender, nationality_id,
                    ethnicity_id, religion_id, id_number, id_issued_on, id_issued_by,
                    id_expires_on, passport_number, passport_issued_on, passport_expires_on,
                    work_permit_number, work_permit_issued_on, work_permit_expires_on,
                    phone_number, personal_email, personal_tax_code, bhxh_code, avatar_path,
                    status, start_date, resigned_date, user_id, is_active, created_at, updated_at
                ) VALUES (
                    :employee_seq, :sequence_id, :full_name, :normalized_name,
                    :last_name, :first_name, :date_of_birth, :gender, :nationality_id,
                    NULL, NULL, :id_number, :id_issued_on, :id_issued_by,
                    NULL, NULL, NULL, NULL,
                    NULL, NULL, NULL,
                    NULL, :personal_email, NULL, NULL, NULL,
                    :status, :start_date, :resigned_date, NULL, :is_active, NOW(), NOW()
                )
                RETURNING id
            """), {
                "employee_seq": max_seq + idx,
                "sequence_id": sequence_id,
                "full_name": employee["full_name"],
                "normalized_name": employee["normalized_name"],
                "last_name": employee["last_name"],
                "first_name": employee["first_name"],
                "date_of_birth": employee["dob"],
                "gender": employee["gender"],
                "nationality_id": nationality_id,
                "id_number": f"{_PREFIX}{idx:03d}",
                "id_issued_on": date(2020, 1, 1),
                "id_issued_by": "CA Test",
                "personal_email": f"{_PREFIX.lower()}_{idx}@example.com",
                "status": employee["status"],
                "start_date": employee["start_date"],
                "resigned_date": employee["resigned_date"],
                "is_active": employee["is_active"],
            })).scalar_one()
            inserted_ids.append(employee_id)

            await s.execute(text("""
                INSERT INTO employee_job_records (
                    employee_id, department_id, job_title_id, job_position_id,
                    probation_start_date, probation_end_date, official_date,
                    effective_from, effective_to, is_current, notes, changed_by,
                    created_at, updated_at
                ) VALUES (
                    :employee_id, :department_id, NULL, NULL,
                    NULL, NULL, NULL,
                    :effective_from, NULL, TRUE, NULL, NULL, NOW(), NOW()
                )
            """), {
                "employee_id": employee_id,
                "department_id": employee["department_id"],
                "effective_from": employee["start_date"],
            })

            if employee["education_id"] is not None:
                await s.execute(text("""
                    INSERT INTO employee_education_histories (
                        employee_id, institution_id, institution_name, major_id, major_name,
                        education_level_id, graduation_year, diploma_type, is_main_education,
                        note, created_at, updated_at
                    ) VALUES (
                        :employee_id, NULL, 'Test University', NULL, 'Test Major',
                        :education_level_id, 2015, 'Bachelor', TRUE,
                        NULL, NOW(), NOW()
                    )
                """), {
                    "employee_id": employee_id,
                    "education_level_id": employee["education_id"],
                })

        await s.commit()
    await engine.dispose()
    return {
        "dept_a": dept_a,
        "dept_a_child": dept_a_child,
        "dept_b": dept_b,
        "dept_zero": dept_zero,
        "month_start_day": month_start.day,
    }


@pytest.fixture(autouse=True)
def _dashboard_fixture_cleanup():
    asyncio.run(_cleanup())
    yield
    asyncio.run(_cleanup())


def _admin_headers(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_summary_and_department_filter(client: TestClient):
    refs = asyncio.run(_seed_dashboard_data())
    headers = _admin_headers(client)
    today = date.today()

    resp = client.get(
        f"{BASE}/summary",
        headers=headers,
        params={"year": today.year, "month": today.month, "department_id": refs["dept_a"]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_headcount"] == 2
    assert data["new_hires_this_month"] == 1
    assert data["resigned_this_month"] == 1
    assert data["headcount_start_of_month"] == 2
    assert data["turnover_rate"] == 50.0

    filtered = client.get(
        f"{BASE}/summary",
        headers=headers,
        params={"year": today.year, "month": today.month, "department_id": refs["dept_b"]},
    )
    assert filtered.status_code == 200, filtered.text
    filtered_data = filtered.json()
    assert filtered_data["total_headcount"] == 1
    assert filtered_data["new_hires_this_month"] == 0
    assert filtered_data["resigned_this_month"] == 0
    assert filtered_data["headcount_start_of_month"] == 1
    assert filtered_data["turnover_rate"] == 0.0


def test_headcount_by_dept_aggregates_roots_and_includes_zero_headcount_departments(client: TestClient):
    refs = asyncio.run(_seed_dashboard_data())
    headers = _admin_headers(client)

    resp = client.get(f"{BASE}/headcount-by-dept", headers=headers)
    assert resp.status_code == 200, resp.text
    items = {item["department_id"]: item for item in resp.json()}
    assert items[refs["dept_a"]]["headcount"] == 2
    assert items[refs["dept_a"]]["direct_headcount"] == 1
    assert items[refs["dept_a"]]["child_department_count"] == 1
    assert refs["dept_a_child"] not in items
    assert items[refs["dept_b"]]["headcount"] == 1
    assert items[refs["dept_b"]]["direct_headcount"] == 1
    assert items[refs["dept_zero"]]["headcount"] == 0


def test_headcount_by_dept_drills_into_direct_children_when_filtered(client: TestClient):
    refs = asyncio.run(_seed_dashboard_data())
    headers = _admin_headers(client)

    resp = client.get(
        f"{BASE}/headcount-by-dept",
        headers=headers,
        params={"department_id": refs["dept_a"]},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) == 1
    assert items[0]["department_id"] == refs["dept_a_child"]
    assert items[0]["headcount"] == 1
    assert items[0]["direct_headcount"] == 1
    assert items[0]["child_department_count"] == 0


def test_monthly_trend_returns_12_months_and_net_change(client: TestClient):
    refs = asyncio.run(_seed_dashboard_data())
    headers = _admin_headers(client)
    today = date.today()
    prev_month = 12 if today.month == 1 else today.month - 1

    resp = client.get(
        f"{BASE}/monthly-trend",
        headers=headers,
        params={"year": today.year, "department_id": refs["dept_a"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["monthly"]) == 12
    current = body["monthly"][today.month - 1]
    assert current["month"] == today.month
    assert current["new_hires"] == 1
    assert current["resigned_count"] == 1
    assert current["net_change"] == 0
    previous = body["monthly"][prev_month - 1]
    assert previous["new_hires"] == 0

    filtered = client.get(
        f"{BASE}/monthly-trend",
        headers=headers,
        params={"year": today.year, "department_id": refs["dept_b"]},
    )
    assert filtered.status_code == 200, filtered.text
    filtered_body = filtered.json()
    assert filtered_body["department_id"] == refs["dept_b"]
    assert filtered_body["monthly"][today.month - 1]["new_hires"] == 0
    assert filtered_body["monthly"][prev_month - 1]["new_hires"] == 1


def test_structure_groups_gender_and_missing_education(client: TestClient):
    refs = asyncio.run(_seed_dashboard_data())
    headers = _admin_headers(client)

    resp = client.get(f"{BASE}/structure", headers=headers, params={"department_id": refs["dept_a"]})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    genders = {item["label"]: item for item in body["gender"]}
    assert genders["Nam"]["count"] == 1
    assert genders["Nữ"]["count"] == 1
    assert "Khác" not in genders
    assert len(body["age_group"]) >= 2
    assert len(body["tenure_group"]) >= 2

    other_resp = client.get(f"{BASE}/structure", headers=headers, params={"department_id": refs["dept_b"]})
    assert other_resp.status_code == 200, other_resp.text
    other_body = other_resp.json()
    other_genders = {item["label"]: item for item in other_body["gender"]}
    assert other_genders["Khác"]["count"] == 1
    education = {item["label"]: item["count"] for item in other_body["education_level"]}
    assert education["Chưa cập nhật"] == 1


def test_dashboard_requires_authentication(client: TestClient):
    resp = client.get(f"{BASE}/summary")
    assert resp.status_code == 401, resp.text
