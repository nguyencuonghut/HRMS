"""Integration tests cho Plan 7.2 — Điều chỉnh mức lương BHXH.

Covers:
  - TestCreateAdjustment   : tạo điều chỉnh thành công + cập nhật profile
  - TestValidation         : validate đầu vào + nghiệp vụ
  - TestListAdjustments    : list + filter employee_id / date range / pagination
  - TestAdjustmentHistory  : lịch sử điều chỉnh theo nhân viên
  - TestIntegrationWith71  : sau khi điều chỉnh, mức lương trong salary-basis
                             được cập nhật và hiện đúng trong danh sách
"""
from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/salary"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"

_TEST_AMOUNT_1 = 7_500_000
_TEST_AMOUNT_2 = 8_000_000
_TEST_REASON = "Điều chỉnh lương BHXH theo quyết định thử nghiệm tích hợp"


# ── Auth ───────────────────────────────────────────────────────────────────────

def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── DB helpers ────────────────────────────────────────────────────────────────

def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _find_active_insured_employee() -> dict | None:
    """Trả về employee đang đóng BHXH và có mức lương BHXH xác định được."""
    async with _make_session()() as s:
        r = await s.execute(text("""
            SELECT e.id, e.full_name,
                   COALESCE(eip.insurance_basis_amount, ec.insurance_salary) AS basis_amount,
                   eip.participation_status
            FROM employees e
            JOIN employee_insurance_profiles eip ON eip.employee_id = e.id
            LEFT JOIN employee_contracts ec
                ON ec.employee_id = e.id AND ec.status = 'active'
            WHERE eip.participation_status = 'active'
              AND (
                eip.insurance_basis_amount IS NOT NULL
                OR (eip.insurance_basis_source = 'contract' AND ec.insurance_salary IS NOT NULL)
              )
              AND e.status != 'resigned'
            ORDER BY e.id
            LIMIT 1
        """))
        row = r.fetchone()
    if row is None:
        return None
    return {"id": row[0], "full_name": row[1], "basis_amount": row[2]}


async def _get_profile_basis(employee_id: int) -> dict | None:
    """Đọc insurance_basis_amount và source từ profile."""
    async with _make_session()() as s:
        r = await s.execute(text("""
            SELECT insurance_basis_amount, insurance_basis_source
            FROM employee_insurance_profiles
            WHERE employee_id = :eid
        """), {"eid": employee_id})
        row = r.fetchone()
    if row is None:
        return None
    return {"amount": row[0], "source": row[1]}


async def _reset_profile_basis(employee_id: int, amount: Decimal, source: str) -> None:
    """Khôi phục lại profile để test không bị side effect."""
    async with _make_session()() as s:
        await s.execute(text("""
            UPDATE employee_insurance_profiles
            SET insurance_basis_amount = :amt, insurance_basis_source = :src
            WHERE employee_id = :eid
        """), {"amt": amount, "src": source, "eid": employee_id})
        await s.commit()


async def _find_employee_without_profile() -> dict | None:
    """Trả về employee không có insurance profile."""
    async with _make_session()() as s:
        r = await s.execute(text("""
            SELECT e.id FROM employees e
            WHERE e.status != 'resigned'
              AND NOT EXISTS (
                SELECT 1 FROM employee_insurance_profiles eip
                WHERE eip.employee_id = e.id
              )
            LIMIT 1
        """))
        row = r.fetchone()
    if row is None:
        return None
    return {"id": row[0]}


async def _count_adjustments_for_employee(employee_id: int) -> int:
    async with _make_session()() as s:
        r = await s.execute(text("""
            SELECT COUNT(*) FROM bhxh_salary_adjustments WHERE employee_id = :eid
        """), {"eid": employee_id})
        return r.scalar_one()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def active_employee() -> dict:
    emp = asyncio.get_event_loop().run_until_complete(_find_active_insured_employee())
    if emp is None:
        pytest.skip("Không có nhân viên active đang đóng BHXH với mức lương xác định")
    return emp


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestCreateAdjustment:
    """Tạo điều chỉnh lương BHXH thành công."""

    def test_create_returns_adjustment_read(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        old_amount = Decimal(str(active_employee["basis_amount"]))
        new_amount = int(old_amount) + 500_000
        try:
            r = client.post(
                f"{BASE}/adjustments",
                json={
                    "employee_id": emp_id,
                    "new_basis_amount": new_amount,
                    "effective_date": str(date.today()),
                    "reason": _TEST_REASON,
                },
                headers=_admin(client),
            )
            assert r.status_code == 201, r.text
            data = r.json()
            assert data["employee_id"] == emp_id
            assert int(Decimal(data["new_basis_amount"])) == new_amount
            assert data["change_direction"] == "increase"
            assert data["insurance_change_event_id"] is not None
        finally:
            asyncio.get_event_loop().run_until_complete(
                _reset_profile_basis(emp_id, old_amount, "manual_fixed")
            )

    def test_create_updates_profile_basis_amount(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        old_amount = Decimal(str(active_employee["basis_amount"]))
        new_amount = int(old_amount) + 300_000
        try:
            client.post(
                f"{BASE}/adjustments",
                json={
                    "employee_id": emp_id,
                    "new_basis_amount": new_amount,
                    "effective_date": str(date.today()),
                    "reason": _TEST_REASON,
                },
                headers=_admin(client),
            )
            profile = asyncio.get_event_loop().run_until_complete(_get_profile_basis(emp_id))
            assert profile is not None
            assert int(Decimal(str(profile["amount"]))) == new_amount
            assert profile["source"] == "manual_fixed"
        finally:
            asyncio.get_event_loop().run_until_complete(
                _reset_profile_basis(emp_id, old_amount, "manual_fixed")
            )

    def test_create_decrease_sets_direction_decrease(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        old_amount = Decimal(str(active_employee["basis_amount"]))
        new_amount = max(500_000, int(old_amount) - 500_000)
        try:
            r = client.post(
                f"{BASE}/adjustments",
                json={
                    "employee_id": emp_id,
                    "new_basis_amount": new_amount,
                    "effective_date": str(date.today()),
                    "reason": _TEST_REASON,
                },
                headers=_admin(client),
            )
            assert r.status_code == 201, r.text
            assert r.json()["change_direction"] == "decrease"
        finally:
            asyncio.get_event_loop().run_until_complete(
                _reset_profile_basis(emp_id, old_amount, "manual_fixed")
            )

    def test_create_stores_decision_number(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        old_amount = Decimal(str(active_employee["basis_amount"]))
        new_amount = int(old_amount) + 200_000
        try:
            r = client.post(
                f"{BASE}/adjustments",
                json={
                    "employee_id": emp_id,
                    "new_basis_amount": new_amount,
                    "effective_date": str(date.today()),
                    "reason": _TEST_REASON,
                    "decision_number": "QĐ-TEST/2099",
                },
                headers=_admin(client),
            )
            assert r.status_code == 201, r.text
            assert r.json()["decision_number"] == "QĐ-TEST/2099"
        finally:
            asyncio.get_event_loop().run_until_complete(
                _reset_profile_basis(emp_id, old_amount, "manual_fixed")
            )


class TestValidation:
    """Validate đầu vào và nghiệp vụ."""

    def test_same_amount_returns_400(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        same_amount = int(Decimal(str(active_employee["basis_amount"])))

        r = client.post(
            f"{BASE}/adjustments",
            json={
                "employee_id": emp_id,
                "new_basis_amount": same_amount,
                "effective_date": str(date.today()),
                "reason": _TEST_REASON,
            },
            headers=_admin(client),
        )
        assert r.status_code == 400, r.text

    def test_missing_reason_returns_422(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        old_amount = int(Decimal(str(active_employee["basis_amount"])))

        r = client.post(
            f"{BASE}/adjustments",
            json={
                "employee_id": emp_id,
                "new_basis_amount": old_amount + 100_000,
                "effective_date": str(date.today()),
                # reason omitted
            },
            headers=_admin(client),
        )
        assert r.status_code == 422, r.text

    def test_nonexistent_employee_returns_404(self, client: TestClient):
        r = client.post(
            f"{BASE}/adjustments",
            json={
                "employee_id": 999_999_999,
                "new_basis_amount": _TEST_AMOUNT_1,
                "effective_date": str(date.today()),
                "reason": _TEST_REASON,
            },
            headers=_admin(client),
        )
        assert r.status_code == 404, r.text

    def test_employee_without_profile_returns_422(self, client: TestClient):
        emp = asyncio.get_event_loop().run_until_complete(_find_employee_without_profile())
        if emp is None:
            pytest.skip("Không có nhân viên thiếu profile bảo hiểm")

        r = client.post(
            f"{BASE}/adjustments",
            json={
                "employee_id": emp["id"],
                "new_basis_amount": _TEST_AMOUNT_1,
                "effective_date": str(date.today()),
                "reason": _TEST_REASON,
            },
            headers=_admin(client),
        )
        assert r.status_code == 422, r.text

    def test_unauthenticated_returns_401(self, client: TestClient, active_employee: dict):
        r = client.post(
            f"{BASE}/adjustments",
            json={
                "employee_id": active_employee["id"],
                "new_basis_amount": _TEST_AMOUNT_1,
                "effective_date": str(date.today()),
                "reason": _TEST_REASON,
            },
        )
        assert r.status_code == 401, r.text


class TestListAdjustments:
    """List điều chỉnh với filter."""

    def test_list_returns_paginated(self, client: TestClient):
        r = client.get(f"{BASE}/adjustments?page=1&page_size=10", headers=_admin(client))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_filter_by_employee_id(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        old_amount = Decimal(str(active_employee["basis_amount"]))
        new_amount = int(old_amount) + 100_000
        try:
            client.post(
                f"{BASE}/adjustments",
                json={
                    "employee_id": emp_id,
                    "new_basis_amount": new_amount,
                    "effective_date": str(date.today()),
                    "reason": _TEST_REASON,
                },
                headers=_admin(client),
            )
            r = client.get(
                f"{BASE}/adjustments?employee_id={emp_id}", headers=_admin(client)
            )
            assert r.status_code == 200, r.text
            items = r.json()["items"]
            assert len(items) >= 1
            assert all(i["employee_id"] == emp_id for i in items)
        finally:
            asyncio.get_event_loop().run_until_complete(
                _reset_profile_basis(emp_id, old_amount, "manual_fixed")
            )

    def test_filter_by_date_range(self, client: TestClient):
        today = date.today()
        r = client.get(
            f"{BASE}/adjustments?from_date={today}&to_date={today}",
            headers=_admin(client),
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        for item in items:
            assert item["effective_date"] == str(today)

    def test_pagination_page_size(self, client: TestClient):
        r = client.get(f"{BASE}/adjustments?page=1&page_size=2", headers=_admin(client))
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["items"]) <= 2


class TestAdjustmentHistory:
    """Lịch sử điều chỉnh của một nhân viên cụ thể."""

    def test_history_returns_list_for_valid_employee(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        r = client.get(
            f"{BASE}/employees/{emp_id}/adjustment-history",
            headers=_admin(client),
        )
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_history_includes_created_adjustment(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        old_amount = Decimal(str(active_employee["basis_amount"]))
        new_amount = int(old_amount) + 150_000
        try:
            client.post(
                f"{BASE}/adjustments",
                json={
                    "employee_id": emp_id,
                    "new_basis_amount": new_amount,
                    "effective_date": str(date.today()),
                    "reason": _TEST_REASON,
                },
                headers=_admin(client),
            )
            r = client.get(
                f"{BASE}/employees/{emp_id}/adjustment-history",
                headers=_admin(client),
            )
            assert r.status_code == 200, r.text
            items = r.json()
            assert len(items) >= 1
            assert any(int(Decimal(i["new_basis_amount"])) == new_amount for i in items)
        finally:
            asyncio.get_event_loop().run_until_complete(
                _reset_profile_basis(emp_id, old_amount, "manual_fixed")
            )

    def test_history_nonexistent_employee_returns_404(self, client: TestClient):
        r = client.get(
            f"{BASE}/employees/999999999/adjustment-history",
            headers=_admin(client),
        )
        assert r.status_code == 404, r.text

    def test_history_sorted_descending_by_effective_date(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        r = client.get(
            f"{BASE}/employees/{emp_id}/adjustment-history",
            headers=_admin(client),
        )
        assert r.status_code == 200, r.text
        items = r.json()
        dates = [i["effective_date"] for i in items]
        assert dates == sorted(dates, reverse=True)


class TestIntegrationWith71:
    """Sau khi điều chỉnh, mức lương hiện ra đúng trong salary-basis."""

    def test_basis_amount_reflects_after_adjustment(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        old_amount = Decimal(str(active_employee["basis_amount"]))
        new_amount = int(old_amount) + 250_000
        try:
            client.post(
                f"{BASE}/adjustments",
                json={
                    "employee_id": emp_id,
                    "new_basis_amount": new_amount,
                    "effective_date": str(date.today()),
                    "reason": _TEST_REASON,
                },
                headers=_admin(client),
            )
            r = client.get(f"{BASE}/employees/{emp_id}/bhxh-basis", headers=_admin(client))
            assert r.status_code == 200, r.text
            basis = r.json()
            assert int(Decimal(str(basis["insurance_basis_amount"]))) == new_amount
            assert basis["insurance_basis_source"] == "manual_fixed"
        finally:
            asyncio.get_event_loop().run_until_complete(
                _reset_profile_basis(emp_id, old_amount, "manual_fixed")
            )

    def test_source_becomes_manual_fixed_after_adjustment(
        self, client: TestClient, active_employee: dict
    ):
        emp_id = active_employee["id"]
        old_amount = Decimal(str(active_employee["basis_amount"]))
        new_amount = int(old_amount) + 100_000
        try:
            client.post(
                f"{BASE}/adjustments",
                json={
                    "employee_id": emp_id,
                    "new_basis_amount": new_amount,
                    "effective_date": str(date.today()),
                    "reason": _TEST_REASON,
                },
                headers=_admin(client),
            )
            profile = asyncio.get_event_loop().run_until_complete(_get_profile_basis(emp_id))
            assert profile is not None
            assert profile["source"] == "manual_fixed"
        finally:
            asyncio.get_event_loop().run_until_complete(
                _reset_profile_basis(emp_id, old_amount, "manual_fixed")
            )
