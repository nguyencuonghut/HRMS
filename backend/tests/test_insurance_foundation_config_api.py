"""Integration tests for insurance foundation config slice."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/insurance"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_TEST_WAGE_NOTE = "TEST_MIN_WAGE_NOTE"
_TEST_SENIORITY_NOTE = "TEST_SENIORITY_NOTE"


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
            text("DELETE FROM regional_minimum_wages WHERE note LIKE :note"),
            {"note": f"{_TEST_WAGE_NOTE}%"},
        )
        await s.execute(
            text(
                """
                WITH ranked AS (
                    SELECT
                        id,
                        region,
                        effective_from,
                        LEAD(effective_from) OVER (
                            PARTITION BY region
                            ORDER BY effective_from ASC, id ASC
                        ) AS next_effective_from
                    FROM regional_minimum_wages
                )
                UPDATE regional_minimum_wages AS w
                SET effective_to = CASE
                    WHEN ranked.next_effective_from IS NULL THEN NULL
                    ELSE ranked.next_effective_from - INTERVAL '1 day'
                END
                FROM ranked
                WHERE w.id = ranked.id
                """
            ),
        )
        await s.execute(
            text("DELETE FROM bhxh_seniority_settings WHERE note LIKE :note"),
            {"note": f"{_TEST_SENIORITY_NOTE}%"},
        )
        await s.execute(
            text(
                """
                WITH ranked AS (
                    SELECT
                        id,
                        effective_from,
                        LEAD(effective_from) OVER (
                            ORDER BY effective_from ASC, id ASC
                        ) AS next_effective_from
                    FROM bhxh_seniority_settings
                )
                UPDATE bhxh_seniority_settings AS s0
                SET effective_to = CASE
                    WHEN ranked.next_effective_from IS NULL THEN NULL
                    ELSE ranked.next_effective_from - INTERVAL '1 day'
                END
                FROM ranked
                WHERE s0.id = ranked.id
                """
            ),
        )
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    await _cleanup()
    yield
    await _cleanup()


def test_minimum_wage_list_returns_seeded_region_three(client: TestClient):
    resp = client.get(f"{BASE}/minimum-wages", headers=_admin(client))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    current_region_three = next(
        item for item in body if item["region"] == 3 and item["effective_to"] is None
    )
    assert current_region_three["amount"] == 4_140_000


def test_create_minimum_wage_closes_previous_current_for_same_region(client: TestClient):
    headers = _admin(client)
    before = client.get(f"{BASE}/minimum-wages", headers=headers)
    assert before.status_code == 200, before.text
    current_region_three = next(
        item for item in before.json() if item["region"] == 3 and item["effective_to"] is None
    )
    new_effective_from = (date.fromisoformat(current_region_three["effective_from"]) + timedelta(days=365)).isoformat()

    create_resp = client.post(
        f"{BASE}/minimum-wages",
        json={
            "decree_number": "TEST/2027/ND-CP",
            "region": 3,
            "amount": 4_500_000,
            "effective_from": new_effective_from,
            "note": _TEST_WAGE_NOTE,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text

    after = client.get(f"{BASE}/minimum-wages", headers=headers)
    assert after.status_code == 200, after.text
    rows = after.json()
    new_current = next(item for item in rows if item["region"] == 3 and item["effective_to"] is None)
    assert new_current["amount"] == 4_500_000
    previous = next(item for item in rows if item["id"] == current_region_three["id"])
    expected_to = (date.fromisoformat(new_effective_from) - timedelta(days=1)).isoformat()
    assert previous["effective_to"] == expected_to


def test_update_minimum_wage_changes_amount_and_note(client: TestClient):
    headers = _admin(client)
    create_resp = client.post(
        f"{BASE}/minimum-wages",
        json={
            "decree_number": "TEST/2028/ND-CP",
            "region": 4,
            "amount": 3_700_000,
            "effective_from": "2028-01-01",
            "note": _TEST_WAGE_NOTE,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()

    update_resp = client.put(
        f"{BASE}/minimum-wages/{created['id']}",
        json={
            "decree_number": "TEST/2028/ND-CP-UPDATED",
            "amount": 3_710_000,
            "note": f"{_TEST_WAGE_NOTE}_UPDATED",
        },
        headers=headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["decree_number"] == "TEST/2028/ND-CP-UPDATED"
    assert updated["amount"] == 3_710_000
    assert updated["note"] == f"{_TEST_WAGE_NOTE}_UPDATED"


def test_delete_minimum_wage_reopens_previous_row(client: TestClient):
    headers = _admin(client)
    current = next(
        item
        for item in client.get(f"{BASE}/minimum-wages", headers=headers).json()
        if item["region"] == 3 and item["effective_to"] is None
    )

    create_resp = client.post(
        f"{BASE}/minimum-wages",
        json={
            "decree_number": "TEST/2029/ND-CP",
            "region": 3,
            "amount": 4_600_000,
            "effective_from": "2029-01-01",
            "note": _TEST_WAGE_NOTE,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()

    delete_resp = client.delete(f"{BASE}/minimum-wages/{created['id']}", headers=headers)
    assert delete_resp.status_code == 204, delete_resp.text

    rows = client.get(f"{BASE}/minimum-wages", headers=headers).json()
    reopened = next(item for item in rows if item["id"] == current["id"])
    assert reopened["effective_to"] is None


def test_get_seniority_settings_returns_seeded_current_rule(client: TestClient):
    resp = client.get(f"{BASE}/seniority-settings", headers=_admin(client))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current"]["raise_month"] == 1
    assert body["current"]["raise_day"] == 1
    assert body["current"]["years_per_grade"] == 3
    assert body["current"]["first_year_cutoff_month"] == 4
    assert body["current"]["first_year_cutoff_day"] == 30


def test_create_seniority_setting_closes_previous_current_rule(client: TestClient):
    headers = _admin(client)
    before = client.get(f"{BASE}/seniority-settings", headers=headers)
    assert before.status_code == 200, before.text
    current = before.json()["current"]
    new_effective_from = (date.fromisoformat(current["effective_from"]) + timedelta(days=365)).isoformat()

    create_resp = client.post(
        f"{BASE}/seniority-settings",
        json={
            "raise_month": 7,
            "raise_day": 1,
            "years_per_grade": 2,
            "first_year_cutoff_month": 6,
            "first_year_cutoff_day": 30,
            "effective_from": new_effective_from,
            "note": _TEST_SENIORITY_NOTE,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    body = create_resp.json()
    assert body["current"]["raise_month"] == 7
    previous = next(item for item in body["history"] if item["id"] == current["id"])
    assert previous["effective_to"] == (date.fromisoformat(new_effective_from) - timedelta(days=1)).isoformat()


def test_update_seniority_setting_changes_rule_fields(client: TestClient):
    headers = _admin(client)
    create_resp = client.post(
        f"{BASE}/seniority-settings",
        json={
            "raise_month": 7,
            "raise_day": 1,
            "years_per_grade": 2,
            "first_year_cutoff_month": 6,
            "first_year_cutoff_day": 30,
            "effective_from": "2028-01-01",
            "note": _TEST_SENIORITY_NOTE,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()["current"]

    update_resp = client.put(
        f"{BASE}/seniority-settings/{created['id']}",
        json={
            "raise_month": 8,
            "raise_day": 15,
            "years_per_grade": 4,
            "first_year_cutoff_month": 5,
            "first_year_cutoff_day": 31,
            "note": f"{_TEST_SENIORITY_NOTE}_UPDATED",
        },
        headers=headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()["current"]
    assert updated["raise_month"] == 8
    assert updated["raise_day"] == 15
    assert updated["years_per_grade"] == 4
    assert updated["first_year_cutoff_month"] == 5
    assert updated["first_year_cutoff_day"] == 31
    assert updated["note"] == f"{_TEST_SENIORITY_NOTE}_UPDATED"


def test_delete_seniority_setting_reopens_previous_rule(client: TestClient):
    headers = _admin(client)
    baseline = client.get(f"{BASE}/seniority-settings", headers=headers).json()["current"]

    create_resp = client.post(
        f"{BASE}/seniority-settings",
        json={
            "raise_month": 7,
            "raise_day": 1,
            "years_per_grade": 2,
            "first_year_cutoff_month": 6,
            "first_year_cutoff_day": 30,
            "effective_from": "2029-01-01",
            "note": _TEST_SENIORITY_NOTE,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()["current"]

    delete_resp = client.delete(f"{BASE}/seniority-settings/{created['id']}", headers=headers)
    assert delete_resp.status_code == 200, delete_resp.text
    body = delete_resp.json()
    assert body["current"]["id"] == baseline["id"]
    assert body["current"]["effective_to"] is None
