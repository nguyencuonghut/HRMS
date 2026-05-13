"""Integration tests cho attachment endpoints của /api/v1/job-positions."""
import io
import pytest
from fastapi.testclient import TestClient

BASE     = "/api/v1/job-positions"
DEPT_URL = "/api/v1/departments"
JT_URL   = "/api/v1/job-titles"

_POS_CODE  = "TEST_ATT_POS"
_DEPT_CODE = "TEST_DEPT_ATT"


# ── Session setup ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def dept_id(client: TestClient) -> int:
    for d in client.get(DEPT_URL).json():
        if d["code"] == _DEPT_CODE:
            client.delete(f"{DEPT_URL}/{d['id']}")
    r = client.post(DEPT_URL, json={"code": _DEPT_CODE, "name": "Test Dept Att", "dept_type": "PHONG"})
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture(scope="session")
def pos_id(client: TestClient, dept_id: int) -> int:
    for p in client.get(BASE).json():
        if p["code"] == _POS_CODE:
            client.delete(f"{BASE}/{p['id']}")
    r = client.post(BASE, json={"code": _POS_CODE, "name": "Test Pos Att", "department_id": dept_id})
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture(scope="session", autouse=True)
def session_cleanup(client: TestClient, dept_id: int, pos_id: int):
    yield
    client.delete(f"{BASE}/{pos_id}")
    client.delete(f"{DEPT_URL}/{dept_id}")


def _fake_file(name: str = "test.pdf", content: bytes = b"dummy pdf content") -> dict:
    return {"file": (name, io.BytesIO(content), "application/pdf")}


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_list_attachments_empty(client: TestClient, pos_id: int):
    resp = client.get(f"{BASE}/{pos_id}/attachments")
    assert resp.status_code == 200
    assert resp.json() == []


def test_upload_attachment(client: TestClient, pos_id: int):
    resp = client.post(
        f"{BASE}/{pos_id}/attachments",
        files=_fake_file("jd.pdf", b"job description content"),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["file_name"] == "jd.pdf"
    assert data["file_size"] == len(b"job description content")
    assert "attachments/" in data["file_path"]
    # cleanup
    client.delete(f"{BASE}/{pos_id}/attachments/{data['id']}")


def test_list_attachments_after_upload(client: TestClient, pos_id: int):
    r = client.post(f"{BASE}/{pos_id}/attachments", files=_fake_file("cv.pdf"))
    assert r.status_code == 201
    att_id = r.json()["id"]

    items = client.get(f"{BASE}/{pos_id}/attachments").json()
    assert any(i["id"] == att_id for i in items)

    client.delete(f"{BASE}/{pos_id}/attachments/{att_id}")


def test_delete_attachment(client: TestClient, pos_id: int):
    r = client.post(f"{BASE}/{pos_id}/attachments", files=_fake_file("del.pdf"))
    att_id = r.json()["id"]

    resp = client.delete(f"{BASE}/{pos_id}/attachments/{att_id}")
    assert resp.status_code == 200
    assert "Đã xóa" in resp.json()["message"]

    items = client.get(f"{BASE}/{pos_id}/attachments").json()
    assert not any(i["id"] == att_id for i in items)


def test_delete_attachment_not_found(client: TestClient, pos_id: int):
    assert client.delete(f"{BASE}/{pos_id}/attachments/999999").status_code == 404


def test_list_attachments_invalid_position(client: TestClient):
    assert client.get(f"{BASE}/999999/attachments").status_code == 404


def test_upload_to_invalid_position(client: TestClient):
    resp = client.post(f"{BASE}/999999/attachments", files=_fake_file())
    assert resp.status_code == 404


def test_multiple_attachments(client: TestClient, pos_id: int):
    ids = []
    for name in ["a.pdf", "b.docx", "c.txt"]:
        r = client.post(f"{BASE}/{pos_id}/attachments", files=_fake_file(name))
        assert r.status_code == 201
        ids.append(r.json()["id"])

    items = client.get(f"{BASE}/{pos_id}/attachments").json()
    listed_ids = [i["id"] for i in items]
    assert all(i in listed_ids for i in ids)

    for att_id in ids:
        client.delete(f"{BASE}/{pos_id}/attachments/{att_id}")
