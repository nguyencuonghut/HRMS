"""Integration tests cho Slice 0 shared insurance foundation."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/insurance"
_TEST_POLICY_CODE = "TEST_INS_POLICY"
_TEST_REGION_NOTE = "TEST_REGION_NOTE"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _cleanup():
    async with _make_session()() as s:
        await s.execute(
            text(
                """
                DELETE FROM insurance_policy_component_rates
                WHERE policy_version_id IN (
                    SELECT id FROM insurance_policy_versions WHERE code LIKE :code
                )
                """
            ),
            {"code": f"{_TEST_POLICY_CODE}%"},
        )
        await s.execute(
            text("DELETE FROM insurance_policy_versions WHERE code LIKE :code"),
            {"code": f"{_TEST_POLICY_CODE}%"},
        )
        await s.execute(
            text(
                """
                UPDATE insurance_policy_versions
                SET is_active = FALSE
                WHERE code NOT LIKE :code
                """
            ),
            {"code": f"{_TEST_POLICY_CODE}%"},
        )
        await s.execute(
            text(
                """
                WITH latest_non_test AS (
                    SELECT id
                    FROM insurance_policy_versions
                    WHERE code NOT LIKE :code
                    ORDER BY effective_from DESC, id DESC
                    LIMIT 1
                )
                UPDATE insurance_policy_versions
                SET is_active = TRUE,
                    effective_to = NULL
                WHERE id = (SELECT id FROM latest_non_test)
                """
            ),
            {"code": f"{_TEST_POLICY_CODE}%"},
        )
        await s.execute(
            text("DELETE FROM company_bhxh_region WHERE note LIKE :note"),
            {"note": f"{_TEST_REGION_NOTE}%"},
        )
        await s.execute(
            text(
                """
                WITH latest_non_test AS (
                    SELECT id
                    FROM company_bhxh_region
                    WHERE note IS NULL OR note NOT LIKE :note
                    ORDER BY effective_from DESC, id DESC
                    LIMIT 1
                )
                UPDATE company_bhxh_region
                SET effective_to = NULL
                WHERE id = (SELECT id FROM latest_non_test)
                """
            ),
            {"note": f"{_TEST_REGION_NOTE}%"},
        )
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    await _cleanup()
    yield
    await _cleanup()


def test_list_foundation_returns_seeded_policy_and_components(client: TestClient):
    resp = client.get(f"{BASE}/policy-versions", headers=_admin(client))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body, "Phải có ít nhất 1 policy version được seed"
    active = [item for item in body if item["is_active"]]
    assert len(active) == 1
    active_item = active[0]
    assert active_item["company_region"] == 3
    component_codes = [item["component_code"] for item in active_item["components"]]
    assert component_codes == [
        "RETIREMENT_SURVIVOR",
        "SICKNESS_MATERNITY",
        "OCC_ACCIDENT_DISEASE",
        "HEALTH",
        "UNEMPLOYMENT",
    ]

    region_resp = client.get(f"{BASE}/company-region", headers=_admin(client))
    assert region_resp.status_code == 200, region_resp.text
    region_body = region_resp.json()
    assert region_body["current"]["region"] == 3


def test_create_and_activate_policy_version_closes_previous_active(client: TestClient):
    headers = _admin(client)
    list_resp = client.get(f"{BASE}/policy-versions", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    current_active = next(item for item in list_resp.json() if item["is_active"])
    current_active_from = date.fromisoformat(current_active["effective_from"])
    new_effective_from = current_active_from + timedelta(days=30)

    create_resp = client.post(
        f"{BASE}/policy-versions",
        json={
            "code": _TEST_POLICY_CODE,
            "name": "TEST Policy",
            "legal_basis_summary": "TEST legal basis",
            "effective_from": new_effective_from.isoformat(),
            "company_region": 3,
            "note": "TEST create",
            "components": [
                {"component_code": "RETIREMENT_SURVIVOR", "employee_rate_percent": "8.0", "employer_rate_percent": "14.0", "employer_advances_employee_part": False},
                {"component_code": "SICKNESS_MATERNITY", "employee_rate_percent": "0", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "OCC_ACCIDENT_DISEASE", "employee_rate_percent": "0", "employer_rate_percent": "0.5", "employer_advances_employee_part": False},
                {"component_code": "HEALTH", "employee_rate_percent": "1.5", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "UNEMPLOYMENT", "employee_rate_percent": "1.0", "employer_rate_percent": "1.0", "employer_advances_employee_part": True},
            ],
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["is_active"] is False

    activate_resp = client.post(f"{BASE}/policy-versions/{created['id']}/activate", headers=headers)
    assert activate_resp.status_code == 200, activate_resp.text
    activated = activate_resp.json()
    assert activated["is_active"] is True

    after = client.get(f"{BASE}/policy-versions", headers=headers).json()
    new_active = next(item for item in after if item["is_active"])
    assert new_active["id"] == created["id"]

    old = next(item for item in after if item["id"] == current_active["id"])
    assert old["is_active"] is False
    assert old["effective_to"] == (new_effective_from - timedelta(days=1)).isoformat()


def test_update_company_region_creates_new_current_row_and_closes_previous(client: TestClient):
    headers = _admin(client)
    before = client.get(f"{BASE}/company-region", headers=headers)
    assert before.status_code == 200, before.text
    previous_current = before.json()["current"]

    update_resp = client.put(
        f"{BASE}/company-region",
        json={
            "region": 2,
            "effective_from": "2026-09-01",
            "note": _TEST_REGION_NOTE,
        },
        headers=headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    body = update_resp.json()
    assert body["current"]["region"] == 2
    assert body["current"]["effective_from"] == "2026-09-01"

    history = body["history"]
    previous = next(item for item in history if item["id"] == previous_current["id"])
    assert previous["effective_to"] == "2026-08-31"


def test_update_non_active_policy_version(client: TestClient):
    headers = _admin(client)
    create_resp = client.post(
        f"{BASE}/policy-versions",
        json={
            "code": f"{_TEST_POLICY_CODE}_EDIT",
            "name": "TEST Policy Edit",
            "effective_from": "2026-10-01",
            "company_region": 3,
            "components": [
                {"component_code": "RETIREMENT_SURVIVOR", "employee_rate_percent": "8.0", "employer_rate_percent": "14.0", "employer_advances_employee_part": False},
                {"component_code": "SICKNESS_MATERNITY", "employee_rate_percent": "0", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "OCC_ACCIDENT_DISEASE", "employee_rate_percent": "0", "employer_rate_percent": "0.5", "employer_advances_employee_part": False},
                {"component_code": "HEALTH", "employee_rate_percent": "1.5", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "UNEMPLOYMENT", "employee_rate_percent": "1.0", "employer_rate_percent": "1.0", "employer_advances_employee_part": False},
            ],
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()

    update_resp = client.put(
        f"{BASE}/policy-versions/{created['id']}",
        json={
            "name": "TEST Policy Edit Updated",
            "legal_basis_summary": "Updated legal basis",
            "effective_from": "2026-10-15",
            "company_region": 2,
            "components": [
                {"component_code": "RETIREMENT_SURVIVOR", "employee_rate_percent": "8.0", "employer_rate_percent": "14.0", "employer_advances_employee_part": False},
                {"component_code": "SICKNESS_MATERNITY", "employee_rate_percent": "0", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "OCC_ACCIDENT_DISEASE", "employee_rate_percent": "0", "employer_rate_percent": "0.5", "employer_advances_employee_part": False},
                {"component_code": "HEALTH", "employee_rate_percent": "1.5", "employer_rate_percent": "3.0", "employer_advances_employee_part": True},
                {"component_code": "UNEMPLOYMENT", "employee_rate_percent": "1.0", "employer_rate_percent": "1.0", "employer_advances_employee_part": False},
            ],
        },
        headers=headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["name"] == "TEST Policy Edit Updated"
    assert updated["effective_from"] == "2026-10-15"
    assert updated["company_region"] == 2
    health = next(item for item in updated["components"] if item["component_code"] == "HEALTH")
    assert health["employer_advances_employee_part"] is True


def test_policy_endpoints_require_authentication(client: TestClient):
    resp = client.get(f"{BASE}/policy-versions")
    assert resp.status_code == 401


def test_create_policy_rejects_duplicate_components(client: TestClient):
    headers = _admin(client)
    resp = client.post(
        f"{BASE}/policy-versions",
        json={
            "code": f"{_TEST_POLICY_CODE}_DUP",
            "name": "TEST duplicate components",
            "effective_from": "2026-11-01",
            "company_region": 3,
            "components": [
                {"component_code": "RETIREMENT_SURVIVOR", "employee_rate_percent": "8.0", "employer_rate_percent": "14.0", "employer_advances_employee_part": False},
                {"component_code": "RETIREMENT_SURVIVOR", "employee_rate_percent": "8.0", "employer_rate_percent": "14.0", "employer_advances_employee_part": False},
                {"component_code": "SICKNESS_MATERNITY", "employee_rate_percent": "0", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "OCC_ACCIDENT_DISEASE", "employee_rate_percent": "0", "employer_rate_percent": "0.5", "employer_advances_employee_part": False},
                {"component_code": "HEALTH", "employee_rate_percent": "1.5", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "UNEMPLOYMENT", "employee_rate_percent": "1.0", "employer_rate_percent": "1.0", "employer_advances_employee_part": False},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 422, resp.text
    assert "Component bị lặp" in resp.json()["detail"]


def test_delete_non_active_policy_version(client: TestClient):
    headers = _admin(client)
    create_resp = client.post(
        f"{BASE}/policy-versions",
        json={
            "code": f"{_TEST_POLICY_CODE}_DELETE",
            "name": "TEST delete draft",
            "effective_from": "2026-12-01",
            "company_region": 3,
            "components": [
                {"component_code": "RETIREMENT_SURVIVOR", "employee_rate_percent": "8.0", "employer_rate_percent": "14.0", "employer_advances_employee_part": False},
                {"component_code": "SICKNESS_MATERNITY", "employee_rate_percent": "0", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "OCC_ACCIDENT_DISEASE", "employee_rate_percent": "0", "employer_rate_percent": "0.5", "employer_advances_employee_part": False},
                {"component_code": "HEALTH", "employee_rate_percent": "1.5", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "UNEMPLOYMENT", "employee_rate_percent": "1.0", "employer_rate_percent": "1.0", "employer_advances_employee_part": False},
            ],
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()

    delete_resp = client.delete(f"{BASE}/policy-versions/{created['id']}", headers=headers)
    assert delete_resp.status_code == 204, delete_resp.text

    list_resp = client.get(f"{BASE}/policy-versions", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    assert all(item["id"] != created["id"] for item in list_resp.json())


def test_delete_active_policy_version_conflicts(client: TestClient):
    headers = _admin(client)
    list_resp = client.get(f"{BASE}/policy-versions", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    active = next(item for item in list_resp.json() if item["is_active"])

    delete_resp = client.delete(f"{BASE}/policy-versions/{active['id']}", headers=headers)
    assert delete_resp.status_code == 409, delete_resp.text


def test_delete_historical_policy_version_conflicts(client: TestClient):
    headers = _admin(client)
    list_resp = client.get(f"{BASE}/policy-versions", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    current_active = next(item for item in list_resp.json() if item["is_active"])
    current_active_from = date.fromisoformat(current_active["effective_from"])
    first_effective_from = current_active_from + timedelta(days=30)
    replacement_effective_from = first_effective_from + timedelta(days=30)

    create_resp = client.post(
        f"{BASE}/policy-versions",
        json={
            "code": f"{_TEST_POLICY_CODE}_HISTORY",
            "name": "TEST historical policy",
            "effective_from": first_effective_from.isoformat(),
            "company_region": 3,
            "components": [
                {"component_code": "RETIREMENT_SURVIVOR", "employee_rate_percent": "8.0", "employer_rate_percent": "14.0", "employer_advances_employee_part": False},
                {"component_code": "SICKNESS_MATERNITY", "employee_rate_percent": "0", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "OCC_ACCIDENT_DISEASE", "employee_rate_percent": "0", "employer_rate_percent": "0.5", "employer_advances_employee_part": False},
                {"component_code": "HEALTH", "employee_rate_percent": "1.5", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "UNEMPLOYMENT", "employee_rate_percent": "1.0", "employer_rate_percent": "1.0", "employer_advances_employee_part": False},
            ],
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()

    activate_resp = client.post(f"{BASE}/policy-versions/{created['id']}/activate", headers=headers)
    assert activate_resp.status_code == 200, activate_resp.text

    replacement_resp = client.post(
        f"{BASE}/policy-versions",
        json={
            "code": f"{_TEST_POLICY_CODE}_NEXT",
            "name": "TEST replacement policy",
            "effective_from": replacement_effective_from.isoformat(),
            "company_region": 3,
            "components": [
                {"component_code": "RETIREMENT_SURVIVOR", "employee_rate_percent": "8.0", "employer_rate_percent": "14.0", "employer_advances_employee_part": False},
                {"component_code": "SICKNESS_MATERNITY", "employee_rate_percent": "0", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "OCC_ACCIDENT_DISEASE", "employee_rate_percent": "0", "employer_rate_percent": "0.5", "employer_advances_employee_part": False},
                {"component_code": "HEALTH", "employee_rate_percent": "1.5", "employer_rate_percent": "3.0", "employer_advances_employee_part": False},
                {"component_code": "UNEMPLOYMENT", "employee_rate_percent": "1.0", "employer_rate_percent": "1.0", "employer_advances_employee_part": False},
            ],
        },
        headers=headers,
    )
    assert replacement_resp.status_code == 201, replacement_resp.text
    replacement = replacement_resp.json()

    activate_replacement_resp = client.post(f"{BASE}/policy-versions/{replacement['id']}/activate", headers=headers)
    assert activate_replacement_resp.status_code == 200, activate_replacement_resp.text

    delete_resp = client.delete(f"{BASE}/policy-versions/{created['id']}", headers=headers)
    assert delete_resp.status_code == 409, delete_resp.text
