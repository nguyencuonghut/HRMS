"""Integration tests for Salary Scales API."""

from __future__ import annotations

from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/insurance/salary-scales"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_TEST_SCALE_NAME = "TEST_SCALE_2027"
_TEST_SCALE_NAME_2 = "TEST_SCALE_2028"


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
        # Find IDs of test scales to delete their entries first
        rows = await s.execute(
            text("SELECT id FROM salary_scales WHERE name IN (:name1, :name2)"),
            {"name1": _TEST_SCALE_NAME, "name2": _TEST_SCALE_NAME_2},
        )
        ids = [r[0] for r in rows.fetchall()]
        if ids:
            await s.execute(
                text("DELETE FROM salary_scale_entries WHERE salary_scale_id IN (:ids)"),
                {"ids": ids},
            )
            await s.execute(
                text("DELETE FROM salary_scales WHERE id IN (:ids)"),
                {"ids": ids},
            )
        # Restore effective_to of default scale if it was closed
        await s.execute(
            text("UPDATE salary_scales SET effective_to = NULL WHERE name = 'Thang bảng lương 2026'")
        )
        await s.commit()


def setup_function():
    import asyncio
    asyncio.run(_cleanup())


def teardown_function():
    import asyncio
    asyncio.run(_cleanup())


def test_list_salary_scales(client: TestClient):
    resp = client.get(BASE, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) >= 1
    # Standard seeded scale should be active
    seeded = next(s for s in body if s["name"] == "Thang bảng lương 2026")
    assert seeded["is_active"] is True
    assert seeded["effective_to"] is None


def test_create_and_delete_salary_scale(client: TestClient):
    headers = _admin(client)
    # Create draft scale
    create_resp = client.post(
        BASE,
        json={
            "name": _TEST_SCALE_NAME,
            "effective_from": "2027-01-01",
            "note": "Draft scale for test",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["name"] == _TEST_SCALE_NAME
    assert created["is_active"] is False
    assert created["effective_to"] == "2027-01-01"  # draft state

    # Delete scale
    delete_resp = client.delete(f"{BASE}/{created['id']}", headers=headers)
    assert delete_resp.status_code == 200, delete_resp.text
    assert not any(s["id"] == created["id"] for s in delete_resp.json())


def test_update_salary_scale(client: TestClient):
    headers = _admin(client)
    create_resp = client.post(
        BASE,
        json={
            "name": _TEST_SCALE_NAME,
            "effective_from": "2027-01-01",
        },
        headers=headers,
    )
    created = create_resp.json()

    # Update metadata of draft scale
    update_resp = client.put(
        f"{BASE}/{created['id']}",
        json={
            "name": _TEST_SCALE_NAME_2,
            "effective_from": "2027-02-01",
            "note": "Updated note",
        },
        headers=headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["name"] == _TEST_SCALE_NAME_2
    assert updated["effective_from"] == "2027-02-01"
    assert updated["note"] == "Updated note"


def test_activate_salary_scale_flow(client: TestClient):
    headers = _admin(client)
    # 1. Create a future scale
    create_resp = client.post(
        BASE,
        json={
            "name": _TEST_SCALE_NAME,
            "effective_from": "2027-01-01",
        },
        headers=headers,
    )
    created = create_resp.json()

    # 2. Activate the scale
    act_resp = client.post(f"{BASE}/{created['id']}/activate", headers=headers)
    assert act_resp.status_code == 200, act_resp.text
    activated = act_resp.json()
    assert activated["is_active"] is True
    assert activated["effective_to"] is None

    # Check that previous active scale (2026) is closed
    list_resp = client.get(BASE, headers=headers)
    body = list_resp.json()
    seeded = next(s for s in body if s["name"] == "Thang bảng lương 2026")
    assert seeded["is_active"] is False
    assert seeded["effective_to"] == "2026-12-31"  # 1 day before new scale


def test_clone_and_update_coefficients(client: TestClient):
    headers = _admin(client)
    # Get seeded scale ID
    list_resp = client.get(BASE, headers=headers)
    seeded_scale = next(s for s in list_resp.json() if s["name"] == "Thang bảng lương 2026")
    
    # Create target scale
    create_resp = client.post(
        BASE,
        json={
            "name": _TEST_SCALE_NAME,
            "effective_from": "2027-01-01",
        },
        headers=headers,
    )
    target = create_resp.json()

    # Clone from seeded scale
    clone_resp = client.post(
        f"{BASE}/{target['id']}/clone?source_scale_id={seeded_scale['id']}",
        headers=headers,
    )
    assert clone_resp.status_code == 200, clone_resp.text
    cloned = clone_resp.json()
    assert len(cloned["groups"]) > 0
    # Coefficients should be populated
    assert len(cloned["groups"][0]["coefficients"]) == 7

    # Update coefficients of first group
    group_id = cloned["groups"][0]["id"]
    coeffs = [
        {
            "grade_no": idx,
            "coefficient": f"{idx + 0.55:.2f}",
            "promotion_months": 24,
            "criteria": f"New criteria {idx}",
        }
        for idx in range(1, 8)
    ]
    upd_resp = client.put(
        f"{BASE}/{target['id']}/coefficients",
        json={
            "groups": [
                {
                    "bhxh_position_group_id": group_id,
                    "coefficients": coeffs,
                }
            ]
        },
        headers=headers,
    )
    assert upd_resp.status_code == 200, upd_resp.text
    updated = upd_resp.json()
    group = next(g for g in updated["groups"] if g["id"] == group_id)
    assert group["coefficients"][0]["coefficient"] == "1.5500"
    assert group["coefficients"][0]["promotion_months"] == 24
    assert group["coefficients"][0]["criteria"] == "New criteria 1"
