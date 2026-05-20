"""Integration tests cho Slice 2 — Employee Insurance API + Computation Snapshot."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/insurance"
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


async def _get_first_employee_id() -> int:
    async with _make_session()() as s:
        row = (await s.execute(text("SELECT id FROM employees ORDER BY id LIMIT 1"))).one()
        return row[0]


async def _reset_profile(employee_id: int) -> None:
    async with _make_session()() as s:
        await s.execute(
            text(
                """
                UPDATE employee_insurance_profiles
                SET bhxh_code = NULL,
                    bhyt_initial_clinic_name = NULL,
                    company_bhxh_joined_date = NULL,
                    participation_status = 'active',
                    status_effective_from = NULL,
                    status_note = NULL,
                    insurance_basis_source = 'contract',
                    insurance_basis_amount = NULL
                WHERE employee_id = :eid
                """
            ),
            {"eid": employee_id},
        )
        await s.execute(
            text(
                """
                DELETE FROM employee_insurance_component_overrides
                WHERE employee_insurance_profile_id IN (
                    SELECT id FROM employee_insurance_profiles WHERE employee_id = :eid
                )
                """
            ),
            {"eid": employee_id},
        )
        await s.commit()


@pytest.fixture
async def emp_id() -> int:
    eid = await _get_first_employee_id()
    await _reset_profile(eid)
    yield eid
    await _reset_profile(eid)


# ── List endpoint ─────────────────────────────────────────────────────────────

def test_list_returns_paginated_result(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}/employees", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "page_size" in body
    assert body["total"] > 0
    assert len(body["items"]) > 0


def test_list_item_has_required_fields(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}/employees?page_size=1", headers=headers)
    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    for field in [
        "employee_id", "employee_code", "employee_name",
        "participation_status", "insurance_basis_source",
        "has_component_overrides", "employer_pays_on_behalf",
        "contributions",
    ]:
        assert field in item, f"Thiếu field: {field}"


def test_list_filter_participation_status(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}/employees?participation_status=active", headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    for item in items:
        assert item["participation_status"] == "active"


def test_list_filter_has_bhxh_code_false(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}/employees?has_bhxh_code=false", headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    for item in items:
        assert item["bhxh_code"] is None


def test_list_filter_keyword(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}/employees?keyword=a&page_size=5", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] >= 0


def test_list_pagination(client: TestClient):
    headers = _admin(client)
    resp_all = client.get(f"{BASE}/employees?page_size=200", headers=headers)
    total = resp_all.json()["total"]
    if total >= 2:
        resp_p1 = client.get(f"{BASE}/employees?page=1&page_size=1", headers=headers)
        resp_p2 = client.get(f"{BASE}/employees?page=2&page_size=1", headers=headers)
        assert resp_p1.json()["items"][0]["employee_id"] != resp_p2.json()["items"][0]["employee_id"]


def test_list_requires_auth(client: TestClient):
    resp = client.get(f"{BASE}/employees")
    assert resp.status_code == 401


# ── Detail endpoint ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_detail_returns_profile(client: TestClient, emp_id: int):
    headers = _admin(client)
    resp = client.get(f"{BASE}/employees/{emp_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["employee_id"] == emp_id
    assert "employee_code" in body
    assert "employee_name" in body
    assert "participation_status" in body
    assert "contributions" in body
    assert "created_at" in body


def test_get_detail_404_on_nonexistent(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}/employees/999999999", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_detail_contributions_present_when_policy_active(client: TestClient, emp_id: int):
    headers = _admin(client)
    # Check if there's an active policy first
    policy_resp = client.get(f"{BASE}/policy-versions", headers=headers)
    active_policies = [p for p in policy_resp.json() if p["is_active"]]
    if not active_policies:
        pytest.skip("Không có policy active trong DB test")

    resp = client.get(f"{BASE}/employees/{emp_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # contributions should list all active components
    assert isinstance(body["contributions"], list)
    if active_policies:
        assert len(body["contributions"]) > 0
        first = body["contributions"][0]
        assert "component_code" in first
        assert "calc_mode" in first
        assert "employer_advances_employee_part" in first


# ── Upsert endpoint ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_updates_bhxh_code(client: TestClient, emp_id: int):
    headers = _admin(client)
    resp = client.put(
        f"{BASE}/employees/{emp_id}",
        json={
            "bhxh_code": "0123456789",
            "participation_status": "active",
            "insurance_basis_source": "contract",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["bhxh_code"] == "0123456789"

    # Verify via detail endpoint
    detail = client.get(f"{BASE}/employees/{emp_id}", headers=headers).json()
    assert detail["bhxh_code"] == "0123456789"


@pytest.mark.asyncio
async def test_upsert_sets_clinic_and_joined_date(client: TestClient, emp_id: int):
    headers = _admin(client)
    resp = client.put(
        f"{BASE}/employees/{emp_id}",
        json={
            "participation_status": "active",
            "insurance_basis_source": "contract",
            "bhyt_initial_clinic_name": "Bệnh viện Bạch Mai",
            "company_bhxh_joined_date": "2023-01-01",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["bhyt_initial_clinic_name"] == "Bệnh viện Bạch Mai"
    assert body["company_bhxh_joined_date"] == "2023-01-01"


@pytest.mark.asyncio
async def test_upsert_stopped_requires_effective_from(client: TestClient, emp_id: int):
    headers = _admin(client)
    resp = client.put(
        f"{BASE}/employees/{emp_id}",
        json={
            "participation_status": "stopped",
            "insurance_basis_source": "contract",
            # Missing status_effective_from
        },
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_upsert_stopped_with_effective_from_ok(client: TestClient, emp_id: int):
    headers = _admin(client)
    resp = client.put(
        f"{BASE}/employees/{emp_id}",
        json={
            "participation_status": "stopped",
            "status_effective_from": "2024-06-01",
            "status_note": "Nghỉ việc",
            "insurance_basis_source": "contract",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["participation_status"] == "stopped"


@pytest.mark.asyncio
async def test_upsert_manual_fixed_basis(client: TestClient, emp_id: int):
    headers = _admin(client)
    resp = client.put(
        f"{BASE}/employees/{emp_id}",
        json={
            "participation_status": "active",
            "insurance_basis_source": "manual_fixed",
            "insurance_basis_amount": 10000000,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["insurance_basis_source"] == "manual_fixed"
    assert float(body["insurance_basis_amount"]) == 10000000


@pytest.mark.asyncio
async def test_upsert_manual_fixed_requires_amount(client: TestClient, emp_id: int):
    headers = _admin(client)
    resp = client.put(
        f"{BASE}/employees/{emp_id}",
        json={
            "participation_status": "active",
            "insurance_basis_source": "manual_fixed",
            # Missing insurance_basis_amount
        },
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_upsert_with_component_overrides(client: TestClient, emp_id: int):
    headers = _admin(client)
    # Get active components first
    comps_resp = client.get(f"{BASE}/components", headers=headers)
    assert comps_resp.status_code == 200
    components = [c for c in comps_resp.json() if c["is_active"]]
    if not components:
        pytest.skip("Không có component active")

    comp_code = components[0]["code"]
    resp = client.put(
        f"{BASE}/employees/{emp_id}",
        json={
            "participation_status": "active",
            "insurance_basis_source": "contract",
            "component_overrides": [
                {
                    "component_code": comp_code,
                    "use_company_default": False,
                    "fixed_employee_amount": 200000,
                    "fixed_employer_amount": 300000,
                }
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_component_overrides"] is True

    # The override component should appear with calc_mode=fixed_amount
    override_snap = next(
        (c for c in body["contributions"] if c["component_code"] == comp_code), None
    )
    if override_snap:
        assert override_snap["calc_mode"] == "fixed_amount"
        assert float(override_snap["fixed_employee_amount"]) == 200000


@pytest.mark.asyncio
async def test_upsert_override_use_company_default_rejects_fixed_amounts(client: TestClient, emp_id: int):
    headers = _admin(client)
    comps_resp = client.get(f"{BASE}/components", headers=headers)
    components = [c for c in comps_resp.json() if c["is_active"]]
    if not components:
        pytest.skip("Không có component active")

    comp_code = components[0]["code"]
    resp = client.put(
        f"{BASE}/employees/{emp_id}",
        json={
            "participation_status": "active",
            "insurance_basis_source": "contract",
            "component_overrides": [
                {
                    "component_code": comp_code,
                    "use_company_default": True,
                    "fixed_employee_amount": 200000,  # invalid: use_company_default=True
                }
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_upsert_overrides_replaced_on_second_call(client: TestClient, emp_id: int):
    headers = _admin(client)
    comps_resp = client.get(f"{BASE}/components", headers=headers)
    components = [c for c in comps_resp.json() if c["is_active"]]
    if len(components) < 1:
        pytest.skip("Cần ít nhất 1 component active")

    comp_code = components[0]["code"]
    # First call: add override
    client.put(
        f"{BASE}/employees/{emp_id}",
        json={
            "participation_status": "active",
            "insurance_basis_source": "contract",
            "component_overrides": [
                {
                    "component_code": comp_code,
                    "use_company_default": False,
                    "fixed_employee_amount": 100000,
                    "fixed_employer_amount": 150000,
                }
            ],
        },
        headers=headers,
    )
    # Second call: clear overrides
    resp2 = client.put(
        f"{BASE}/employees/{emp_id}",
        json={
            "participation_status": "active",
            "insurance_basis_source": "contract",
            "component_overrides": [],
        },
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["has_component_overrides"] is False


def test_upsert_404_on_nonexistent(client: TestClient):
    headers = _admin(client)
    resp = client.put(
        f"{BASE}/employees/999999999",
        json={"participation_status": "active", "insurance_basis_source": "contract"},
        headers=headers,
    )
    assert resp.status_code == 404


# ── Contribution snapshot logic ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_contributions_use_company_policy_by_default(client: TestClient, emp_id: int):
    headers = _admin(client)
    policy_resp = client.get(f"{BASE}/policy-versions", headers=headers)
    active_policies = [p for p in policy_resp.json() if p["is_active"]]
    if not active_policies:
        pytest.skip("Cần policy active")

    # Reset to company default (no overrides)
    client.put(
        f"{BASE}/employees/{emp_id}",
        json={"participation_status": "active", "insurance_basis_source": "contract", "component_overrides": []},
        headers=headers,
    )
    detail = client.get(f"{BASE}/employees/{emp_id}", headers=headers).json()
    for contrib in detail["contributions"]:
        assert contrib["calc_mode"] == "company_policy", f"Component {contrib['component_code']} should use company_policy"


@pytest.mark.asyncio
async def test_manual_fixed_basis_computes_amounts(client: TestClient, emp_id: int):
    headers = _admin(client)
    policy_resp = client.get(f"{BASE}/policy-versions", headers=headers)
    active_policies = [p for p in policy_resp.json() if p["is_active"]]
    if not active_policies:
        pytest.skip("Cần policy active")

    basis = 10_000_000
    client.put(
        f"{BASE}/employees/{emp_id}",
        json={
            "participation_status": "active",
            "insurance_basis_source": "manual_fixed",
            "insurance_basis_amount": basis,
            "component_overrides": [],
        },
        headers=headers,
    )
    detail = client.get(f"{BASE}/employees/{emp_id}", headers=headers).json()
    for contrib in detail["contributions"]:
        if contrib["employee_rate_percent"] is not None:
            rate = float(contrib["employee_rate_percent"])
            expected = round(basis * rate / 100)
            actual = float(contrib["employee_amount"])
            assert abs(actual - expected) <= 1, (
                f"Component {contrib['component_code']}: expected {expected}, got {actual}"
            )
