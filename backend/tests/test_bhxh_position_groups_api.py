"""Integration tests for BHXH position groups slice."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/insurance/position-groups"
DEPT_URL = "/api/v1/departments"
POS_URL = "/api/v1/job-positions"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_TEST_GROUP_CODE = "TEST_BHXH_GROUP"
_TEST_GROUP_CODE_2 = "TEST_BHXH_GROUP_2"
_TEST_DEPT_CODE = "TEST_DEPT_BHXH_GROUP"
_TEST_POS_CODE = "TEST_POS_BHXH_GROUP"


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
                DELETE FROM salary_scale_entries
                WHERE bhxh_position_group_id IN (
                    SELECT id FROM bhxh_position_groups WHERE code IN (:code1, :code2)
                )
                """
            ),
            {"code1": _TEST_GROUP_CODE, "code2": _TEST_GROUP_CODE_2},
        )
        await s.execute(
            text(
                """
                DELETE FROM bhxh_position_group_members
                WHERE bhxh_position_group_id IN (
                    SELECT id FROM bhxh_position_groups WHERE code IN (:code1, :code2)
                )
                """
            ),
            {"code1": _TEST_GROUP_CODE, "code2": _TEST_GROUP_CODE_2},
        )
        await s.execute(
            text("DELETE FROM bhxh_position_groups WHERE code IN (:code1, :code2)"),
            {"code1": _TEST_GROUP_CODE, "code2": _TEST_GROUP_CODE_2},
        )
        await s.execute(
            text("DELETE FROM job_positions WHERE code = :code"),
            {"code": _TEST_POS_CODE},
        )
        await s.execute(
            text("DELETE FROM departments WHERE code = :code"),
            {"code": _TEST_DEPT_CODE},
        )
        await s.commit()


def _ensure_position(client: TestClient) -> int:
    dept_resp = client.post(
        DEPT_URL,
        json={"code": _TEST_DEPT_CODE, "name": "Test Dept BHXH Group", "dept_type": "PHONG"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]

    pos_resp = client.post(
        POS_URL,
        json={"code": _TEST_POS_CODE, "name": "Test Position BHXH Group", "department_id": dept_id},
    )
    assert pos_resp.status_code == 201, pos_resp.text
    return pos_resp.json()["id"]


def _coefficients(base: str = "TEST") -> list[dict]:
    values = [1.11, 1.22, 1.33, 1.44, 1.55, 1.66, 1.77]
    return [
        {
            "grade_no": idx,
            "coefficient": f"{value:.2f}",
            "promotion_months": 12,
            "criteria": f"{base} grade {idx}",
        }
        for idx, value in enumerate(values, start=1)
    ]


def setup_function():
    import asyncio

    asyncio.run(_cleanup())


def teardown_function():
    import asyncio

    asyncio.run(_cleanup())


def test_list_position_groups_returns_current_scale_and_seeded_groups(client: TestClient):
    resp = client.get(BASE, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_scale"] is not None
    assert body["current_scale"]["name"] == "Thang bảng lương 2026"
    assert any(len(group["coefficients"]) == 7 for group in body["groups"])


def test_create_position_group_persists_members_and_coefficients(client: TestClient):
    headers = _admin(client)
    position_id = _ensure_position(client)

    resp = client.post(
        BASE,
        json={
            "code": _TEST_GROUP_CODE,
            "name": "Test nhóm vị trí BHXH",
            "description": "Test mapping group",
            "position_ids": [position_id],
            "coefficients": _coefficients(),
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    group = next(item for item in body["groups"] if item["code"] == _TEST_GROUP_CODE)
    assert len(group["coefficients"]) == 7
    assert group["coefficients"][0]["grade_no"] == 1
    assert group["coefficients"][0]["coefficient"] == "1.1100"
    assert group["members"][0]["job_position_id"] == position_id
    assert group["members"][0]["job_position_code"] == _TEST_POS_CODE


def test_same_position_cannot_belong_to_two_bhxh_groups(client: TestClient):
    headers = _admin(client)
    position_id = _ensure_position(client)

    first = client.post(
        BASE,
        json={
            "code": _TEST_GROUP_CODE,
            "name": "Nhóm 1",
            "position_ids": [position_id],
            "coefficients": _coefficients("A"),
        },
        headers=headers,
    )
    assert first.status_code == 201, first.text

    second = client.post(
        BASE,
        json={
            "code": _TEST_GROUP_CODE_2,
            "name": "Nhóm 2",
            "position_ids": [position_id],
            "coefficients": _coefficients("B"),
        },
        headers=headers,
    )
    assert second.status_code == 409, second.text
    assert "đã được gán vào nhóm BHXH khác" in second.json()["detail"]
