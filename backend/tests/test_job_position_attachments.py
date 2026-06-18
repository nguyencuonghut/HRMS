"""Integration tests cho attachment endpoints của /api/v1/job-positions."""
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.config import settings

BASE     = "/api/v1/job-positions"
DEPT_URL = "/api/v1/departments"
JT_URL   = "/api/v1/job-titles"

_POS_CODE  = "TEST_ATT_POS"
_DEPT_CODE = "TEST_DEPT_ATT"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Session setup ──────────────────────────────────────────────────────────────

def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _clean_db():
    async with _make_session()() as session:
        # Delete code rules referencing the position or department
        await session.execute(text("""
            DELETE FROM employee_code_sequence_rules 
            WHERE job_position_id IN (SELECT id FROM job_positions WHERE code = :pos_code)
               OR department_id IN (SELECT id FROM departments WHERE code = :dept_code)
        """), {"pos_code": _POS_CODE, "dept_code": _DEPT_CODE})
        
        # Delete job records referencing the position or department
        await session.execute(text("""
            DELETE FROM employee_job_records 
            WHERE job_position_id IN (SELECT id FROM job_positions WHERE code = :pos_code)
               OR department_id IN (SELECT id FROM departments WHERE code = :dept_code)
        """), {"pos_code": _POS_CODE, "dept_code": _DEPT_CODE})
        
        # Delete attachments
        await session.execute(text("""
            DELETE FROM job_position_attachments 
            WHERE job_position_id IN (SELECT id FROM job_positions WHERE code = :pos_code)
        """), {"pos_code": _POS_CODE})
        
        # Delete job positions
        await session.execute(text("DELETE FROM job_positions WHERE code = :pos_code"), {"pos_code": _POS_CODE})
        
        # Delete departments
        await session.execute(text("DELETE FROM departments WHERE code = :dept_code"), {"dept_code": _DEPT_CODE})
        
        await session.commit()


@pytest.fixture(scope="session", autouse=True)
async def db_cleanup():
    await _clean_db()
    yield
    await _clean_db()


@pytest.fixture(scope="session")
def dept_id(db_cleanup, client: TestClient) -> int:
    r = client.post(
        DEPT_URL,
        json={"code": _DEPT_CODE, "name": "Test Dept Att", "dept_type": "PHONG"},
        headers=_admin(client),
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture(scope="session")
def pos_id(client: TestClient, dept_id: int) -> int:
    r = client.post(
        BASE,
        json={"code": _POS_CODE, "name": "Test Pos Att", "department_id": dept_id},
        headers=_admin(client),
    )
    assert r.status_code == 201
    return r.json()["id"]


def _fake_file(name: str = "test.pdf", content: bytes = b"dummy pdf content") -> dict:
    return {"file": (name, io.BytesIO(content), "application/pdf")}


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_list_attachments_empty(client: TestClient, pos_id: int):
    resp = client.get(f"{BASE}/{pos_id}/attachments", headers=_admin(client))
    assert resp.status_code == 200
    assert resp.json() == []


def test_upload_attachment(client: TestClient, pos_id: int):
    headers = _admin(client)
    resp = client.post(
        f"{BASE}/{pos_id}/attachments",
        files=_fake_file("jd.pdf", b"job description content"),
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["file_name"] == "jd.pdf"
    assert data["file_size"] == len(b"job description content")
    assert "attachments/" in data["file_path"]
    # cleanup
    client.delete(f"{BASE}/{pos_id}/attachments/{data['id']}", headers=headers)


def test_list_attachments_after_upload(client: TestClient, pos_id: int):
    headers = _admin(client)
    r = client.post(f"{BASE}/{pos_id}/attachments", files=_fake_file("cv.pdf"), headers=headers)
    assert r.status_code == 201
    att_id = r.json()["id"]

    items = client.get(f"{BASE}/{pos_id}/attachments", headers=headers).json()
    assert any(i["id"] == att_id for i in items)

    client.delete(f"{BASE}/{pos_id}/attachments/{att_id}", headers=headers)


def test_delete_attachment(client: TestClient, pos_id: int):
    headers = _admin(client)
    r = client.post(f"{BASE}/{pos_id}/attachments", files=_fake_file("del.pdf"), headers=headers)
    att_id = r.json()["id"]

    resp = client.delete(f"{BASE}/{pos_id}/attachments/{att_id}", headers=headers)
    assert resp.status_code == 200
    assert "Đã xóa" in resp.json()["message"]

    items = client.get(f"{BASE}/{pos_id}/attachments", headers=headers).json()
    assert not any(i["id"] == att_id for i in items)


def test_delete_attachment_not_found(client: TestClient, pos_id: int):
    assert client.delete(f"{BASE}/{pos_id}/attachments/999999", headers=_admin(client)).status_code == 404


def test_list_attachments_invalid_position(client: TestClient):
    assert client.get(f"{BASE}/999999/attachments", headers=_admin(client)).status_code == 404


def test_upload_to_invalid_position(client: TestClient):
    resp = client.post(f"{BASE}/999999/attachments", files=_fake_file(), headers=_admin(client))
    assert resp.status_code == 404


def test_multiple_attachments(client: TestClient, pos_id: int):
    headers = _admin(client)
    ids = []
    for name in ["a.pdf", "b.docx", "c.xlsx"]:
        r = client.post(f"{BASE}/{pos_id}/attachments", files=_fake_file(name), headers=headers)
        assert r.status_code == 201
        ids.append(r.json()["id"])

    items = client.get(f"{BASE}/{pos_id}/attachments", headers=headers).json()
    listed_ids = [i["id"] for i in items]
    assert all(i in listed_ids for i in ids)

    for att_id in ids:
        client.delete(f"{BASE}/{pos_id}/attachments/{att_id}", headers=headers)
