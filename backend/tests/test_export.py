from __future__ import annotations

import asyncio
import io
import uuid
from datetime import date, timedelta

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.workers.export_tasks import run_export_task

BASE = "/api/v1/reports/export"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_PREFIX = f"T11EXP_{uuid.uuid4().hex[:8]}"


def _engine():
    return create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})


def _admin_headers(client: TestClient) -> dict[str, str]:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _cleanup() -> None:
    engine = _engine()
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        await s.execute(text("""
            DELETE FROM export_jobs WHERE filename LIKE :prefix
        """), {"prefix": f"{_PREFIX}%"})
        await s.execute(text("""
            DELETE FROM employee_contracts
            WHERE employee_id IN (SELECT id FROM employees WHERE id_number LIKE :prefix)
        """), {"prefix": f"{_PREFIX}%"})
        await s.execute(text("""
            DELETE FROM employee_job_records
            WHERE employee_id IN (SELECT id FROM employees WHERE id_number LIKE :prefix)
        """), {"prefix": f"{_PREFIX}%"})
        await s.execute(text("DELETE FROM employees WHERE id_number LIKE :prefix"), {"prefix": f"{_PREFIX}%"})
        await s.execute(text("DELETE FROM contract_categories WHERE code LIKE :prefix"), {"prefix": f"{_PREFIX}%"})
        await s.execute(text("DELETE FROM job_titles WHERE code LIKE :prefix"), {"prefix": f"{_PREFIX}%"})
        await s.execute(text("DELETE FROM departments WHERE code LIKE :prefix"), {"prefix": f"{_PREFIX}%"})
        await s.commit()
    await engine.dispose()


async def _seed() -> None:
    await _cleanup()
    engine = _engine()
    Session = async_sessionmaker(engine, expire_on_commit=False)
    today = date.today()
    async with Session() as s:
        nationality_id = (await s.execute(text("SELECT id FROM nationalities ORDER BY id LIMIT 1"))).scalar_one()
        sequence_id = (await s.execute(text("SELECT id FROM employee_code_sequences ORDER BY id LIMIT 1"))).scalar_one()
        max_seq = (await s.execute(text("SELECT COALESCE(MAX(employee_seq), 0) FROM employees"))).scalar_one()

        dept_id = (await s.execute(text("""
            INSERT INTO departments (code, name, short_name, dept_type, order_no, is_active, created_at)
            VALUES (:code, :name, 'EXP', 'PHONG', 0, TRUE, NOW()) RETURNING id
        """), {"code": f"{_PREFIX}_DEPT", "name": f"{_PREFIX} Dept"})).scalar_one()
        job_title_id = (await s.execute(text("""
            INSERT INTO job_titles (code, name, level, is_active, created_at)
            VALUES (:code, :name, 4, TRUE, NOW()) RETURNING id
        """), {"code": f"{_PREFIX}_JT", "name": f"{_PREFIX} Staff"})).scalar_one()
        category_id = (await s.execute(text("""
            INSERT INTO contract_categories (code, name, normalized_name, document_kind, is_active, created_at)
            VALUES (:code, :name, :normalized_name, 'labor_contract', TRUE, NOW()) RETURNING id
        """), {
            "code": f"{_PREFIX}_CAT",
            "name": f"{_PREFIX} Labor",
            "normalized_name": f"{_PREFIX.lower()} labor",
        })).scalar_one()

        for index in range(1, 4):
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
                    :last_name, :first_name, :date_of_birth, 'male', :nationality_id,
                    NULL, NULL, :id_number, :id_issued_on, 'CA Test',
                    NULL, NULL, NULL, NULL,
                    NULL, NULL, NULL,
                    NULL, :personal_email, NULL, NULL, NULL,
                    'official', :start_date, NULL, NULL, TRUE, NOW(), NOW()
                ) RETURNING id
            """), {
                "employee_seq": max_seq + index,
                "sequence_id": sequence_id,
                "full_name": f"{_PREFIX} Employee {index}",
                "normalized_name": f"{_PREFIX.lower()} employee {index}",
                "last_name": f"Employee{index}",
                "first_name": _PREFIX,
                "date_of_birth": date(1990, 1, min(index, 28)),
                "nationality_id": nationality_id,
                "id_number": f"{_PREFIX}{index:03d}",
                "id_issued_on": date(2020, 1, 1),
                "personal_email": f"{_PREFIX.lower()}_{index}@example.com",
                "start_date": today - timedelta(days=120 * index),
            })).scalar_one()

            await s.execute(text("""
                INSERT INTO employee_job_records (
                    employee_id, department_id, job_title_id, job_position_id,
                    probation_start_date, probation_end_date, official_date,
                    effective_from, effective_to, is_current, notes, changed_by, created_at, updated_at
                ) VALUES (
                    :employee_id, :department_id, :job_title_id, NULL,
                    NULL, NULL, NULL,
                    :effective_from, NULL, TRUE, NULL, NULL, NOW(), NOW()
                )
            """), {
                "employee_id": employee_id,
                "department_id": dept_id,
                "job_title_id": job_title_id,
                "effective_from": today - timedelta(days=120 * index),
            })
            await s.execute(text("""
                INSERT INTO employee_contracts (
                    employee_id, parent_contract_id, contract_category_id, document_kind,
                    contract_number, signed_date, effective_from, effective_to,
                    insurance_salary, status, created_at, updated_at
                ) VALUES (
                    :employee_id, NULL, :category_id, 'labor_contract',
                    :contract_number, :signed_date, :effective_from, :effective_to,
                    NULL, 'active', NOW(), NOW()
                )
            """), {
                "employee_id": employee_id,
                "category_id": category_id,
                "contract_number": f"{_PREFIX}-C-{index:03d}",
                "signed_date": today - timedelta(days=120 * index),
                "effective_from": today - timedelta(days=120 * index),
                "effective_to": today + timedelta(days=30 * index),
            })
        await s.commit()
    await engine.dispose()


@pytest.fixture(scope="module", autouse=True)
def _seed_data():
    asyncio.run(_seed())
    yield
    asyncio.run(_cleanup())


def test_sync_export_xlsx(client: TestClient):
    headers = _admin_headers(client)
    response = client.post(
        BASE,
        headers=headers,
        json={
            "report_type": "hr-employee-list",
            "format": "xlsx",
            "filename": f"{_PREFIX}_sync",
            "filters": {"page_size": 20},
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "done"
    assert payload["download_url"]

    download = client.get(payload["download_url"], headers=headers)
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    workbook = openpyxl.load_workbook(io.BytesIO(download.content))
    assert workbook.active.title == "Danh sach nhan su"
    assert workbook.active["A1"].value == "Ma NV"


def test_async_export_history_status_and_delete(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    headers = _admin_headers(client)

    class _TaskResult:
        id = "fake-export-task"

    monkeypatch.setattr("app.services.export_service.ASYNC_THRESHOLD_ROWS", 1)
    monkeypatch.setattr("app.workers.export_tasks.run_export_task.delay", lambda *args, **kwargs: _TaskResult())

    response = client.post(
        BASE,
        headers=headers,
        json={
            "report_type": "hr-employee-list",
            "format": "xlsx",
            "filename": f"{_PREFIX}_async",
            "filters": {"page_size": 20},
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "pending"
    job_id = payload["id"]

    status_pending = client.get(f"{BASE}/{job_id}/status", headers=headers)
    assert status_pending.status_code == 200
    assert status_pending.json()["status"] == "pending"

    run_export_task.run(job_id, {
        "report_type": "hr-employee-list",
        "format": "xlsx",
        "filename": f"{_PREFIX}_async.xlsx",
        "filters": {"page_size": 20},
    })

    status_done = client.get(f"{BASE}/{job_id}/status", headers=headers)
    assert status_done.status_code == 200
    assert status_done.json()["status"] == "done"
    assert status_done.json()["download_url"]

    history = client.get(f"{BASE}/history?page=1&page_size=10", headers=headers)
    assert history.status_code == 200
    assert history.json()["total"] >= 1
    assert any(item["id"] == job_id for item in history.json()["items"])

    delete_response = client.delete(f"{BASE}/{job_id}", headers=headers)
    assert delete_response.status_code == 204

    status_missing = client.get(f"{BASE}/{job_id}/status", headers=headers)
    assert status_missing.status_code == 404
