"""Integration tests cho /api/v1/org-history."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BASE     = "/api/v1/org-history"
DEPT_URL = "/api/v1/departments"
JT_URL   = "/api/v1/job-titles"
POS_URL  = "/api/v1/job-positions"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"

_RUN_SUFFIX = uuid4().hex[:6].upper()
_DEPT_CODE = f"THD{_RUN_SUFFIX}"
_JT_CODE   = f"THJ{_RUN_SUFFIX}"
_POS_CODE  = f"THP{_RUN_SUFFIX}"


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Setup / teardown ───────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def seed_history(client: TestClient):
    """Tạo một số thao tác để có dữ liệu log."""
    headers = _admin(client)

    # Tạo dept → log create
    dept_resp = client.post(
        DEPT_URL,
        json={"code": _DEPT_CODE, "name": "Hist Dept", "dept_type": "PHONG"},
        headers=headers,
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept = dept_resp.json()
    # Sửa dept → log update
    dept_update = client.put(
        f"{DEPT_URL}/{dept['id']}",
        json={"name": "Hist Dept Updated"},
        headers=headers,
    )
    assert dept_update.status_code == 200, dept_update.text

    # Tạo job_title → log create
    jt_resp = client.post(
        JT_URL,
        json={"code": _JT_CODE, "name": "Hist JT", "level": 3},
        headers=headers,
    )
    assert jt_resp.status_code == 201, jt_resp.text
    jt = jt_resp.json()

    # Tạo job_position → log create
    pos_resp = client.post(
        POS_URL,
        json={"code": _POS_CODE, "name": "Hist Pos", "department_id": dept["id"]},
        headers=headers,
    )
    assert pos_resp.status_code == 201, pos_resp.text
    pos = pos_resp.json()
    # Sửa position → log update
    pos_update = client.put(
        f"{POS_URL}/{pos['id']}",
        json={"name": "Hist Pos Updated"},
        headers=headers,
    )
    assert pos_update.status_code == 200, pos_update.text

    yield

    # Cleanup
    client.delete(f"{POS_URL}/{pos['id']}", headers=headers)
    client.delete(f"{DEPT_URL}/{dept['id']}", headers=headers)
    client.delete(f"{JT_URL}/{jt['id']}", headers=headers)


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_list_returns_200(client: TestClient):
    resp = client.get(BASE)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)


def test_list_has_data(client: TestClient):
    items = client.get(BASE).json()["items"]
    assert len(items) > 0


def test_required_fields_present(client: TestClient):
    item = client.get(BASE).json()["items"][0]
    for field in ("id", "entity_type", "entity_label", "entity_id", "entity_name",
                  "action", "action_label", "changed_at"):
        assert field in item, f"Thiếu field: {field}"


def test_entity_label_mapped(client: TestClient):
    items = client.get(BASE).json()["items"]
    labels = {i["entity_label"] for i in items}
    # Sau seed_history phải có ít nhất Phòng/Ban và Chức danh
    assert "Phòng/Ban" in labels
    assert "Chức danh" in labels


def test_action_label_mapped(client: TestClient):
    items = client.get(BASE).json()["items"]
    action_labels = {i["action_label"] for i in items}
    assert "Tạo mới" in action_labels
    assert "Cập nhật" in action_labels


def test_filter_by_entity_type_department(client: TestClient):
    resp = client.get(BASE, params={"entity_type": "department"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) > 0
    assert all(i["entity_type"] == "department" for i in items)


def test_filter_by_entity_type_job_title(client: TestClient):
    resp = client.get(BASE, params={"entity_type": "job_title"})
    assert resp.status_code == 200
    assert all(i["entity_type"] == "job_title" for i in resp.json()["items"])


def test_filter_by_entity_type_job_position(client: TestClient):
    resp = client.get(BASE, params={"entity_type": "job_position"})
    assert resp.status_code == 200
    assert all(i["entity_type"] == "job_position" for i in resp.json()["items"])


def test_filter_date_from(client: TestClient):
    resp = client.get(BASE, params={"date_from": "2020-01-01"})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) > 0


def test_filter_date_to_excludes_future(client: TestClient):
    resp = client.get(BASE, params={"date_to": "2000-01-01"})
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_limit_param(client: TestClient):
    resp = client.get(BASE, params={"page_size": 2})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) <= 2


def test_create_action_has_no_old_data(client: TestClient):
    items = client.get(BASE, params={"entity_type": "department"}).json()["items"]
    creates = [i for i in items if i["action"] == "create"]
    assert len(creates) > 0
    assert all(i["old_data"] is None for i in creates)


def test_update_action_has_both_snapshots(client: TestClient):
    items = client.get(BASE, params={"entity_type": "department"}).json()["items"]
    updates = [i for i in items if i["action"] == "update"]
    assert len(updates) > 0
    for u in updates:
        assert u["old_data"] is not None
        assert u["new_data"] is not None


def test_ordered_by_changed_at_desc(client: TestClient):
    items = client.get(BASE).json()["items"]
    times = [i["changed_at"] for i in items]
    assert times == sorted(times, reverse=True)
