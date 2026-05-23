"""Integration tests cho Plan 7.1 — Mức lương BHXH (xem / lịch sử).

Covers:
  - TestListSalaryEmployees : list + filter dept/status/search + discrepancy
  - TestGetBhxhBasis        : chi tiết mức lương BHXH của một nhân viên
  - TestGetBhxhHistory      : lịch sử mức lương BHXH
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/salary"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"


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


async def _find_employee_with_contract_and_profile() -> dict:
    """Trả về employee có cả profile + active contract với insurance_salary."""
    async with _make_session()() as s:
        r = await s.execute(text("""
            SELECT e.id, e.full_name, ejr.department_id,
                   eip.insurance_basis_amount, eip.insurance_basis_source,
                   eip.participation_status,
                   ec.insurance_salary AS contract_salary
            FROM employees e
            JOIN employee_insurance_profiles eip ON eip.employee_id = e.id
            JOIN employee_contracts ec
                ON ec.employee_id = e.id
               AND ec.status = 'active'
               AND ec.insurance_salary IS NOT NULL
               AND ec.insurance_salary > 0
            LEFT JOIN employee_job_records ejr
                ON ejr.employee_id = e.id AND ejr.is_current = true
            WHERE e.status != 'resigned'
            ORDER BY e.id
            LIMIT 1
        """))
        row = r.fetchone()
        assert row is not None, "Không tìm thấy employee đủ điều kiện cho test"
        return {
            "id": row[0],
            "full_name": row[1],
            "department_id": row[2],
            "basis_amount": row[3],
            "basis_source": row[4],
            "participation_status": row[5],
            "contract_salary": row[6],
        }


async def _find_employee_no_profile() -> dict | None:
    """Trả về employee KHÔNG có insurance_profile, hoặc None nếu không có."""
    async with _make_session()() as s:
        r = await s.execute(text("""
            SELECT e.id, e.full_name
            FROM employees e
            LEFT JOIN employee_insurance_profiles eip ON eip.employee_id = e.id
            WHERE eip.id IS NULL AND e.status != 'resigned'
            ORDER BY e.id
            LIMIT 1
        """))
        row = r.fetchone()
        if row is None:
            return None
        return {"id": row[0], "full_name": row[1]}


async def _find_employee_manual_fixed_with_contract() -> dict | None:
    """Trả về employee có source=manual_fixed VÀ active contract, để kiểm discrepancy."""
    async with _make_session()() as s:
        r = await s.execute(text("""
            SELECT e.id
            FROM employees e
            JOIN employee_insurance_profiles eip ON eip.employee_id = e.id
            JOIN employee_contracts ec
                ON ec.employee_id = e.id
               AND ec.status = 'active'
               AND ec.insurance_salary IS NOT NULL
            WHERE eip.insurance_basis_source = 'manual_fixed'
              AND eip.insurance_basis_amount IS NOT NULL
              AND eip.insurance_basis_amount != ec.insurance_salary
              AND e.status != 'resigned'
            ORDER BY e.id
            LIMIT 1
        """))
        row = r.fetchone()
        if row is None:
            return None
        return {"id": row[0]}


async def _find_department_with_employees() -> int | None:
    """Trả về department_id có ít nhất 1 employee đang active."""
    async with _make_session()() as s:
        r = await s.execute(text("""
            SELECT ejr.department_id
            FROM employee_job_records ejr
            JOIN employees e ON e.id = ejr.employee_id
            WHERE ejr.is_current = true AND e.status != 'resigned'
            GROUP BY ejr.department_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
        """))
        row = r.fetchone()
        return row[0] if row else None


# ══════════════════════════════════════════════════════════════════════════════
# TestListSalaryEmployees
# ══════════════════════════════════════════════════════════════════════════════

class TestListSalaryEmployees:

    def test_list_returns_paginated_result(self, client: TestClient):
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body
        assert isinstance(body["items"], list)
        assert body["total"] >= 0

    def test_list_each_item_has_required_fields(self, client: TestClient):
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees", headers=headers, params={"page_size": 5})
        assert resp.status_code == 200
        items = resp.json()["items"]
        if not items:
            pytest.skip("Không có dữ liệu để kiểm tra fields")
        required = {"employee_id", "employee_code", "full_name", "has_discrepancy"}
        for item in items:
            assert required.issubset(item.keys()), f"Thiếu fields: {required - item.keys()}"

    @pytest.mark.asyncio
    async def test_filter_by_department(self, client: TestClient):
        dept_id = await _find_department_with_employees()
        if dept_id is None:
            pytest.skip("Không tìm thấy department phù hợp")
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees", headers=headers,
                          params={"department_id": dept_id})
        assert resp.status_code == 200
        body = resp.json()
        # Tất cả kết quả phải thuộc department đó
        for item in body["items"]:
            assert item["department_id"] == dept_id

    def test_filter_by_status_active(self, client: TestClient):
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees", headers=headers,
                          params={"participation_status": "active"})
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["participation_status"] == "active"

    def test_filter_by_status_paused(self, client: TestClient):
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees", headers=headers,
                          params={"participation_status": "paused"})
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["participation_status"] == "paused"

    def test_search_by_name(self, client: TestClient):
        headers = _admin(client)
        # Search với keyword ngắn — kiểm rằng kết quả không chứa những tên không liên quan
        resp = client.get(f"{BASE}/employees", headers=headers,
                          params={"search": "van"})
        assert resp.status_code == 200
        # Ít nhất endpoint hoạt động không lỗi
        assert isinstance(resp.json()["items"], list)

    @pytest.mark.asyncio
    async def test_discrepancy_flag_true_when_manual_and_differs_from_contract(
        self, client: TestClient
    ):
        emp = await _find_employee_manual_fixed_with_contract()
        if emp is None:
            pytest.skip("Không tìm thấy employee manual_fixed với discrepancy")
        headers = _admin(client)
        # Tìm employee cụ thể trong list
        resp = client.get(f"{BASE}/employees", headers=headers, params={"page_size": 200})
        assert resp.status_code == 200
        items = {i["employee_id"]: i for i in resp.json()["items"]}
        assert emp["id"] in items
        assert items[emp["id"]]["has_discrepancy"] is True

    @pytest.mark.asyncio
    async def test_employee_without_profile_returns_null_fields(self, client: TestClient):
        emp = await _find_employee_no_profile()
        if emp is None:
            pytest.skip("Không có employee nào thiếu insurance_profile trong DB test")
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees", headers=headers, params={"page_size": 200})
        assert resp.status_code == 200
        items = {i["employee_id"]: i for i in resp.json()["items"]}
        if emp["id"] not in items:
            pytest.skip("Employee không có profile không xuất hiện trong list (đã lọc)")
        row = items[emp["id"]]
        assert row["insurance_basis_amount"] is None
        assert row["participation_status"] is None
        assert row["has_discrepancy"] is False

    def test_pagination_page2_different_from_page1(self, client: TestClient):
        headers = _admin(client)
        p1 = client.get(f"{BASE}/employees", headers=headers,
                        params={"page": 1, "page_size": 5}).json()
        if p1["total"] <= 5:
            pytest.skip("Không đủ dữ liệu để kiểm tra pagination")
        p2 = client.get(f"{BASE}/employees", headers=headers,
                        params={"page": 2, "page_size": 5}).json()
        ids_p1 = {i["employee_id"] for i in p1["items"]}
        ids_p2 = {i["employee_id"] for i in p2["items"]}
        assert ids_p1.isdisjoint(ids_p2), "Page 1 và Page 2 không được chứa cùng employee"

    def test_unauthenticated_returns_401(self, client: TestClient):
        resp = client.get(f"{BASE}/employees")
        assert resp.status_code == 401

    def test_invalid_status_returns_no_results(self, client: TestClient):
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees", headers=headers,
                          params={"participation_status": "nonexistent_status"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# TestGetBhxhBasis
# ══════════════════════════════════════════════════════════════════════════════

class TestGetBhxhBasis:

    @pytest.mark.asyncio
    async def test_get_basis_returns_correct_fields(self, client: TestClient):
        emp = await _find_employee_with_contract_and_profile()
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees/{emp['id']}/bhxh-basis", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["employee_id"] == emp["id"]
        assert body["full_name"] == emp["full_name"]
        assert "insurance_basis_amount" in body
        assert "insurance_basis_source" in body
        assert "participation_status" in body
        assert "has_discrepancy" in body

    def test_get_basis_404_for_nonexistent_employee(self, client: TestClient):
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees/999999999/bhxh-basis", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_basis_shows_active_contract_salary(self, client: TestClient):
        emp = await _find_employee_with_contract_and_profile()
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees/{emp['id']}/bhxh-basis", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        # Employee này có active contract với insurance_salary
        assert body["active_contract_insurance_salary"] is not None
        assert float(body["active_contract_insurance_salary"]) > 0


# ══════════════════════════════════════════════════════════════════════════════
# TestGetBhxhHistory
# ══════════════════════════════════════════════════════════════════════════════

class TestGetBhxhHistory:

    @pytest.mark.asyncio
    async def test_history_sorted_descending_by_effective_date(self, client: TestClient):
        emp = await _find_employee_with_contract_and_profile()
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees/{emp['id']}/bhxh-history", headers=headers)
        assert resp.status_code == 200
        items = resp.json()
        if len(items) < 2:
            pytest.skip("Không đủ lịch sử để kiểm tra thứ tự sắp xếp")
        dates = [i["effective_date"] for i in items]
        assert dates == sorted(dates, reverse=True), "Lịch sử phải sắp xếp giảm dần"

    @pytest.mark.asyncio
    async def test_history_excludes_contracts_without_insurance_salary(self, client: TestClient):
        """Contracts với insurance_salary=NULL không được xuất hiện trong history."""
        emp = await _find_employee_with_contract_and_profile()
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees/{emp['id']}/bhxh-history", headers=headers)
        assert resp.status_code == 200
        for item in resp.json():
            if item["source_type"] == "contract":
                assert item["basis_amount"] is not None

    def test_history_404_for_nonexistent_employee(self, client: TestClient):
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees/999999999/bhxh-history", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_history_returns_list(self, client: TestClient):
        emp = await _find_employee_with_contract_and_profile()
        headers = _admin(client)
        resp = client.get(f"{BASE}/employees/{emp['id']}/bhxh-history", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        # Ít nhất 1 item từ active contract đã biết
        assert len(body) >= 1
        # Mỗi item phải có các fields cần thiết
        for item in body:
            assert "effective_date" in item
            assert "basis_amount" in item
            assert "source_type" in item
