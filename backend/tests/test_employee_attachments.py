"""Tests cho module hồ sơ đính kèm (3.5)."""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.employee import Employee
from app.schemas.employee_attachment import MAX_FILE_SIZE
from app.seeds import employees as employees_seed

BASE = "/api/v1/employees"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_LINE_MANAGER_EMAIL = "linemanager@hrms.local"
_PREFIX = "TESTATT"


def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict:
    token = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient) -> dict:
    return _login(client)


def _viewer(client: TestClient) -> dict:
    return _login(client, _LINE_MANAGER_EMAIL)


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup_test_employees():
    async with _make_session()() as s:
        employee_ids = [e.id for e in (await s.execute(select(Employee))).scalars().all() if e.id_number.startswith(_PREFIX)]
        if employee_ids:
            await s.execute(text("DELETE FROM employee_attachments WHERE employee_id = ANY(:employee_ids)"), {"employee_ids": employee_ids})
            await s.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
        await s.commit()


@pytest.fixture(scope="session", autouse=True)
async def seed_data():
    async with _make_session()() as session:
        await employees_seed.seed_sample_employees(session)
        await session.commit()
    yield


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await _cleanup_test_employees()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _create_employee(client: TestClient, headers: dict, suffix: str = "0000001") -> dict:
    resp = client.post(BASE, json={
        "employee_code_sequence_id": 1,
        "full_name": "Test Attachment Viên",
        "last_name": "Test",
        "first_name": "Attachment Viên",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": 1,
        "id_number": f"{_PREFIX}{suffix}",
        "id_issued_on": "2020-01-01",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ",
        "status": "probation",
        "start_date": "2026-01-01",
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _upload(client: TestClient, employee_id: int, headers: dict,
            document_type: str = "id_card_front",
            content: bytes = b"fake pdf content",
            filename: str = "test.pdf") -> dict:
    resp = client.post(
        f"{BASE}/{employee_id}/attachments",
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
        data={"document_type": document_type},
        headers=headers,
    )
    return resp


# ── List ───────────────────────────────────────────────────────────────────────

def test_list_attachments_empty(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = client.get(f"{BASE}/{emp['id']}/attachments", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


# ── Upload ─────────────────────────────────────────────────────────────────────

def test_upload_attachment_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = _upload(client, emp["id"], headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["document_type"] == "id_card_front"
    assert data["document_type_label"] == "CCCD / CMND — Mặt trước"
    assert data["file_name"] == "test.pdf"
    assert data["file_size"] > 0
    assert data["download_url"].endswith(f"/download")
    assert data["employee_id"] == emp["id"]


def test_upload_attachment_with_description(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = client.post(
        f"{BASE}/{emp['id']}/attachments",
        files={"file": ("cccd.jpg", io.BytesIO(b"img"), "image/jpeg")},
        data={"document_type": "id_card_back", "description": "Scan độ phân giải cao"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["description"] == "Scan độ phân giải cao"


def test_upload_attachment_invalid_document_type_422(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    resp = client.post(
        f"{BASE}/{emp['id']}/attachments",
        files={"file": ("f.pdf", io.BytesIO(b"x"), "application/pdf")},
        data={"document_type": "invalid_type"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_upload_attachment_file_too_large_413(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    oversized = b"x" * (MAX_FILE_SIZE + 1)
    resp = client.post(
        f"{BASE}/{emp['id']}/attachments",
        files={"file": ("big.pdf", io.BytesIO(oversized), "application/pdf")},
        data={"document_type": "degree"},
        headers=headers,
    )
    assert resp.status_code == 413


# ── Download ───────────────────────────────────────────────────────────────────

def test_download_attachment_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    att = _upload(client, emp["id"], headers, content=b"pdf content here").json()
    resp = client.get(f"{BASE}/{emp['id']}/attachments/{att['id']}/download", headers=headers)
    assert resp.status_code == 200
    assert b"pdf content here" in resp.content


def test_download_wrong_employee_404(client: TestClient):
    headers = _admin(client)
    emp1 = _create_employee(client, headers, suffix="0000002")
    emp2 = _create_employee(client, headers, suffix="0000003")
    att = _upload(client, emp1["id"], headers).json()
    resp = client.get(f"{BASE}/{emp2['id']}/attachments/{att['id']}/download", headers=headers)
    assert resp.status_code == 404


# ── Delete ─────────────────────────────────────────────────────────────────────

def test_delete_attachment_success(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    att = _upload(client, emp["id"], headers).json()
    resp = client.delete(f"{BASE}/{emp['id']}/attachments/{att['id']}", headers=headers)
    assert resp.status_code == 204
    # Verify gone from list
    lst = client.get(f"{BASE}/{emp['id']}/attachments", headers=headers).json()
    assert not any(a["id"] == att["id"] for a in lst)


def test_delete_wrong_employee_404(client: TestClient):
    headers = _admin(client)
    emp1 = _create_employee(client, headers, suffix="0000004")
    emp2 = _create_employee(client, headers, suffix="0000005")
    att = _upload(client, emp1["id"], headers).json()
    resp = client.delete(f"{BASE}/{emp2['id']}/attachments/{att['id']}", headers=headers)
    assert resp.status_code == 404


# ── Filter ─────────────────────────────────────────────────────────────────────

def test_filter_by_document_type(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    _upload(client, emp["id"], headers, document_type="degree")
    _upload(client, emp["id"], headers, document_type="id_card_front")
    _upload(client, emp["id"], headers, document_type="id_card_back")

    resp = client.get(f"{BASE}/{emp['id']}/attachments?document_type=degree", headers=headers)
    data = resp.json()
    assert resp.status_code == 200
    assert len(data) == 1
    assert data[0]["document_type"] == "degree"


def test_multiple_versions_same_type(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    _upload(client, emp["id"], headers, document_type="avatar", content=b"v1", filename="v1.jpg")
    _upload(client, emp["id"], headers, document_type="avatar", content=b"v2", filename="v2.jpg")

    resp = client.get(f"{BASE}/{emp['id']}/attachments?document_type=avatar", headers=headers)
    data = resp.json()
    assert len(data) == 2
    # Mới nhất trả về trước (uploaded_at DESC)
    assert data[0]["file_name"] == "v2.jpg"
    assert data[1]["file_name"] == "v1.jpg"


# ── Audit log ──────────────────────────────────────────────────────────────────

def test_upload_audit_log(client: TestClient):
    headers = _admin(client)
    emp = _create_employee(client, headers)
    _upload(client, emp["id"], headers, document_type="passport")

    logs = client.get("/api/v1/audit-logs", params={"entity_type": "employee_attachment"}, headers=headers).json()
    actions = [l["action"] for l in logs]
    assert "UPLOAD_ATTACHMENT" in actions


# ── Permissions ────────────────────────────────────────────────────────────────

def test_viewer_cannot_upload_403(client: TestClient):
    admin_headers = _admin(client)
    viewer_headers = _viewer(client)
    emp = _create_employee(client, admin_headers)
    resp = client.post(
        f"{BASE}/{emp['id']}/attachments",
        files={"file": ("f.pdf", io.BytesIO(b"x"), "application/pdf")},
        data={"document_type": "degree"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


def test_viewer_cannot_delete_403(client: TestClient):
    admin_headers = _admin(client)
    viewer_headers = _viewer(client)
    emp = _create_employee(client, admin_headers)
    att = _upload(client, emp["id"], admin_headers).json()
    resp = client.delete(f"{BASE}/{emp['id']}/attachments/{att['id']}", headers=viewer_headers)
    assert resp.status_code == 403


def test_viewer_can_list_and_download(client: TestClient):
    admin_headers = _admin(client)
    viewer_headers = _viewer(client)
    emp = _create_employee(client, admin_headers)
    att = _upload(client, emp["id"], admin_headers, content=b"readonly").json()

    lst = client.get(f"{BASE}/{emp['id']}/attachments", headers=viewer_headers)
    assert lst.status_code == 200

    dl = client.get(f"{BASE}/{emp['id']}/attachments/{att['id']}/download", headers=viewer_headers)
    assert dl.status_code == 200
