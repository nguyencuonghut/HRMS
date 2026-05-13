"""Integration tests cho /api/v1/org-history."""
import pytest
from fastapi.testclient import TestClient

BASE     = "/api/v1/org-history"
DEPT_URL = "/api/v1/departments"
JT_URL   = "/api/v1/job-titles"
POS_URL  = "/api/v1/job-positions"

_DEPT_CODE = "TEST_HIST_DEPT"
_JT_CODE   = "TEST_HIST_JT"
_POS_CODE  = "TEST_HIST_POS"


# ── Setup / teardown ───────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def seed_history(client: TestClient):
    """Tạo một số thao tác để có dữ liệu log."""
    # Dọn trước
    for d in client.get(DEPT_URL).json():
        if d["code"] == _DEPT_CODE:
            client.delete(f"{DEPT_URL}/{d['id']}")
    for jt in client.get(JT_URL).json():
        if jt["code"] == _JT_CODE:
            client.delete(f"{JT_URL}/{jt['id']}")
    for p in client.get(POS_URL).json():
        if p["code"] == _POS_CODE:
            client.delete(f"{POS_URL}/{p['id']}")

    # Tạo dept → log create
    dept = client.post(DEPT_URL, json={"code": _DEPT_CODE, "name": "Hist Dept", "dept_type": "PHONG"}).json()
    # Sửa dept → log update
    client.put(f"{DEPT_URL}/{dept['id']}", json={"name": "Hist Dept Updated"})

    # Tạo job_title → log create
    jt = client.post(JT_URL, json={"code": _JT_CODE, "name": "Hist JT", "level": 3}).json()

    # Tạo job_position → log create
    pos = client.post(POS_URL, json={"code": _POS_CODE, "name": "Hist Pos", "department_id": dept["id"]}).json()
    # Sửa position → log update
    client.put(f"{POS_URL}/{pos['id']}", json={"name": "Hist Pos Updated"})

    yield

    # Cleanup
    client.delete(f"{POS_URL}/{pos['id']}")
    client.delete(f"{DEPT_URL}/{dept['id']}")
    client.delete(f"{JT_URL}/{jt['id']}")


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_list_returns_200(client: TestClient):
    resp = client.get(BASE)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_has_data(client: TestClient):
    items = client.get(BASE).json()
    assert len(items) > 0


def test_required_fields_present(client: TestClient):
    item = client.get(BASE).json()[0]
    for field in ("id", "entity_type", "entity_label", "entity_id", "entity_name",
                  "action", "action_label", "changed_at"):
        assert field in item, f"Thiếu field: {field}"


def test_entity_label_mapped(client: TestClient):
    items = client.get(BASE).json()
    labels = {i["entity_label"] for i in items}
    # Sau seed_history phải có ít nhất Phòng/Ban và Chức danh
    assert "Phòng/Ban" in labels
    assert "Chức danh" in labels


def test_action_label_mapped(client: TestClient):
    items = client.get(BASE).json()
    action_labels = {i["action_label"] for i in items}
    assert "Tạo mới" in action_labels
    assert "Cập nhật" in action_labels


def test_filter_by_entity_type_department(client: TestClient):
    resp = client.get(BASE, params={"entity_type": "department"})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) > 0
    assert all(i["entity_type"] == "department" for i in items)


def test_filter_by_entity_type_job_title(client: TestClient):
    resp = client.get(BASE, params={"entity_type": "job_title"})
    assert resp.status_code == 200
    assert all(i["entity_type"] == "job_title" for i in resp.json())


def test_filter_by_entity_type_job_position(client: TestClient):
    resp = client.get(BASE, params={"entity_type": "job_position"})
    assert resp.status_code == 200
    assert all(i["entity_type"] == "job_position" for i in resp.json())


def test_filter_date_from(client: TestClient):
    resp = client.get(BASE, params={"date_from": "2020-01-01"})
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_filter_date_to_excludes_future(client: TestClient):
    resp = client.get(BASE, params={"date_to": "2000-01-01"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_limit_param(client: TestClient):
    resp = client.get(BASE, params={"limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()) <= 2


def test_create_action_has_no_old_data(client: TestClient):
    items = client.get(BASE, params={"entity_type": "department"}).json()
    creates = [i for i in items if i["action"] == "create"]
    assert len(creates) > 0
    assert all(i["old_data"] is None for i in creates)


def test_update_action_has_both_snapshots(client: TestClient):
    items = client.get(BASE, params={"entity_type": "department"}).json()
    updates = [i for i in items if i["action"] == "update"]
    assert len(updates) > 0
    for u in updates:
        assert u["old_data"] is not None
        assert u["new_data"] is not None


def test_ordered_by_changed_at_desc(client: TestClient):
    items = client.get(BASE).json()
    times = [i["changed_at"] for i in items]
    assert times == sorted(times, reverse=True)
