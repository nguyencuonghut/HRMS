from __future__ import annotations

import asyncio
import io
import uuid
from datetime import date, timedelta

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.org import DepartmentJobPosition
from app.schemas.employee_import import IMPORT_COLUMNS
from app.services.employee_import_service import process_import


BASE_EMP = "/api/v1/employees"
BASE_POS = "/api/v1/job-positions"
BASE_DEPT = "/api/v1/departments"
BASE_JR = "/api/v1/recruitment/job-requisitions"
BASE_CAND = "/api/v1/recruitment/candidates"
BASE_APP = "/api/v1/recruitment/applications"
BASE_OFFERS = "/api/v1/recruitment/offers"
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
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _add_mapping(department_id: int, job_position_id: int) -> None:
    engine, session_factory = _make_session()
    try:
        async with session_factory() as session:
            session.add(
                DepartmentJobPosition(
                    department_id=department_id,
                    job_position_id=job_position_id,
                    is_active=True,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


def _create_department(client: TestClient, headers: dict, *, code: str, name: str) -> int:
    res = client.post(
        BASE_DEPT,
        json={"code": code, "name": name, "dept_type": "PHONG"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _get_any_department(client: TestClient, headers: dict) -> dict:
    payload = client.get(BASE_DEPT, headers=headers).json()
    rows = payload["items"] if isinstance(payload, dict) else payload
    assert rows, "Cần ít nhất 1 phòng ban seed"
    return rows[0]


def _get_any_job_title_id(client: TestClient, headers: dict) -> int | None:
    payload = client.get("/api/v1/job-titles", headers=headers).json()
    rows = payload if isinstance(payload, list) else payload.get("items", payload)
    assert rows, "Cần ít nhất 1 chức danh seed"
    return rows[0]["id"]


def _create_position(
    client: TestClient,
    headers: dict,
    *,
    department_id: int,
    job_title_id: int | None,
    code: str,
    name: str,
) -> dict:
    res = client.post(
        BASE_POS,
        json={
            "code": code,
            "name": name,
            "department_id": department_id,
            "job_title_id": job_title_id,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _valid_employee_payload(*, suffix: str, department_id: int, position_id: int, job_title_id: int | None) -> dict:
    return {
        "employee_code_sequence_id": 1,
        "full_name": f"Nhân sự shared {suffix}",
        "last_name": "Nhân sự",
        "first_name": f"shared {suffix}",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": 1,
        "id_number": f"SHARED{suffix[:12]}",
        "id_issued_on": "2020-01-01",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ",
        "status": "probation",
        "start_date": "2026-01-01",
        "initial_department_id": department_id,
        "initial_job_title_id": job_title_id,
        "initial_job_position_id": position_id,
        "initial_job_effective_from": "2026-01-01",
    }


def _make_import_row(*, suffix: str, department_code: str, position_name: str) -> list[str]:
    values = {column: "" for column in IMPORT_COLUMNS}
    values.update(
        {
            "Họ và tên": f"Import Shared {suffix}",
            "Họ": "Import",
            "Tên": f"Shared {suffix}",
            "Ngày sinh": "01/01/1990",
            "Giới tính": "nam",
            "Số CCCD/CMND": f"IMPSH{suffix[:10]}",
            "Ngày cấp CCCD": "01/01/2020",
            "Nơi cấp CCCD": "Cục Cảnh sát ĐKQLCƯ",
            "Trạng thái": "probation",
            "Ngày vào làm": date.today().strftime("%d/%m/%Y"),
            "Phòng ban": department_code,
            "Vị trí công việc": position_name,
            "Hệ mã nhân viên": "SYS1",
        }
    )
    return [values[column] for column in IMPORT_COLUMNS]


def _make_xlsx(rows: list[list[str]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _create_shared_position_setup(client: TestClient, headers: dict) -> tuple[dict, dict, dict]:
    suffix = uuid.uuid4().hex[:8].upper()
    owner = _get_any_department(client, headers)
    target_id = _create_department(
        client,
        headers,
        code=f"TSP{suffix}",
        name=f"Phòng dùng chung {suffix}",
    )
    job_title_id = _get_any_job_title_id(client, headers)
    position = _create_position(
        client,
        headers,
        department_id=owner["id"],
        job_title_id=job_title_id,
        code=f"TSPOS{suffix}",
        name=f"Vị trí dùng chung {suffix}",
    )
    target = {"id": target_id, "code": f"TSP{suffix}", "name": f"Phòng dùng chung {suffix}"}

    asyncio.run(_add_mapping(target["id"], position["id"]))
    return owner, target, position


def _create_recruitment_flow(
    client: TestClient,
    headers: dict,
    *,
    department_id: int,
    position_id: int,
    suffix: str,
) -> int:
    jr = client.post(
        BASE_JR,
        json={
            "job_position_id": position_id,
            "department_id": department_id,
            "quantity": 1,
            "reason_type": "new",
        },
        headers=headers,
    )
    assert jr.status_code == 201, jr.text
    jr_id = jr.json()["id"]
    assert client.post(f"{BASE_JR}/{jr_id}/submit", headers=headers).status_code == 200
    assert client.post(f"{BASE_JR}/{jr_id}/approve", headers=headers).status_code == 200
    pipeline_res = client.post(
        f"{BASE_JR}/{jr_id}/pipeline",
        json={"stages": [{"stage_order": 1, "stage_name": "Sàng lọc", "stage_type": "screening", "is_active": True}]},
        headers=headers,
    )
    assert pipeline_res.status_code == 200, pipeline_res.text

    candidate = client.post(
        BASE_CAND,
        json={
            "full_name": f"Ứng viên shared {suffix}",
            "last_name": "Ứng viên",
            "first_name": f"shared {suffix}",
            "personal_email": f"shared_{suffix}@example.com",
            "date_of_birth": "1990-01-01",
            "gender": "male",
            "nationality_id": 1,
            "id_number": f"0{suffix[:9]}99",
            "id_issued_on": "2015-01-01",
            "id_issued_by": "Cục CSQLHC",
        },
        headers=headers,
    )
    assert candidate.status_code == 201, candidate.text
    candidate_id = candidate.json()["id"]

    app = client.post(
        f"/api/v1/recruitment/candidates/{candidate_id}/apply",
        json={
            "job_requisition_id": jr_id,
            "applied_date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert app.status_code == 201, app.text
    app_id = app.json()["id"]
    application_stage = app.json()["current_stage"]

    pipeline = client.get(f"{BASE_JR}/{jr_id}/pipeline", headers=headers)
    assert pipeline.status_code == 200, pipeline.text
    stages = pipeline.json()
    assert stages, "JR không có pipeline stages"

    while application_stage != "offer":
        stage = next((item for item in stages if item["stage_type"] == application_stage), None)
        assert stage is not None, f"Không tìm thấy stage '{application_stage}' trong pipeline"
        advance = client.post(
            f"{BASE_APP}/{app_id}/advance",
            json={"stage_id": stage["id"], "result": "pass"},
            headers=headers,
        )
        assert advance.status_code == 200, advance.text
        application_stage = advance.json()["current_stage"]

    offer = client.post(
        f"/api/v1/recruitment/applications/{app_id}/offers",
        json={
            "job_position_id": position_id,
            "department_id": department_id,
            "proposed_start_date": (date.today() + timedelta(days=14)).isoformat(),
            "official_salary": 15000000,
            "probation_salary": 13000000,
            "probation_days": 30,
            "internal_note": f"shared-mapping-{suffix}",
        },
        headers=headers,
    )
    assert offer.status_code == 201, offer.text
    offer_id = offer.json()["id"]

    assert client.post(f"{BASE_OFFERS}/{offer_id}/send", headers=headers).status_code == 200
    assert client.post(f"{BASE_OFFERS}/{offer_id}/accept", headers=headers).status_code == 200
    return offer_id


def test_job_position_list_filter_includes_shared_mapping(client: TestClient):
    headers = _admin(client)
    owner, target, position = _create_shared_position_setup(client, headers)

    res = client.get(BASE_POS, headers=headers, params={"department_id": target["id"], "is_active": True})
    assert res.status_code == 200, res.text
    rows = res.json()
    found = next((row for row in rows if row["id"] == position["id"]), None)
    assert found is not None
    assert found["department_id"] == owner["id"]


def test_create_employee_allows_shared_position_mapping(client: TestClient):
    headers = _admin(client)
    _, target, position = _create_shared_position_setup(client, headers)
    suffix = uuid.uuid4().hex[:10].upper()

    res = client.post(
        BASE_EMP,
        json=_valid_employee_payload(
            suffix=suffix,
            department_id=target["id"],
            position_id=position["id"],
            job_title_id=position["job_title_id"],
        ),
        headers=headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["current_job"]["department_id"] == target["id"]
    assert res.json()["current_job"]["job_position_id"] == position["id"]


def test_create_job_record_allows_shared_position_mapping(client: TestClient):
    headers = _admin(client)
    _, target, position = _create_shared_position_setup(client, headers)
    suffix = uuid.uuid4().hex[:10].upper()
    employee = client.post(
        BASE_EMP,
        json={
            "employee_code_sequence_id": 1,
            "full_name": f"Job record shared {suffix}",
            "last_name": "Job",
            "first_name": f"Shared {suffix}",
            "date_of_birth": "1990-01-01",
            "gender": "male",
            "nationality_id": 1,
            "id_number": f"JOBSH{suffix[:10]}",
            "id_issued_on": "2020-01-01",
            "id_issued_by": "Cục Cảnh sát ĐKQLCƯ",
            "status": "probation",
            "start_date": "2026-01-01",
        },
        headers=headers,
    )
    assert employee.status_code == 201, employee.text

    record = client.post(
        f"{BASE_EMP}/{employee.json()['id']}/job-records",
        json={
            "department_id": target["id"],
            "job_position_id": position["id"],
            "job_title_id": position["job_title_id"],
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    assert record.status_code == 201, record.text
    assert record.json()["department_id"] == target["id"]
    assert record.json()["job_position_id"] == position["id"]


@pytest.mark.asyncio
async def test_employee_import_accepts_shared_position_mapping():
    engine, session_factory = _make_session()
    suffix = uuid.uuid4().hex[:8].upper()
    try:
        async with session_factory() as session:
            from app.models.org import Department, JobPosition, JobTitle

            job_title = (await session.execute(select(JobTitle))).scalars().first()
            assert job_title is not None

            owner = Department(code=f"IMPOWN{suffix}", name=f"Phòng owner import {suffix}", dept_type="PHONG")
            target = Department(code=f"IMPTGT{suffix}", name=f"Phòng target import {suffix}", dept_type="PHONG")
            session.add(owner)
            session.add(target)
            await session.flush()

            position = JobPosition(
                code=f"IMPPOS{suffix}",
                name=f"Vị trí shared import {suffix}",
                department_id=owner.id,
                job_title_id=job_title.id,
                is_active=True,
            )
            session.add(position)
            await session.flush()
            session.add(
                DepartmentJobPosition(
                    department_id=target.id,
                    job_position_id=position.id,
                    is_active=True,
                )
            )
            await session.flush()

            workbook = _make_xlsx(
                [
                    IMPORT_COLUMNS,
                    _make_import_row(
                        suffix=suffix,
                        department_code=target.code,
                        position_name=position.name,
                    ),
                ]
            )

            result = await process_import(session, workbook)
            assert result.success == 1
            assert result.failed == 0
    finally:
        await engine.dispose()


def test_create_hiring_decision_allows_shared_position_mapping(client: TestClient):
    headers = _admin(client)
    _, target, position = _create_shared_position_setup(client, headers)
    suffix = uuid.uuid4().hex[:8]
    offer_id = _create_recruitment_flow(
        client,
        headers,
        department_id=target["id"],
        position_id=position["id"],
        suffix=suffix,
    )

    res = client.post(
        f"/api/v1/recruitment/offers/{offer_id}/hiring-decision",
        json={
            "decision_number": f"QDSH-{suffix.upper()}",
            "signed_date": date.today().isoformat(),
            "department_id": target["id"],
            "job_position_id": position["id"],
            "job_title_id": position["job_title_id"],
            "start_date": (date.today() + timedelta(days=21)).isoformat(),
            "probation_salary": 13000000,
            "official_salary": 15000000,
            "probation_days": 30,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["department_id"] == target["id"]
    assert res.json()["job_position_id"] == position["id"]
