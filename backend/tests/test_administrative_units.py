from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/admin-units"
TREE_BASE = "/api/v1/admin-hierarchies/tree"
CODE = "TEST_ADMIN_001"


def _delete_by_code(client: TestClient, code: str) -> None:
    resp = client.get(BASE)
    assert resp.status_code == 200, resp.text
    for item in resp.json():
        if item["code"] == code:
            client.delete(f"{BASE}/{item['id']}")


def _payload(code: str) -> dict:
    return {
        "code": code,
        "name": f"Phường Test {code}",
        "unit_type": "ward",
        "province_code": "25",
        "official_name": f"Phường Test {code}",
    }


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _hard_delete_test_units():
    async with _make_session()() as s:
        await s.execute(text("""
            DELETE FROM administrative_hierarchies
            WHERE child_unit_id IN (
                SELECT id FROM administrative_units WHERE code LIKE 'TEST_ADMIN_%'
            )
               OR parent_unit_id IN (
                SELECT id FROM administrative_units WHERE code LIKE 'TEST_ADMIN_%'
            )
        """))
        await s.execute(text("DELETE FROM administrative_units WHERE code LIKE 'TEST_ADMIN_%'"))
        await s.commit()


import pytest


@pytest.fixture(scope="session", autouse=True)
def seed_official_import(client: TestClient):
    seed_resp = client.post(f"{BASE}/import", json={
        "system_type": "new",
        "source_name": "official_import",
        "source_version": "qd19_2025",
        "mode": "merge",
    })
    assert seed_resp.status_code == 200, seed_resp.text
    yield


@pytest.fixture(autouse=True)
async def session_cleanup(client: TestClient):
    await _hard_delete_test_units()
    yield
    await _hard_delete_test_units()


def test_list_admin_units_returns_200(client: TestClient):
    resp = client.get(BASE, params={"unit_type": "province"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["items"], list)
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] >= len(data["items"])


def test_list_admin_units_supports_server_side_pagination(client: TestClient):
    resp = client.get(BASE, params={"unit_type": "province", "page": 2, "page_size": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 5
    assert data["page"] == 2
    assert data["page_size"] == 5
    assert data["total"] >= 34


def test_list_admin_units_old_system_is_empty_when_old_hierarchy_not_seeded(client: TestClient):
    resp = client.get(BASE, params={"system_type": "old"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_create_admin_unit_success(client: TestClient):
    resp = client.post(BASE, json=_payload("TEST_ADMIN_101"))
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["code"] == "TEST_ADMIN_101"
    assert data["unit_type"] == "ward"
    assert data["province_code"] == "25"


def test_create_duplicate_admin_unit_409(client: TestClient):
    r1 = client.post(BASE, json=_payload("TEST_ADMIN_102"))
    assert r1.status_code == 201, r1.text

    r2 = client.post(BASE, json=_payload("TEST_ADMIN_102"))
    assert r2.status_code == 409


def test_get_admin_unit_by_id(client: TestClient):
    created = client.post(BASE, json=_payload("TEST_ADMIN_103")).json()

    resp = client.get(f"{BASE}/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["code"] == "TEST_ADMIN_103"


def test_update_admin_unit_success(client: TestClient):
    created = client.post(BASE, json=_payload("TEST_ADMIN_104")).json()

    resp = client.put(f"{BASE}/{created['id']}", json={"name": "Phường Test API Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Phường Test API Updated"
    assert resp.json()["updated_at"] is not None


def test_delete_admin_unit_soft_deactivate(client: TestClient):
    created = client.post(BASE, json=_payload("TEST_ADMIN_105")).json()

    resp = client.delete(f"{BASE}/{created['id']}")
    assert resp.status_code == 200
    assert "Đã khóa" in resp.json()["message"]

    after = client.get(f"{BASE}/{created['id']}").json()
    assert after["is_active"] is False


def test_get_hierarchy_tree_new_system(client: TestClient):
    resp = client.get(TREE_BASE, params={"system_type": "new"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert data[0]["unit_type"] == "province"
        assert "children" in data[0]


def test_get_hierarchy_tree_old_system_is_empty_when_not_seeded(client: TestClient):
    resp = client.get(TREE_BASE, params={"system_type": "old"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_import_endpoint_works(client: TestClient):
    resp = client.post(f"{BASE}/import", json={
        "system_type": "new",
        "source_name": "official_import",
        "source_version": "qd19_2025",
        "mode": "merge",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["batch_status"] in {"success", "failed"}
    assert data["total_rows"] >= 1


def test_import_batches_returns_200(client: TestClient):
    resp = client.get(f"{BASE}/import-batches")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
