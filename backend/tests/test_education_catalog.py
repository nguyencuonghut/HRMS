from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds import education_catalog

LEVEL_BASE = "/api/v1/education-levels"
INSTITUTION_BASE = "/api/v1/educational-institutions"
MAJOR_BASE = "/api/v1/education-majors"
LOOKUP_LEVELS = "/api/v1/lookups/education-levels"
LOOKUP_INSTITUTIONS = "/api/v1/lookups/educational-institutions"
LOOKUP_MAJORS = "/api/v1/lookups/education-majors"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_OFFICER_EMAIL = "hrofficer@hrms.local"


def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict:
    token = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient) -> dict:
    return _login(client)


def _officer(client: TestClient) -> dict:
    return _login(client, _OFFICER_EMAIL)


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup_test_rows():
    async with _make_session()() as s:
        await s.execute(text("DELETE FROM education_levels WHERE code LIKE 'test_level_%'"))
        await s.execute(text("DELETE FROM educational_institutions WHERE code LIKE 'TEST_INSTITUTION_%'"))
        await s.execute(text("DELETE FROM education_majors WHERE code LIKE 'test_major_%'"))
        await s.commit()


import pytest


@pytest.fixture(scope="session", autouse=True)
async def seed_education_catalog_data():
    async with _make_session()() as session:
        await education_catalog.seed_required_education_catalog(session)
        await education_catalog.seed_sample_education_catalog(session)
        await session.commit()
    yield


@pytest.fixture(autouse=True)
async def session_cleanup():
    await _cleanup_test_rows()
    yield
    await _cleanup_test_rows()


def test_list_education_levels_returns_page(client: TestClient):
    resp = client.get(LEVEL_BASE, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 8
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert any(item["code"] == "bachelor" for item in body["items"])


def test_list_educational_institutions_supports_filters(client: TestClient):
    resp = client.get(
        INSTITUTION_BASE,
        params={"keyword": "nha trang", "institution_type": "university", "page_size": 10},
        headers=_admin(client),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert any(item["code"] == "NTU" for item in body["items"])


def test_create_and_update_education_level_success(client: TestClient):
    create_resp = client.post(
        LEVEL_BASE,
        json={"code": "test_level_api_001", "name": "Chứng chỉ nghề", "rank_no": 99},
        headers=_admin(client),
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["code"] == "test_level_api_001"
    assert created["rank_no"] == 99

    update_resp = client.put(
        f"{LEVEL_BASE}/{created['id']}",
        json={"name": "Chứng chỉ nghề nâng cao", "rank_no": 98},
        headers=_admin(client),
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["name"] == "Chứng chỉ nghề nâng cao"
    assert updated["rank_no"] == 98

    logs = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "education_level", "action": "UPDATE", "page_size": 10},
        headers=_admin(client),
    )
    assert logs.status_code == 200, logs.text
    payload = logs.json()
    assert any(row["entity_name"] == "Chứng chỉ nghề nâng cao" for row in payload["items"])


def test_create_educational_institution_writes_audit_log(client: TestClient):
    resp = client.post(
        INSTITUTION_BASE,
        json={
            "code": "TEST_INSTITUTION_001",
            "name": "Trường Cao đẳng Nông nghiệp Test",
            "short_name": "CĐ NN Test",
            "institution_type": "college",
            "country_code": "vn",
            "province_code": "19",
        },
        headers=_admin(client),
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["country_code"] == "VN"

    logs = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "educational_institution", "action": "CREATE", "page_size": 10},
        headers=_admin(client),
    )
    assert logs.status_code == 200, logs.text
    payload = logs.json()
    assert any(row["entity_name"] == "Trường Cao đẳng Nông nghiệp Test" for row in payload["items"])


def test_delete_education_major_soft_deactivate(client: TestClient):
    created = client.post(
        MAJOR_BASE,
        json={"code": "test_major_api_001", "name": "Công nghệ thức ăn thủy sản", "major_group": "aquaculture"},
        headers=_admin(client),
    )
    assert created.status_code == 201, created.text

    delete_resp = client.delete(f"{MAJOR_BASE}/{created.json()['id']}", headers=_admin(client))
    assert delete_resp.status_code == 200, delete_resp.text

    detail = client.get(f"{MAJOR_BASE}/{created.json()['id']}", headers=_admin(client))
    assert detail.status_code == 200, detail.text
    assert detail.json()["is_active"] is False

    logs = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "education_major", "action": "DELETE", "page_size": 10},
        headers=_admin(client),
    )
    assert logs.status_code == 200, logs.text
    payload = logs.json()
    assert any(row["entity_name"] == "Công nghệ thức ăn thủy sản" for row in payload["items"])


def test_delete_educational_institution_writes_audit_log(client: TestClient):
    created = client.post(
        INSTITUTION_BASE,
        json={
            "code": "TEST_INSTITUTION_002",
            "name": "Trường Đại học Nông nghiệp Vận hành",
            "short_name": "ĐHNN Vận hành",
            "institution_type": "university",
            "country_code": "VN",
        },
        headers=_admin(client),
    )
    assert created.status_code == 201, created.text

    deleted = client.delete(f"{INSTITUTION_BASE}/{created.json()['id']}", headers=_admin(client))
    assert deleted.status_code == 200, deleted.text

    logs = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "educational_institution", "action": "DELETE", "page_size": 10},
        headers=_admin(client),
    )
    assert logs.status_code == 200, logs.text
    payload = logs.json()
    assert any(row["entity_name"] == "Trường Đại học Nông nghiệp Vận hành" for row in payload["items"])


def test_lookup_education_levels_returns_active_sorted_rows(client: TestClient):
    resp = client.get(LOOKUP_LEVELS, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert rows[0]["code"] == "primary_school"
    assert rows[-1]["code"] == "doctor"


def test_lookup_educational_institutions_supports_keyword_search(client: TestClient):
    resp = client.get(LOOKUP_INSTITUTIONS, params={"keyword": "nong nghiep"}, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert any(row["code"] == "VNUA" for row in rows)


def test_lookup_education_majors_supports_keyword_search(client: TestClient):
    resp = client.get(LOOKUP_MAJORS, params={"keyword": "thuc an chan nuoi"}, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert any(row["code"] == "feed_nutrition" for row in rows)


def test_officer_cannot_delete_education_catalog_rows(client: TestClient):
    created = client.post(
        MAJOR_BASE,
        json={"code": "test_major_api_002", "name": "Quản trị trại giống", "major_group": "animal_science"},
        headers=_admin(client),
    )
    assert created.status_code == 201, created.text

    resp = client.delete(f"{MAJOR_BASE}/{created.json()['id']}", headers=_officer(client))
    assert resp.status_code == 403


def test_officer_can_view_and_edit_but_not_delete_catalog_rows(client: TestClient):
    created = client.post(
        LEVEL_BASE,
        json={"code": "test_level_api_002", "name": "Trình độ test HR Officer", "rank_no": 97},
        headers=_admin(client),
    )
    assert created.status_code == 201, created.text

    listed = client.get(LEVEL_BASE, headers=_officer(client))
    assert listed.status_code == 200, listed.text

    updated = client.put(
        f"{LEVEL_BASE}/{created.json()['id']}",
        json={"name": "Trình độ test HR Officer Updated"},
        headers=_officer(client),
    )
    assert updated.status_code == 200, updated.text

    deleted = client.delete(f"{LEVEL_BASE}/{created.json()['id']}", headers=_officer(client))
    assert deleted.status_code == 403


def test_education_catalog_admin_endpoints_require_token(client: TestClient):
    resp = client.get(INSTITUTION_BASE)
    assert resp.status_code == 401
