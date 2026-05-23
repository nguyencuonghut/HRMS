"""Integration tests cho Plan 8.1 — Khen thưởng.

Covers:
  - TestRewardTypeCatalog: CRUD danh mục loại khen thưởng
  - TestCreateReward: tạo khen thưởng có/không file, validate is_monetary
  - TestListRewards: list + filter (employee, type, date range, search)
  - TestUpdateDeleteReward: sửa + xoá khen thưởng
  - TestEmployeeHistory: lịch sử khen thưởng của nhân viên
"""
from __future__ import annotations

import io
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/rewards"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_TEST_DATE = "2098-06-15"
_TEST_CODE_PREFIX = "TST_REWARD"
_RUN_ID = uuid.uuid4().hex[:8]  # unique per test session để tránh 409 từ runs trước


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _get_any_employee() -> dict:
    async with _make_session()() as s:
        r = await s.execute(text("SELECT id, full_name FROM employees ORDER BY id LIMIT 1"))
        row = r.fetchone()
        assert row is not None, "Không tìm thấy employee nào"
        return {"id": row[0], "name": row[1]}


async def _get_monetary_type_id() -> int:
    async with _make_session()() as s:
        r = await s.execute(text("SELECT id FROM reward_types WHERE is_monetary=true AND is_active=true LIMIT 1"))
        row = r.fetchone()
        assert row is not None, "Không tìm thấy loại khen thưởng tiền tệ"
        return row[0]


async def _get_non_monetary_type_id() -> int:
    async with _make_session()() as s:
        r = await s.execute(text("SELECT id FROM reward_types WHERE is_monetary=false AND is_active=true LIMIT 1"))
        row = r.fetchone()
        assert row is not None, "Không tìm thấy loại khen thưởng phi tiền tệ"
        return row[0]


def _create_reward(client, h, emp_id, type_id, title="Test reward"):
    payload = json.dumps({
        "employee_id": emp_id,
        "reward_type_id": type_id,
        "title": title,
        "reward_date": _TEST_DATE,
    })
    return client.post(BASE, data={"body": payload}, headers=h).json()


# ── TestRewardTypeCatalog ──────────────────────────────────────────────────────

class TestRewardTypeCatalog:
    def test_list_types_returns_seeded_data(self, client: TestClient):
        h = _admin(client)
        r = client.get(f"{BASE}/types", headers=h)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 4
        codes = [i["code"] for i in items]
        assert "bang_khen" in codes
        assert "thuong_tien" in codes

    def test_create_type_success(self, client: TestClient):
        h = _admin(client)
        code = f"{_TEST_CODE_PREFIX}_{_RUN_ID}_CREATE"
        r = client.post(
            f"{BASE}/types",
            json={"code": code, "name": "Loại test tạo mới", "is_monetary": False},
            headers=h,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["code"] == code
        assert data["is_active"] is True

    def test_create_type_duplicate_code_returns_409(self, client: TestClient):
        h = _admin(client)
        code = f"{_TEST_CODE_PREFIX}_{_RUN_ID}_DUP"
        client.post(f"{BASE}/types", json={"code": code, "name": "Lần 1"}, headers=h)
        r = client.post(f"{BASE}/types", json={"code": code, "name": "Lần 2"}, headers=h)
        assert r.status_code == 409

    def test_update_type_deactivate(self, client: TestClient):
        h = _admin(client)
        code = f"{_TEST_CODE_PREFIX}_{_RUN_ID}_DEACT"
        created = client.post(
            f"{BASE}/types",
            json={"code": code, "name": "Loại deactivate"},
            headers=h,
        ).json()
        type_id = created["id"]
        r = client.put(f"{BASE}/types/{type_id}", json={"is_active": False}, headers=h)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_delete_type_unused_success(self, client: TestClient):
        h = _admin(client)
        code = f"{_TEST_CODE_PREFIX}_{_RUN_ID}_DEL"
        created = client.post(
            f"{BASE}/types",
            json={"code": code, "name": "Loại sẽ xoá"},
            headers=h,
        ).json()
        type_id = created["id"]
        r = client.delete(f"{BASE}/types/{type_id}", headers=h)
        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_type_in_use_returns_409(self, client: TestClient):
        """Loại đã có reward dùng thì không cho xoá."""
        emp = await _get_any_employee()
        h = _admin(client)

        code = f"{_TEST_CODE_PREFIX}_{_RUN_ID}_INUSE"
        type_id = client.post(
            f"{BASE}/types",
            json={"code": code, "name": "Loại đang dùng"},
            headers=h,
        ).json()["id"]

        _create_reward(client, h, emp["id"], type_id, "Khen thưởng test in-use")

        r = client.delete(f"{BASE}/types/{type_id}", headers=h)
        assert r.status_code == 409


# ── TestCreateReward ───────────────────────────────────────────────────────────

class TestCreateReward:
    @pytest.mark.asyncio
    async def test_create_non_monetary_reward_success(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_non_monetary_type_id()
        h = _admin(client)

        payload = json.dumps({
            "employee_id": emp["id"],
            "reward_type_id": type_id,
            "title": "Bằng khen xuất sắc",
            "reward_date": _TEST_DATE,
            "decision_number": "QD-TEST-001",
        })
        r = client.post(BASE, data={"body": payload}, headers=h)
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Bằng khen xuất sắc"
        assert data["has_file"] is False

    @pytest.mark.asyncio
    async def test_create_monetary_reward_requires_value(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_monetary_type_id()
        h = _admin(client)

        payload = json.dumps({
            "employee_id": emp["id"],
            "reward_type_id": type_id,
            "title": "Thưởng tiền không có value",
            "reward_date": _TEST_DATE,
        })
        r = client.post(BASE, data={"body": payload}, headers=h)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_create_monetary_reward_with_value_success(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_monetary_type_id()
        h = _admin(client)

        payload = json.dumps({
            "employee_id": emp["id"],
            "reward_type_id": type_id,
            "title": "Thưởng tiền có value",
            "reward_date": _TEST_DATE,
            "value": 5000000,
        })
        r = client.post(BASE, data={"body": payload}, headers=h)
        assert r.status_code == 201
        data = r.json()
        assert float(data["value"]) == 5000000.0

    @pytest.mark.asyncio
    async def test_create_reward_with_file(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_non_monetary_type_id()
        h = _admin(client)

        payload = json.dumps({
            "employee_id": emp["id"],
            "reward_type_id": type_id,
            "title": "Khen thưởng có đính kèm",
            "reward_date": _TEST_DATE,
        })
        fake_pdf = io.BytesIO(b"%PDF-1.4 test")
        r = client.post(
            BASE,
            data={"body": payload},
            files={"file": ("quyet_dinh.pdf", fake_pdf, "application/pdf")},
            headers=h,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["has_file"] is True
        assert data["file_name"] == "quyet_dinh.pdf"

    @pytest.mark.asyncio
    async def test_create_reward_invalid_employee_returns_404(self, client: TestClient):
        type_id = await _get_non_monetary_type_id()
        h = _admin(client)

        payload = json.dumps({
            "employee_id": 999999,
            "reward_type_id": type_id,
            "title": "Khen thưởng nhân viên không tồn tại",
            "reward_date": _TEST_DATE,
        })
        r = client.post(BASE, data={"body": payload}, headers=h)
        assert r.status_code == 404


# ── TestListRewards ────────────────────────────────────────────────────────────

class TestListRewards:
    def test_list_returns_paginated(self, client: TestClient):
        h = _admin(client)
        r = client.get(BASE, params={"page": 1, "page_size": 10}, headers=h)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_filter_by_employee_id(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_non_monetary_type_id()
        h = _admin(client)

        _create_reward(client, h, emp["id"], type_id, "Lọc theo nhân viên")
        r = client.get(BASE, params={"employee_id": emp["id"], "page_size": 100}, headers=h)
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(item["employee_id"] == emp["id"] for item in items)

    @pytest.mark.asyncio
    async def test_filter_by_reward_type(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_non_monetary_type_id()
        h = _admin(client)

        _create_reward(client, h, emp["id"], type_id, "Lọc theo loại")
        r = client.get(BASE, params={"reward_type_id": type_id, "page_size": 100}, headers=h)
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(item["reward_type_id"] == type_id for item in items)

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_non_monetary_type_id()
        h = _admin(client)

        _create_reward(client, h, emp["id"], type_id, "Lọc theo ngày")
        r = client.get(
            BASE,
            params={"from_date": "2098-01-01", "to_date": "2098-12-31", "page_size": 100},
            headers=h,
        )
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(item["reward_date"].startswith("2098") for item in items)

    @pytest.mark.asyncio
    async def test_search_by_name(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_non_monetary_type_id()
        h = _admin(client)

        _create_reward(client, h, emp["id"], type_id, "Khen test search")
        r = client.get(BASE, params={"search": emp["name"][:4], "page_size": 50}, headers=h)
        assert r.status_code == 200


# ── TestUpdateDeleteReward ─────────────────────────────────────────────────────

class TestUpdateDeleteReward:
    @pytest.mark.asyncio
    async def test_update_title(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_non_monetary_type_id()
        h = _admin(client)

        created = _create_reward(client, h, emp["id"], type_id)
        rid = created["id"]
        payload = json.dumps({"title": "Tiêu đề đã sửa"})
        r = client.put(f"{BASE}/{rid}", data={"body": payload}, headers=h)
        assert r.status_code == 200
        assert r.json()["title"] == "Tiêu đề đã sửa"

    @pytest.mark.asyncio
    async def test_update_adds_file(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_non_monetary_type_id()
        h = _admin(client)

        created = _create_reward(client, h, emp["id"], type_id, "Sửa thêm file")
        rid = created["id"]
        assert created["has_file"] is False

        payload = json.dumps({"title": "Sửa thêm file"})
        fake_pdf = io.BytesIO(b"%PDF-1.4 new file")
        r = client.put(
            f"{BASE}/{rid}",
            data={"body": payload},
            files={"file": ("new_decision.pdf", fake_pdf, "application/pdf")},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["has_file"] is True

    @pytest.mark.asyncio
    async def test_delete_reward_success(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_non_monetary_type_id()
        h = _admin(client)

        created = _create_reward(client, h, emp["id"], type_id, "Sẽ bị xoá")
        rid = created["id"]
        r = client.delete(f"{BASE}/{rid}", headers=h)
        assert r.status_code == 204
        r2 = client.get(f"{BASE}/{rid}", headers=h)
        assert r2.status_code == 404

    def test_update_nonexistent_returns_404(self, client: TestClient):
        h = _admin(client)
        payload = json.dumps({"title": "Không tồn tại"})
        r = client.put(f"{BASE}/999999", data={"body": payload}, headers=h)
        assert r.status_code == 404


# ── TestEmployeeHistory ────────────────────────────────────────────────────────

class TestEmployeeHistory:
    @pytest.mark.asyncio
    async def test_history_returns_list(self, client: TestClient):
        emp = await _get_any_employee()
        type_id = await _get_non_monetary_type_id()
        h = _admin(client)

        payload = json.dumps({
            "employee_id": emp["id"],
            "reward_type_id": type_id,
            "title": "Lịch sử khen thưởng",
            "reward_date": _TEST_DATE,
        })
        client.post(BASE, data={"body": payload}, headers=h)

        r = client.get(f"/api/v1/employees/{emp['id']}/rewards", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(item["employee_id"] == emp["id"] for item in data)

    def test_history_nonexistent_employee_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.get("/api/v1/employees/999999/rewards", headers=h)
        assert r.status_code == 404
