"""Tests cho 5.1 — Danh mục loại nghỉ phép (các trường quy tắc mới)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/leave-types"
LOOKUP = "/api/v1/lookups/leave-types"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_OFFICER_EMAIL  = "hrofficer@hrms.local"
_PREFIX         = "TEST_LT_"


def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup():
    async with _make_session()() as s:
        await s.execute(text(f"DELETE FROM leave_types WHERE code LIKE '{_PREFIX}%'"))
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await _cleanup()


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_leave_type_with_all_rule_fields(client: TestClient):
    """POST với đầy đủ 6 trường quy tắc → 201, read-back khớp."""
    headers = _login(client)
    payload = {
        "code": f"{_PREFIX}FULL01",
        "name": "Nghỉ kiểm thử đầy đủ",
        "is_paid_leave": True,
        "affects_annual_leave": False,
        "allow_half_day": True,
        "requires_attachment": False,
        "color_tag": "teal",
        "count_public_holidays": False,
        "max_days_per_year": 5,
        "max_consecutive_days": 3,
        "min_advance_days": 2,
        "carryover_allowed": True,
        "carryover_cutoff_month": 6,
    }
    resp = client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["count_public_holidays"] is False
    assert body["max_days_per_year"] == 5
    assert body["max_consecutive_days"] == 3
    assert body["min_advance_days"] == 2
    assert body["carryover_allowed"] is True
    assert body["carryover_cutoff_month"] == 6


def test_create_leave_type_defaults(client: TestClient):
    """POST chỉ có code + name → các trường quy tắc nhận giá trị mặc định."""
    headers = _login(client)
    resp = client.post(
        BASE,
        json={"code": f"{_PREFIX}DEF01", "name": "Nghỉ mặc định"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["count_public_holidays"] is True
    assert body["max_days_per_year"] is None
    assert body["max_consecutive_days"] is None
    assert body["min_advance_days"] == 0
    assert body["carryover_allowed"] is False
    assert body["carryover_cutoff_month"] == 3


def test_create_leave_type_count_public_holidays_false(client: TestClient):
    """`count_public_holidays=False` lưu và trả về đúng."""
    headers = _login(client)
    resp = client.post(
        BASE,
        json={"code": f"{_PREFIX}NOHOL", "name": "Không tính lễ", "count_public_holidays": False},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["count_public_holidays"] is False


# ── Validation ────────────────────────────────────────────────────────────────

def test_carryover_cutoff_month_zero_rejected(client: TestClient):
    """`carryover_cutoff_month=0` → 422."""
    headers = _login(client)
    resp = client.post(
        BASE,
        json={"code": f"{_PREFIX}BAD01", "name": "Tháng 0", "carryover_cutoff_month": 0},
        headers=headers,
    )
    assert resp.status_code == 422


def test_carryover_cutoff_month_13_rejected(client: TestClient):
    """`carryover_cutoff_month=13` → 422."""
    headers = _login(client)
    resp = client.post(
        BASE,
        json={"code": f"{_PREFIX}BAD02", "name": "Tháng 13", "carryover_cutoff_month": 13},
        headers=headers,
    )
    assert resp.status_code == 422


def test_carryover_cutoff_month_12_accepted(client: TestClient):
    """`carryover_cutoff_month=12` hợp lệ → 201."""
    headers = _login(client)
    resp = client.post(
        BASE,
        json={"code": f"{_PREFIX}M12", "name": "Tháng 12", "carryover_cutoff_month": 12},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["carryover_cutoff_month"] == 12


def test_max_days_per_year_zero_rejected(client: TestClient):
    """`max_days_per_year=0` → 422 (ge=1)."""
    headers = _login(client)
    resp = client.post(
        BASE,
        json={"code": f"{_PREFIX}BAD03", "name": "0 ngày", "max_days_per_year": 0},
        headers=headers,
    )
    assert resp.status_code == 422


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_leave_type_max_days_per_year(client: TestClient):
    """PUT max_days_per_year → cập nhật đúng."""
    headers = _login(client)
    created = client.post(
        BASE,
        json={"code": f"{_PREFIX}UPD01", "name": "Cập nhật ngày"},
        headers=headers,
    ).json()

    resp = client.put(f"{BASE}/{created['id']}", json={"max_days_per_year": 10}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["max_days_per_year"] == 10


def test_update_leave_type_carryover_toggle(client: TestClient):
    """Bật carryover + đặt tháng tùy chỉnh → lưu đúng."""
    headers = _login(client)
    created = client.post(
        BASE,
        json={"code": f"{_PREFIX}UPD02", "name": "Toggle carryover"},
        headers=headers,
    ).json()
    assert created["carryover_allowed"] is False

    resp = client.put(
        f"{BASE}/{created['id']}",
        json={"carryover_allowed": True, "carryover_cutoff_month": 6},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["carryover_allowed"] is True
    assert body["carryover_cutoff_month"] == 6


# ── Seed data ─────────────────────────────────────────────────────────────────

def test_seed_annual_leave_has_correct_rules(client: TestClient):
    """Seed annual_leave: count_public_holidays=False, carryover_allowed=True, cutoff=3."""
    headers = _login(client)
    resp = client.get(BASE, params={"keyword": "annual_leave"}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    row = next((i for i in items if i["code"] == "annual_leave"), None)
    assert row is not None, "annual_leave not found"
    assert row["count_public_holidays"] is False
    assert row["carryover_allowed"] is True
    assert row["carryover_cutoff_month"] == 3


def test_seed_paternity_leave_exists(client: TestClient):
    """Seed paternity_leave tồn tại, max_days_per_year=14."""
    headers = _login(client)
    resp = client.get(BASE, params={"keyword": "paternity_leave"}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    row = next((i for i in items if i["code"] == "paternity_leave"), None)
    assert row is not None, "paternity_leave not found"
    assert row["max_days_per_year"] == 14
    assert row["requires_attachment"] is True


def test_seed_child_care_leave_exists(client: TestClient):
    """Seed child_care_leave tồn tại, max_days_per_year=20."""
    headers = _login(client)
    resp = client.get(BASE, params={"keyword": "child_care_leave"}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    row = next((i for i in items if i["code"] == "child_care_leave"), None)
    assert row is not None, "child_care_leave not found"
    assert row["max_days_per_year"] == 20


def test_seed_bereavement_max_days(client: TestClient):
    """Seed bereavement_leave: max_days_per_year=3."""
    headers = _login(client)
    resp = client.get(BASE, params={"keyword": "bereavement_leave"}, headers=headers)
    items = resp.json()["items"]
    row = next((i for i in items if i["code"] == "bereavement_leave"), None)
    assert row is not None
    assert row["max_days_per_year"] == 3


# ── Lookup ────────────────────────────────────────────────────────────────────

def test_lookup_leave_types_returns_new_fields(client: TestClient):
    """GET /lookups/leave-types trả đầy đủ 6 trường quy tắc mới."""
    headers = _login(client)
    resp = client.get(LOOKUP, headers=headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) >= 1
    first = rows[0]
    for field in ("count_public_holidays", "max_days_per_year", "max_consecutive_days",
                  "min_advance_days", "carryover_allowed", "carryover_cutoff_month"):
        assert field in first, f"Missing field: {field}"


# ── RBAC ──────────────────────────────────────────────────────────────────────

def test_officer_cannot_delete_leave_type(client: TestClient):
    """Officer không có quyền xóa loại nghỉ phép → 403."""
    admin = _login(client)
    created = client.post(
        BASE,
        json={"code": f"{_PREFIX}NODELETE", "name": "Không phép xóa"},
        headers=admin,
    )
    assert created.status_code == 201, created.text
    row_id = created.json()["id"]

    officer = _login(client, _OFFICER_EMAIL)
    resp = client.delete(f"{BASE}/{row_id}", headers=officer)
    assert resp.status_code == 403


def test_unauthenticated_request_rejected(client: TestClient):
    """Không có token → 401."""
    resp = client.get(BASE)
    assert resp.status_code == 401
