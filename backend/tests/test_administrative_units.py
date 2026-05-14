from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/admin-units"
TREE_BASE = "/api/v1/admin-hierarchies/tree"
CODE = "TEST_ADMIN_001"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_OFFICER_EMAIL = "hrofficer@hrms.local"


def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient) -> dict:
    return _login(client)


def _officer(client: TestClient) -> dict:
    return _login(client, _OFFICER_EMAIL)


def _delete_by_code(client: TestClient, code: str) -> None:
    resp = client.get(BASE, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    for item in resp.json()["items"]:
        if item["code"] == code:
            client.delete(f"{BASE}/{item['id']}", headers=_admin(client))


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
    }, headers=_admin(client))
    assert seed_resp.status_code == 200, seed_resp.text
    seed_old_resp = client.post(f"{BASE}/import", json={
        "system_type": "old",
        "source_name": "official_import_old",
        "source_version": "legacy_3_level",
        "mode": "merge",
    }, headers=_admin(client))
    assert seed_old_resp.status_code == 200, seed_old_resp.text
    yield


@pytest.fixture(autouse=True)
async def session_cleanup(client: TestClient):
    await _hard_delete_test_units()
    yield
    await _hard_delete_test_units()


def test_list_admin_units_returns_200(client: TestClient):
    resp = client.get(BASE, params={"unit_type": "province"}, headers=_admin(client))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["items"], list)
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] >= len(data["items"])


def test_list_admin_units_supports_server_side_pagination(client: TestClient):
    resp = client.get(BASE, params={"unit_type": "province", "page": 2, "page_size": 5}, headers=_admin(client))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 5
    assert data["page"] == 2
    assert data["page_size"] == 5
    assert data["total"] >= 34


def test_list_admin_units_old_system_returns_seeded_rows(client: TestClient):
    resp = client.get(BASE, params={"system_type": "old", "unit_type": "province"}, headers=_admin(client))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert data["total"] >= len(data["items"])
    assert any(item["source_code"] == "01" for item in data["items"])


def test_create_admin_unit_success(client: TestClient):
    resp = client.post(BASE, json=_payload("TEST_ADMIN_101"), headers=_admin(client))
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["code"] == "TEST_ADMIN_101"
    assert data["unit_type"] == "ward"
    assert data["province_code"] == "25"


def test_create_duplicate_admin_unit_409(client: TestClient):
    r1 = client.post(BASE, json=_payload("TEST_ADMIN_102"), headers=_admin(client))
    assert r1.status_code == 201, r1.text

    r2 = client.post(BASE, json=_payload("TEST_ADMIN_102"), headers=_admin(client))
    assert r2.status_code == 409


def test_get_admin_unit_by_id(client: TestClient):
    created = client.post(BASE, json=_payload("TEST_ADMIN_103"), headers=_admin(client)).json()

    resp = client.get(f"{BASE}/{created['id']}", headers=_admin(client))
    assert resp.status_code == 200
    assert resp.json()["code"] == "TEST_ADMIN_103"


def test_update_admin_unit_success(client: TestClient):
    created = client.post(BASE, json=_payload("TEST_ADMIN_104"), headers=_admin(client)).json()

    resp = client.put(f"{BASE}/{created['id']}", json={"name": "Phường Test API Updated"}, headers=_admin(client))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Phường Test API Updated"
    assert resp.json()["updated_at"] is not None


def test_delete_admin_unit_soft_deactivate(client: TestClient):
    created = client.post(BASE, json=_payload("TEST_ADMIN_105"), headers=_admin(client)).json()

    resp = client.delete(f"{BASE}/{created['id']}", headers=_admin(client))
    assert resp.status_code == 200
    assert "Đã khóa" in resp.json()["message"]

    after = client.get(f"{BASE}/{created['id']}", headers=_admin(client)).json()
    assert after["is_active"] is False


def test_get_hierarchy_tree_new_system(client: TestClient):
    resp = client.get(TREE_BASE, params={"system_type": "new"}, headers=_admin(client))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert data[0]["unit_type"] == "province"
        assert "children" in data[0]


def test_get_hierarchy_tree_old_system(client: TestClient):
    resp = client.get(TREE_BASE, params={"system_type": "old"}, headers=_admin(client))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(node["source_code"] == "01" for node in data)


def test_import_endpoint_works(client: TestClient):
    resp = client.post(f"{BASE}/import", json={
        "system_type": "new",
        "source_name": "official_import",
        "source_version": "qd19_2025",
        "mode": "merge",
    }, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["batch_status"] in {"success", "failed"}
    assert data["total_rows"] >= 1


def test_import_batches_returns_200(client: TestClient):
    resp = client.get(f"{BASE}/import-batches", headers=_admin(client))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_admin_units_requires_token(client: TestClient):
    resp = client.get(BASE)
    assert resp.status_code == 401


def test_officer_cannot_view_admin_units(client: TestClient):
    resp = client.get(BASE, headers=_officer(client))
    assert resp.status_code == 403


def test_create_admin_unit_writes_audit_log(client: TestClient):
    created = client.post(BASE, json=_payload("TEST_ADMIN_106"), headers=_admin(client))
    assert created.status_code == 201, created.text

    logs = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "administrative_unit", "action": "CREATE", "limit": 10},
        headers=_admin(client),
    )
    assert logs.status_code == 200, logs.text
    assert any(row["entity_name"] == "Phường Test TEST_ADMIN_106" for row in logs.json())


def test_import_writes_audit_log(client: TestClient):
    resp = client.post(f"{BASE}/import", json={
        "system_type": "new",
        "source_name": "official_import",
        "source_version": "qd19_2025",
        "mode": "merge",
    }, headers=_admin(client))
    assert resp.status_code == 200, resp.text

    logs = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "administrative_import_batch", "action": "IMPORT", "limit": 10},
        headers=_admin(client),
    )
    assert logs.status_code == 200, logs.text
    assert any(row["entity_name"] == "official_import:qd19_2025" for row in logs.json())
