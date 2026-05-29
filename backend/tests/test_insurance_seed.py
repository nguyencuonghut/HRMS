"""Integration tests cho Slice 1 — seed insurance components + policy version baseline.

Lưu ý: Migration 0018 đã seed:
  - 5 components (insurance_kind lowercase: bhxh/bhyt/bhtn, sort_order 10/20/30/40/50)
  - Policy VN_STANDARD_2026_01_01 (is_active=TRUE, effective_from=2026-01-01)

Các hàm seed trong required.py là belt-and-suspenders cho fresh env không có migration data.
Tests này verify cả state sau migration và idempotency của seeder.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import engine as app_engine
from app.seeds.required import seed_insurance_components, seed_insurance_policy_version_baseline

BASE = "/api/v1/insurance"

# Khớp với migration 0018
_MIGRATION_POLICY_CODE = "VN_STANDARD_2026_01_01"
_EXPECTED_COMPONENT_CODES = {
    "RETIREMENT_SURVIVOR",
    "SICKNESS_MATERNITY",
    "OCC_ACCIDENT_DISEASE",
    "HEALTH",
    "UNEMPLOYMENT",
}

# Tổng tỷ lệ theo FEATURES.md §6.2
_EXPECTED_EMPLOYEE_TOTAL = Decimal("10.5")
_EXPECTED_EMPLOYER_TOTAL = Decimal("21.5")

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


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from app.main import app
    asyncio.run(app_engine.dispose())
    with TestClient(app) as c:
        yield c
    asyncio.run(app_engine.dispose())


@pytest.fixture(autouse=True, scope="module")
async def restore_migration_policy():
    """Đảm bảo VN_STANDARD_2026_01_01 là active policy trước khi chạy tests.

    Các test khác (test_insurance_policy_api.py) có thể đã activate policy khác.
    """
    async with _make_session()() as s:
        await s.execute(text("UPDATE insurance_policy_versions SET is_active = FALSE, effective_to = NULL"))
        await s.execute(
            text("UPDATE insurance_policy_versions SET is_active = TRUE WHERE code = :code"),
            {"code": _MIGRATION_POLICY_CODE},
        )
        await s.commit()
    yield
    # Không cần teardown — state này là đúng


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_active_policy() -> dict | None:
    async with _make_session()() as s:
        result = await s.execute(
            text("SELECT id, code, effective_from FROM insurance_policy_versions WHERE is_active = TRUE LIMIT 1")
        )
        row = result.fetchone()
        return {"id": row[0], "code": row[1], "effective_from": row[2]} if row else None


async def _get_component_rates(policy_id: int) -> list[dict]:
    async with _make_session()() as s:
        result = await s.execute(
            text("""
                SELECT component_code, employee_rate_percent, employer_rate_percent,
                       employer_advances_employee_part
                FROM insurance_policy_component_rates
                WHERE policy_version_id = :pid
            """),
            {"pid": policy_id},
        )
        return [
            {
                "component_code": row[0],
                "employee_rate_percent": Decimal(str(row[1])),
                "employer_rate_percent": Decimal(str(row[2])),
                "employer_advances_employee_part": row[3],
            }
            for row in result.fetchall()
        ]


# ── Tests: insurance_contribution_components (migration data) ──────────────────

class TestInsuranceComponents:

    @pytest.mark.anyio
    async def test_five_active_components_exist(self):
        async with _make_session()() as s:
            result = await s.execute(
                text("SELECT COUNT(*) FROM insurance_contribution_components WHERE is_active = TRUE")
            )
        assert result.scalar() == 5

    @pytest.mark.anyio
    async def test_component_codes_are_correct(self):
        async with _make_session()() as s:
            result = await s.execute(
                text("SELECT code FROM insurance_contribution_components WHERE is_active = TRUE")
            )
            codes = {row[0] for row in result.fetchall()}
        assert codes == _EXPECTED_COMPONENT_CODES

    @pytest.mark.anyio
    async def test_insurance_kinds_are_assigned(self):
        """Migration seed dùng lowercase: bhxh, bhyt, bhtn."""
        async with _make_session()() as s:
            result = await s.execute(
                text("SELECT code, insurance_kind FROM insurance_contribution_components WHERE is_active = TRUE")
            )
            rows = {row[0]: row[1] for row in result.fetchall()}

        assert rows["RETIREMENT_SURVIVOR"].lower() == "bhxh"
        assert rows["SICKNESS_MATERNITY"].lower() == "bhxh"
        assert rows["OCC_ACCIDENT_DISEASE"].lower() == "bhxh"
        assert rows["HEALTH"].lower() == "bhyt"
        assert rows["UNEMPLOYMENT"].lower() == "bhtn"

    @pytest.mark.anyio
    async def test_sort_orders_are_unique_and_ordered(self):
        async with _make_session()() as s:
            result = await s.execute(
                text("SELECT sort_order FROM insurance_contribution_components WHERE is_active = TRUE ORDER BY sort_order")
            )
            orders = [row[0] for row in result.fetchall()]
        assert len(orders) == 5
        assert orders == sorted(orders), "sort_order phải tăng dần"
        assert len(set(orders)) == 5, "sort_order phải unique"

    @pytest.mark.anyio
    async def test_seed_components_is_idempotent(self):
        """Chạy seed_insurance_components khi đã có data → không insert thêm."""
        async with _make_session()() as s:
            added = await seed_insurance_components(s)
            await s.commit()
        assert added == 0

        async with _make_session()() as s:
            result = await s.execute(
                text("SELECT COUNT(*) FROM insurance_contribution_components WHERE is_active = TRUE")
            )
            assert result.scalar() == 5


# ── Tests: insurance_policy_versions (migration data) ─────────────────────────

class TestInsurancePolicyVersionBaseline:

    @pytest.mark.anyio
    async def test_exactly_one_active_policy(self):
        async with _make_session()() as s:
            result = await s.execute(
                text("SELECT COUNT(*) FROM insurance_policy_versions WHERE is_active = TRUE")
            )
        assert result.scalar() == 1

    @pytest.mark.anyio
    async def test_active_policy_is_migration_seeded(self):
        policy = await _get_active_policy()
        assert policy is not None
        assert policy["code"] == _MIGRATION_POLICY_CODE

    @pytest.mark.anyio
    async def test_active_policy_has_five_component_rates(self):
        policy = await _get_active_policy()
        rates = await _get_component_rates(policy["id"])
        assert len(rates) == 5

    @pytest.mark.anyio
    async def test_active_policy_covers_all_component_codes(self):
        policy = await _get_active_policy()
        rates = await _get_component_rates(policy["id"])
        codes = {r["component_code"] for r in rates}
        assert codes == _EXPECTED_COMPONENT_CODES

    @pytest.mark.anyio
    async def test_employee_total_rate_matches_spec(self):
        """NLĐ tổng = 10.5% theo FEATURES.md §6.2."""
        policy = await _get_active_policy()
        rates = await _get_component_rates(policy["id"])
        total = sum(r["employee_rate_percent"] for r in rates)
        assert total == _EXPECTED_EMPLOYEE_TOTAL, (
            f"Tổng NLĐ kỳ vọng {_EXPECTED_EMPLOYEE_TOTAL}%, nhận {total}%"
        )

    @pytest.mark.anyio
    async def test_employer_total_rate_matches_spec(self):
        """NSDLĐ tổng = 21.5% theo FEATURES.md §6.2."""
        policy = await _get_active_policy()
        rates = await _get_component_rates(policy["id"])
        total = sum(r["employer_rate_percent"] for r in rates)
        assert total == _EXPECTED_EMPLOYER_TOTAL, (
            f"Tổng NSDLĐ kỳ vọng {_EXPECTED_EMPLOYER_TOTAL}%, nhận {total}%"
        )

    @pytest.mark.anyio
    async def test_individual_rates_are_correct(self):
        """Tỷ lệ từng component theo căn cứ pháp lý."""
        policy = await _get_active_policy()
        rates = await _get_component_rates(policy["id"])
        rate_map = {r["component_code"]: r for r in rates}

        # Luật BHXH 2024 Điều 85–87
        assert rate_map["RETIREMENT_SURVIVOR"]["employee_rate_percent"] == Decimal("8")
        assert rate_map["RETIREMENT_SURVIVOR"]["employer_rate_percent"] == Decimal("14")
        assert rate_map["SICKNESS_MATERNITY"]["employee_rate_percent"] == Decimal("0")
        assert rate_map["SICKNESS_MATERNITY"]["employer_rate_percent"] == Decimal("3")
        assert rate_map["OCC_ACCIDENT_DISEASE"]["employee_rate_percent"] == Decimal("0")
        assert rate_map["OCC_ACCIDENT_DISEASE"]["employer_rate_percent"] == Decimal("0.5")
        # NĐ 188/2025/NĐ-CP
        assert rate_map["HEALTH"]["employee_rate_percent"] == Decimal("1.5")
        assert rate_map["HEALTH"]["employer_rate_percent"] == Decimal("3")
        # Luật Việc làm 2025
        assert rate_map["UNEMPLOYMENT"]["employee_rate_percent"] == Decimal("1")
        assert rate_map["UNEMPLOYMENT"]["employer_rate_percent"] == Decimal("1")

    @pytest.mark.anyio
    async def test_all_employer_advances_default_false(self):
        """Cờ employer_advances_employee_part phải FALSE theo mặc định."""
        policy = await _get_active_policy()
        rates = await _get_component_rates(policy["id"])
        for r in rates:
            assert r["employer_advances_employee_part"] is False, (
                f"Component {r['component_code']} có employer_advances = True"
            )

    @pytest.mark.anyio
    async def test_seed_policy_skips_if_any_policy_exists(self):
        """seed_insurance_policy_version_baseline bỏ qua khi đã có policy."""
        async with _make_session()() as s:
            result = await seed_insurance_policy_version_baseline(s)
            await s.commit()
        assert result is False

        async with _make_session()() as s:
            count = await s.execute(
                text("SELECT COUNT(*) FROM insurance_policy_versions WHERE is_active = TRUE")
            )
            assert count.scalar() == 1


# ── Tests: API hoạt động sau migration seed ────────────────────────────────────

class TestApiAfterSeed:

    def test_components_endpoint_returns_five(self, client):
        headers = _admin(client)
        resp = client.get(f"{BASE}/components", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 5

    def test_policy_versions_endpoint_has_active(self, client):
        headers = _admin(client)
        resp = client.get(f"{BASE}/policy-versions", headers=headers)
        assert resp.status_code == 200
        active = [p for p in resp.json() if p["is_active"]]
        assert len(active) == 1
        assert active[0]["code"] == _MIGRATION_POLICY_CODE

    def test_effective_config_from_policy_date_resolves_ok(self, client):
        """Từ ngày hiệu lực của policy trở đi → effective-config trả về 200."""
        headers = _admin(client)
        # Policy effective_from = 2026-01-01
        resp = client.get(f"{BASE}/effective-config", params={"as_of_date": "2026-01-01"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy_version"]["code"] == _MIGRATION_POLICY_CODE
        assert data["company_region"]["region"] == 3

    def test_effective_config_before_policy_date_returns_error(self, client):
        """Trước ngày hiệu lực 2026-01-01 → 422 (không có policy active cho ngày đó)."""
        headers = _admin(client)
        resp = client.get(f"{BASE}/effective-config", params={"as_of_date": "2025-12-31"}, headers=headers)
        assert resp.status_code == 422

    def test_active_policy_components_have_correct_total_rates(self, client):
        """Verify tổng tỷ lệ NLĐ và NSDLĐ qua API."""
        headers = _admin(client)
        resp = client.get(f"{BASE}/policy-versions", headers=headers)
        active = next(p for p in resp.json() if p["is_active"])
        components = active["components"]

        employee_total = sum(float(c["employee_rate_percent"]) for c in components)
        employer_total = sum(float(c["employer_rate_percent"]) for c in components)

        assert abs(employee_total - 10.5) < 0.001, f"NLĐ tổng: {employee_total}%"
        assert abs(employer_total - 21.5) < 0.001, f"NSDLĐ tổng: {employer_total}%"
