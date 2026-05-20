"""Integration tests cho Slice 1.5 effective contribution config resolver."""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/insurance"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_POLICY_PREFIX = "TEST_EFFECTIVE_CFG"
_REGION_NOTE_PREFIX = "TEST_EFFECTIVE_REGION"


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


def _admin(client) -> dict:
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
                    SELECT id FROM insurance_policy_versions WHERE code LIKE :policy_code
                )
                """
            ),
            {"policy_code": f"{_POLICY_PREFIX}%"},
        )
        await s.execute(
            text("DELETE FROM insurance_policy_versions WHERE code LIKE :policy_code"),
            {"policy_code": f"{_POLICY_PREFIX}%"},
        )
        await s.execute(
            text("DELETE FROM company_bhxh_region WHERE note LIKE :region_note"),
            {"region_note": f"{_REGION_NOTE_PREFIX}%"},
        )
        await s.execute(
            text(
                """
                UPDATE insurance_policy_versions
                SET is_active = FALSE
                WHERE code NOT LIKE :policy_code
                """
            ),
            {"policy_code": f"{_POLICY_PREFIX}%"},
        )
        await s.execute(
            text(
                """
                WITH latest_non_test AS (
                    SELECT id
                    FROM insurance_policy_versions
                    WHERE code NOT LIKE :policy_code
                    ORDER BY effective_from DESC, id DESC
                    LIMIT 1
                )
                UPDATE insurance_policy_versions
                SET is_active = TRUE,
                    effective_to = NULL
                WHERE id = (SELECT id FROM latest_non_test)
                """
            ),
            {"policy_code": f"{_POLICY_PREFIX}%"},
        )
        await s.execute(
            text(
                """
                WITH latest_non_test AS (
                    SELECT id
                    FROM company_bhxh_region
                    WHERE note IS NULL OR note NOT LIKE :region_note
                    ORDER BY effective_from DESC, id DESC
                    LIMIT 1
                )
                UPDATE company_bhxh_region
                SET effective_to = NULL
                WHERE id = (SELECT id FROM latest_non_test)
                """
            ),
            {"region_note": f"{_REGION_NOTE_PREFIX}%"},
        )
        await s.commit()


async def _close_non_test_open_ended_rows(*, cutoff_date: str) -> None:
    cutoff = date.fromisoformat(cutoff_date)
    async with _make_session()() as s:
        await s.execute(
            text(
                """
                UPDATE insurance_policy_versions
                SET is_active = FALSE,
                    effective_to = :cutoff_date
                WHERE code NOT LIKE :policy_code
                  AND is_active = TRUE
                """
            ),
            {"cutoff_date": cutoff, "policy_code": f"{_POLICY_PREFIX}%"},
        )
        await s.execute(
            text(
                """
                UPDATE company_bhxh_region
                SET effective_to = :cutoff_date
                WHERE (note IS NULL OR note NOT LIKE :region_note)
                  AND effective_to IS NULL
                """
            ),
            {"cutoff_date": cutoff, "region_note": f"{_REGION_NOTE_PREFIX}%"},
        )
        await s.commit()


async def _insert_policy_and_rates(
    *,
    code: str,
    name: str,
    company_region: int,
    effective_from: str,
    effective_to: str | None,
    note: str | None = None,
) -> None:
    async with _make_session()() as s:
        policy_id = (
            await s.execute(
                text(
                    """
                    INSERT INTO insurance_policy_versions (
                        code, name, legal_basis_summary, effective_from, effective_to,
                        is_active, company_region, note
                    )
                    VALUES (
                        :code, :name, 'test', :effective_from, :effective_to,
                        FALSE, :company_region, :note
                    )
                    RETURNING id
                    """
                ),
                {
                    "code": code,
                    "name": name,
                    "effective_from": date.fromisoformat(effective_from),
                    "effective_to": date.fromisoformat(effective_to) if effective_to else None,
                    "company_region": company_region,
                    "note": note,
                },
            )
        ).scalar_one()
        await s.execute(
            text(
                """
                INSERT INTO insurance_policy_component_rates (
                    policy_version_id,
                    component_code,
                    employee_rate_percent,
                    employer_rate_percent,
                    employer_advances_employee_part,
                    is_active
                )
                SELECT
                    :policy_id,
                    component.code,
                    CASE component.code
                        WHEN 'RETIREMENT_SURVIVOR' THEN 8.0
                        WHEN 'HEALTH' THEN 1.5
                        WHEN 'UNEMPLOYMENT' THEN 1.0
                        ELSE 0.0
                    END,
                    CASE component.code
                        WHEN 'RETIREMENT_SURVIVOR' THEN 14.0
                        WHEN 'SICKNESS_MATERNITY' THEN 3.0
                        WHEN 'OCC_ACCIDENT_DISEASE' THEN 0.5
                        WHEN 'HEALTH' THEN 3.0
                        WHEN 'UNEMPLOYMENT' THEN 1.0
                        ELSE 0.0
                    END,
                    FALSE,
                    TRUE
                FROM insurance_contribution_components component
                """
            ),
            {"policy_id": policy_id},
        )
        await s.commit()


async def _insert_region(*, region: int, effective_from: str, effective_to: str | None, note: str) -> None:
    async with _make_session()() as s:
        await s.execute(
            text(
                """
                INSERT INTO company_bhxh_region (region, effective_from, effective_to, note)
                VALUES (:region, :effective_from, :effective_to, :note)
                """
            ),
            {
                "region": region,
                "effective_from": date.fromisoformat(effective_from),
                "effective_to": date.fromisoformat(effective_to) if effective_to else None,
                "note": note,
            },
        )
        await s.commit()


async def _seed_future_window() -> None:
    await _close_non_test_open_ended_rows(cutoff_date="2029-12-31")
    await _insert_region(
        region=3,
        effective_from="2030-01-01",
        effective_to="2030-06-30",
        note=f"{_REGION_NOTE_PREFIX}_1",
    )
    await _insert_region(
        region=2,
        effective_from="2030-07-01",
        effective_to="2030-12-31",
        note=f"{_REGION_NOTE_PREFIX}_2",
    )
    await _insert_policy_and_rates(
        code=f"{_POLICY_PREFIX}_1",
        name="Resolver Window 1",
        company_region=3,
        effective_from="2030-01-01",
        effective_to="2030-06-30",
    )
    await _insert_policy_and_rates(
        code=f"{_POLICY_PREFIX}_2",
        name="Resolver Window 2",
        company_region=2,
        effective_from="2030-07-01",
        effective_to="2030-12-31",
    )


import pytest


@pytest.fixture(autouse=True)
async def cleanup():
    await _cleanup()
    yield
    await _cleanup()


def test_effective_config_requires_authentication(client):
    resp = client.get(f"{BASE}/effective-config", params={"as_of_date": "2030-06-15"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_effective_config_resolves_region_and_policy_by_date(client):
    await _seed_future_window()
    headers = _admin(client)

    first = client.get(f"{BASE}/effective-config", params={"as_of_date": "2030-06-15"}, headers=headers)
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["company_region"]["region"] == 3
    assert first_body["policy_version"]["code"] == f"{_POLICY_PREFIX}_1"
    assert len(first_body["policy_version"]["components"]) == 5

    second = client.get(f"{BASE}/effective-config", params={"as_of_date": "2030-08-15"}, headers=headers)
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["company_region"]["region"] == 2
    assert second_body["policy_version"]["code"] == f"{_POLICY_PREFIX}_2"


@pytest.mark.asyncio
async def test_effective_config_returns_422_when_missing_company_region(client):
    await _close_non_test_open_ended_rows(cutoff_date="2030-12-31")
    await _insert_policy_and_rates(
        code=f"{_POLICY_PREFIX}_MISSING_REGION",
        name="Missing region",
        company_region=3,
        effective_from="2031-01-01",
        effective_to="2031-12-31",
    )
    headers = _admin(client)

    resp = client.get(f"{BASE}/effective-config", params={"as_of_date": "2031-06-15"}, headers=headers)
    assert resp.status_code == 422, resp.text
    assert "Không có vùng BHXH công ty hiệu lực" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_effective_config_returns_409_when_policy_region_mismatches_company_region(client):
    await _close_non_test_open_ended_rows(cutoff_date="2031-12-31")
    await _insert_region(
        region=3,
        effective_from="2032-01-01",
        effective_to="2032-12-31",
        note=f"{_REGION_NOTE_PREFIX}_MISMATCH",
    )
    await _insert_policy_and_rates(
        code=f"{_POLICY_PREFIX}_MISMATCH",
        name="Mismatch policy",
        company_region=4,
        effective_from="2032-01-01",
        effective_to="2032-12-31",
    )
    headers = _admin(client)

    resp = client.get(f"{BASE}/effective-config", params={"as_of_date": "2032-06-15"}, headers=headers)
    assert resp.status_code == 409, resp.text
    assert "không khớp với vùng BHXH công ty" in resp.json()["detail"]
