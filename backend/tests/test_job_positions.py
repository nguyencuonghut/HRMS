"""Integration tests cho /api/v1/job-positions."""
import pytest
from fastapi.testclient import TestClient

BASE     = "/api/v1/job-positions"
DEPT_URL = "/api/v1/departments"
JT_URL   = "/api/v1/job-titles"

_POS_CODE  = "TEST_POS_001"
_POS_CODE2 = "TEST_POS_002"
_DEPT_CODE = "TEST_DEPT_JP"
_DEPT_CODE2 = "TEST_DEPT_JP_2"
_JT_CODE   = "TEST_JT_JP"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Session setup: tạo/dọn prerequisite data ──────────────────────────────────

@pytest.fixture(scope="session")
def dept_id(client: TestClient) -> int:
    headers = _admin(client)
    # Dọn nếu tồn tại
    for d in client.get(DEPT_URL, headers=headers).json():
        if d["code"] == _DEPT_CODE:
            client.delete(f"{DEPT_URL}/{d['id']}", headers=headers)
    r = client.post(
        DEPT_URL,
        json={"code": _DEPT_CODE, "name": "Test Dept JP", "dept_type": "PHONG"},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture(scope="session")
def dept_id_2(client: TestClient) -> int:
    headers = _admin(client)
    for d in client.get(DEPT_URL, headers=headers).json():
        if d["code"] == _DEPT_CODE2:
            client.delete(f"{DEPT_URL}/{d['id']}", headers=headers)
    r = client.post(
        DEPT_URL,
        json={"code": _DEPT_CODE2, "name": "Test Dept JP 2", "dept_type": "PHONG"},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture(scope="session")
def jt_id(client: TestClient) -> int:
    headers = _admin(client)
    for jt in client.get(JT_URL, headers=headers).json():
        if jt["code"] == _JT_CODE:
            client.delete(f"{JT_URL}/{jt['id']}", headers=headers)
    r = client.post(
        JT_URL,
        json={"code": _JT_CODE, "name": "Test JT JP", "level": 5},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


def _delete_pos_by_code(client: TestClient, code: str) -> None:
    headers = _admin(client)
    for item in client.get(BASE, headers=headers).json():
        if item["code"] == code:
            client.delete(f"{BASE}/{item['id']}", headers=headers)


@pytest.fixture(scope="session", autouse=True)
def session_cleanup(client: TestClient, dept_id: int, dept_id_2: int, jt_id: int):
    headers = _admin(client)
    _delete_pos_by_code(client, _POS_CODE)
    _delete_pos_by_code(client, _POS_CODE2)
    yield
    _delete_pos_by_code(client, _POS_CODE)
    _delete_pos_by_code(client, _POS_CODE2)
    # Dọn prerequisite
    client.delete(f"{DEPT_URL}/{dept_id}", headers=headers)
    client.delete(f"{DEPT_URL}/{dept_id_2}", headers=headers)
    client.delete(f"{JT_URL}/{jt_id}", headers=headers)


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_list_returns_200(client: TestClient):
    resp = client.get(BASE, headers=_admin(client))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_success(client: TestClient, dept_id: int):
    headers = _admin(client)
    resp = client.post(BASE, json={
        "code": _POS_CODE, "name": "Test Vị trí",
        "department_id": dept_id, "default_grade": 2,
        "bhxh_allowance": 500000, "non_bhxh_allowance": 200000,
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == _POS_CODE
    assert data["name"] == "Test Vị trí"
    assert data["department_id"] == dept_id
    assert data["bhxh_allowance"] == 500000
    assert data["is_active"] is True
    client.delete(f"{BASE}/{data['id']}", headers=headers)


def test_create_with_job_title(client: TestClient, dept_id: int, jt_id: int):
    headers = _admin(client)
    resp = client.post(BASE, json={
        "code": _POS_CODE, "name": "Vị trí có chức danh",
        "department_id": dept_id, "job_title_id": jt_id,
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["job_title_id"] == jt_id
    client.delete(f"{BASE}/{resp.json()['id']}", headers=headers)


def test_create_code_auto_uppercase(client: TestClient, dept_id: int):
    headers = _admin(client)
    resp = client.post(BASE, json={
        "code": "test_pos_001", "name": "Upper Test",
        "department_id": dept_id,
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["code"] == _POS_CODE
    client.delete(f"{BASE}/{resp.json()['id']}", headers=headers)


def test_create_duplicate_code_409(client: TestClient, dept_id: int):
    headers = _admin(client)
    r1 = client.post(BASE, json={"code": _POS_CODE, "name": "First", "department_id": dept_id}, headers=headers)
    assert r1.status_code == 201
    r2 = client.post(BASE, json={"code": _POS_CODE, "name": "Dup",   "department_id": dept_id}, headers=headers)
    assert r2.status_code == 409
    client.delete(f"{BASE}/{r1.json()['id']}", headers=headers)


def test_create_invalid_dept_404(client: TestClient):
    resp = client.post(BASE, json={"code": _POS_CODE, "name": "Bad dept", "department_id": 999999}, headers=_admin(client))
    assert resp.status_code == 404


def test_create_invalid_jt_404(client: TestClient, dept_id: int):
    headers = _admin(client)
    resp = client.post(BASE, json={
        "code": _POS_CODE, "name": "Bad JT",
        "department_id": dept_id, "job_title_id": 999999,
    }, headers=headers)
    assert resp.status_code == 404


def test_get_by_id(client: TestClient, dept_id: int):
    headers = _admin(client)
    r = client.post(BASE, json={"code": _POS_CODE, "name": "Detail test", "department_id": dept_id}, headers=headers)
    pos_id = r.json()["id"]
    resp = client.get(f"{BASE}/{pos_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == pos_id
    client.delete(f"{BASE}/{pos_id}", headers=headers)


def test_get_not_found_404(client: TestClient):
    assert client.get(f"{BASE}/999999", headers=_admin(client)).status_code == 404


def test_update_success(client: TestClient, dept_id: int):
    headers = _admin(client)
    r = client.post(BASE, json={"code": _POS_CODE, "name": "Original", "department_id": dept_id}, headers=headers)
    pos_id = r.json()["id"]
    resp = client.put(f"{BASE}/{pos_id}", json={"name": "Updated", "bhxh_allowance": 1000000}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"
    assert resp.json()["bhxh_allowance"] == 1000000
    client.delete(f"{BASE}/{pos_id}", headers=headers)


def test_update_deactivate(client: TestClient, dept_id: int):
    headers = _admin(client)
    r = client.post(BASE, json={"code": _POS_CODE, "name": "Active", "department_id": dept_id}, headers=headers)
    pos_id = r.json()["id"]
    resp = client.put(f"{BASE}/{pos_id}", json={"is_active": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    client.delete(f"{BASE}/{pos_id}", headers=headers)


def test_update_not_found_404(client: TestClient):
    assert client.put(f"{BASE}/999999", json={"name": "ghost"}, headers=_admin(client)).status_code == 404


def test_delete_success(client: TestClient, dept_id: int):
    headers = _admin(client)
    r = client.post(BASE, json={"code": _POS_CODE, "name": "To delete", "department_id": dept_id}, headers=headers)
    pos_id = r.json()["id"]
    resp = client.delete(f"{BASE}/{pos_id}", headers=headers)
    assert resp.status_code == 200
    assert "Đã xóa" in resp.json()["message"]
    assert client.get(f"{BASE}/{pos_id}", headers=headers).status_code == 404


def test_delete_not_found_404(client: TestClient):
    assert client.delete(f"{BASE}/999999", headers=_admin(client)).status_code == 404


def test_filter_by_department(client: TestClient, dept_id: int):
    headers = _admin(client)
    r = client.post(BASE, json={"code": _POS_CODE, "name": "Dept filter", "department_id": dept_id}, headers=headers)
    pos_id = r.json()["id"]
    resp = client.get(BASE, params={"department_id": dept_id}, headers=headers)
    assert resp.status_code == 200
    assert any(i["id"] == pos_id for i in resp.json())
    client.delete(f"{BASE}/{pos_id}", headers=headers)


def test_create_shared_position_with_assigned_departments(client: TestClient, dept_id: int, dept_id_2: int):
    headers = _admin(client)
    resp = client.post(
        BASE,
        json={
            "code": _POS_CODE,
            "name": "Shared Position",
            "department_id": dept_id,
            "assigned_department_ids": [dept_id, dept_id_2],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["department_id"] == dept_id
    assert sorted(data["assigned_department_ids"]) == sorted([dept_id, dept_id_2])
    assert data["is_shared"] is True
    assert {item["id"] for item in data["assigned_departments"]} == {dept_id, dept_id_2}
    client.delete(f"{BASE}/{data['id']}", headers=headers)


def test_get_by_id_returns_assigned_departments(client: TestClient, dept_id: int, dept_id_2: int):
    headers = _admin(client)
    create = client.post(
        BASE,
        json={
            "code": _POS_CODE,
            "name": "Detail Shared",
            "department_id": dept_id,
            "assigned_department_ids": [dept_id_2],
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    pos_id = create.json()["id"]

    resp = client.get(f"{BASE}/{pos_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert {item["id"] for item in data["assigned_departments"]} == {dept_id, dept_id_2}
    client.delete(f"{BASE}/{pos_id}", headers=headers)


def test_update_assigned_departments(client: TestClient, dept_id: int, dept_id_2: int):
    headers = _admin(client)
    create = client.post(
        BASE,
        json={"code": _POS_CODE, "name": "Update Shared", "department_id": dept_id},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    pos_id = create.json()["id"]

    update = client.put(
        f"{BASE}/{pos_id}",
        json={"assigned_department_ids": [dept_id, dept_id_2]},
        headers=headers,
    )
    assert update.status_code == 200, update.text
    data = update.json()
    assert sorted(data["assigned_department_ids"]) == sorted([dept_id, dept_id_2])
    assert data["is_shared"] is True
    client.delete(f"{BASE}/{pos_id}", headers=headers)


def test_filter_by_department_includes_shared_mapping(client: TestClient, dept_id: int, dept_id_2: int):
    headers = _admin(client)
    create = client.post(
        BASE,
        json={
            "code": _POS_CODE,
            "name": "Shared Filter",
            "department_id": dept_id,
            "assigned_department_ids": [dept_id_2],
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    pos_id = create.json()["id"]

    resp = client.get(BASE, params={"department_id": dept_id_2}, headers=headers)
    assert resp.status_code == 200
    assert any(item["id"] == pos_id for item in resp.json())
    client.delete(f"{BASE}/{pos_id}", headers=headers)


def test_filter_by_is_active(client: TestClient, dept_id: int):
    headers = _admin(client)
    r1 = client.post(BASE, json={"code": _POS_CODE,  "name": "Active",   "department_id": dept_id}, headers=headers)
    r2 = client.post(BASE, json={"code": _POS_CODE2, "name": "Inactive", "department_id": dept_id}, headers=headers)
    client.put(f"{BASE}/{r2.json()['id']}", json={"is_active": False}, headers=headers)

    active_ids   = [i["id"] for i in client.get(BASE, params={"is_active": "true"}, headers=headers).json()]
    inactive_ids = [i["id"] for i in client.get(BASE, params={"is_active": "false"}, headers=headers).json()]

    assert r1.json()["id"] in active_ids   and r2.json()["id"] not in active_ids
    assert r2.json()["id"] in inactive_ids and r1.json()["id"] not in inactive_ids

    client.delete(f"{BASE}/{r1.json()['id']}", headers=headers)
    client.delete(f"{BASE}/{r2.json()['id']}", headers=headers)


def test_search(client: TestClient, dept_id: int):
    headers = _admin(client)
    r = client.post(BASE, json={"code": _POS_CODE, "name": "UniqueSearchTerm XYZ", "department_id": dept_id}, headers=headers)
    pos_id = r.json()["id"]
    resp = client.get(BASE, params={"search": "UniqueSearchTerm"}, headers=headers)
    assert resp.status_code == 200
    assert any(i["id"] == pos_id for i in resp.json())
    client.delete(f"{BASE}/{pos_id}", headers=headers)


def test_list_includes_department_name(client: TestClient, dept_id: int):
    headers = _admin(client)
    r = client.post(BASE, json={"code": _POS_CODE, "name": "Joined test", "department_id": dept_id}, headers=headers)
    pos_id = r.json()["id"]
    items = client.get(BASE, headers=headers).json()
    item = next(i for i in items if i["id"] == pos_id)
    assert item["department_name"] == "Test Dept JP"
    client.delete(f"{BASE}/{pos_id}", headers=headers)
