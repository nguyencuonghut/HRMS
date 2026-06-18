from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_HR_OFFICER_EMAIL = "hrofficer@hrms.local"
_HR_OFFICER_PASSWORD = "Hrms@2026"


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _get_active_employee_id() -> int:
    async with _make_session()() as s:
        row = (
            await s.execute(
                text("SELECT id FROM employees WHERE status != 'resigned' ORDER BY id LIMIT 1")
            )
        ).fetchone()
        assert row is not None, "Không tìm thấy nhân viên active"
        return row[0]


def test_hr_officer_can_create_but_not_delete_training_course(client: TestClient):
    headers = _login(client, _HR_OFFICER_EMAIL, _HR_OFFICER_PASSWORD)
    code = f"RBAC_TR_{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/api/v1/training/courses",
        json={
            "code": code,
            "name": f"RBAC training {code}",
            "course_type": "noi_bo",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    course_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/training/courses/{course_id}", headers=headers)
    assert deleted.status_code == 403, deleted.text


def test_hr_officer_can_create_but_not_delete_recruitment_channel(client: TestClient):
    headers = _login(client, _HR_OFFICER_EMAIL, _HR_OFFICER_PASSWORD)
    code = f"rbac_ch_{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/api/v1/recruitment/channels",
        json={"code": code, "name": f"RBAC channel {code}"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    channel_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/recruitment/channels/{channel_id}", headers=headers)
    assert deleted.status_code == 403, deleted.text


@pytest.mark.asyncio
async def test_hr_officer_can_create_but_not_delete_discipline(client: TestClient):
    headers = _login(client, _HR_OFFICER_EMAIL, _HR_OFFICER_PASSWORD)
    employee_id = await _get_active_employee_id()
    created = client.post(
        "/api/v1/disciplines",
        data={
            "body": json.dumps(
                {
                    "employee_id": employee_id,
                    "discipline_form": "khien_trach",
                    "violation_date": "2098-01-10",
                    "effective_date": "2098-01-11",
                    "title": f"RBAC discipline {uuid.uuid4().hex[:8]}",
                }
            )
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    discipline_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/disciplines/{discipline_id}", headers=headers)
    assert deleted.status_code == 403, deleted.text


def test_admin_can_import_admin_units_with_catalog_edit_permission(client: TestClient):
    headers = _login(client, _ADMIN_EMAIL, _ADMIN_PASSWORD)
    response = client.post(
        "/api/v1/admin-units/import",
        json={
            "system_type": "new",
            "source_name": "rbac_import_check",
            "source_version": f"v_{uuid.uuid4().hex[:8]}",
            "mode": "merge",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
