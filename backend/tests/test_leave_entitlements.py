"""Tests cho 5.2 — Quản lý số ngày phép (LeaveEntitlement)."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE   = "/api/v1/leave-entitlements"
BULK   = f"{BASE}/bulk-allocate"
BASE_EMP = "/api/v1/employees"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_OFFICER_EMAIL  = "hrofficer@hrms.local"

# Dùng employee_id=1 và leave_type_id=1 (annual_leave) là seed data tồn tại sẵn
_EMP_ID  = 1
_LT_ID   = 1   # annual_leave
_TEST_YEAR = 2090  # Năm đủ xa để không đụng bulk-allocate thật
# Employee 2 có is_active=True — dùng cho bulk-allocate (service lọc is_active=True)
_BULK_EMP_ID = 2


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
        await s.execute(text(f"DELETE FROM leave_entitlements WHERE year >= {_TEST_YEAR}"))
        await s.execute(text(f"DELETE FROM leave_entitlements WHERE year = {_TEST_YEAR - 1}"))
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    await _cleanup()
    yield
    await _cleanup()


def _create(client, headers, *, year=_TEST_YEAR, employee_id=_EMP_ID,
            leave_type_id=_LT_ID, allocated_days=12.0,
            carryover_days=0.0, carryover_expires=None, note=None):
    body = {
        "employee_id": employee_id,
        "leave_type_id": leave_type_id,
        "year": year,
        "allocated_days": allocated_days,
        "carryover_days": carryover_days,
    }
    if carryover_expires:
        body["carryover_expires"] = str(carryover_expires)
    if note:
        body["note"] = note
    return client.post(BASE, json=body, headers=headers)


def _employee_display_code(client: TestClient, headers: dict, employee_id: int) -> str:
    resp = client.get(f"{BASE_EMP}/{employee_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["display_code"]


# ── Tạo thủ công ──────────────────────────────────────────────────────────────

def test_create_entitlement_manual(client: TestClient):
    """POST với đủ trường → 201, remaining_days = allocated - used."""
    headers = _login(client)
    r = _create(client, headers, allocated_days=12.0)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["allocated_days"] == 12.0
    assert body["used_days"] == 0.0
    assert body["remaining_days"] == 12.0
    assert body["employee_id"] == _EMP_ID
    assert body["leave_type_code"] == "annual_leave"


def test_create_entitlement_with_carryover(client: TestClient):
    """POST với carryover → 201, remaining phản ánh đúng."""
    headers = _login(client)
    r = _create(client, headers, allocated_days=12.0, carryover_days=4.0,
                carryover_expires=date(_TEST_YEAR, 3, 31))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["carryover_days"] == 4.0
    assert body["remaining_days"] == 16.0


def test_entitlement_employee_code_matches_employee_display_code(client: TestClient):
    headers = _login(client)
    expected_code = _employee_display_code(client, headers, _EMP_ID)

    created = _create(client, headers, allocated_days=12.0)
    assert created.status_code == 201, created.text
    assert created.json()["employee_code"] == expected_code

    listed = client.get(BASE, params={"year": _TEST_YEAR, "employee_id": _EMP_ID}, headers=headers)
    assert listed.status_code == 200, listed.text
    item = next(i for i in listed.json()["items"] if i["employee_id"] == _EMP_ID)
    assert item["employee_code"] == expected_code


def test_create_entitlement_duplicate_rejected(client: TestClient):
    """POST cùng (employee, leave_type, year) lần 2 → 409."""
    headers = _login(client)
    _create(client, headers)
    r2 = _create(client, headers)
    assert r2.status_code == 409


def test_create_entitlement_invalid_allocated_days(client: TestClient):
    """allocated_days âm → 422."""
    headers = _login(client)
    r = _create(client, headers, allocated_days=-1.0)
    assert r.status_code == 422


def test_create_carryover_without_expires_rejected(client: TestClient):
    """carryover_days > 0 nhưng không có carryover_expires → 422."""
    headers = _login(client)
    r = _create(client, headers, carryover_days=4.0)
    assert r.status_code == 422


# ── remaining_days FIFO ───────────────────────────────────────────────────────

def test_remaining_no_carryover(client: TestClient):
    """allocated=12, carryover=0, used=0 → remaining=12."""
    headers = _login(client)
    r = _create(client, headers, allocated_days=12.0)
    assert r.json()["remaining_days"] == 12.0


def test_remaining_active_carryover(client: TestClient):
    """carryover_expires trong tương lai → remaining = allocated + carryover."""
    headers = _login(client)
    future = date(_TEST_YEAR, 3, 31)
    r = _create(client, headers, allocated_days=12.0, carryover_days=4.0,
                carryover_expires=future)
    assert r.status_code == 201, r.text
    assert r.json()["remaining_days"] == 16.0


def test_remaining_expired_carryover_fifo(client: TestClient):
    """
    carryover_expires đã qua, used=5 (FIFO: 4 từ carryover + 1 từ regular)
    → remaining = 12 - max(0, 5-4) = 11
    """
    import asyncio
    headers = _login(client)
    past = date(2020, 3, 31)  # Đã qua
    r = _create(client, headers, allocated_days=12.0, carryover_days=4.0,
                carryover_expires=past)
    assert r.status_code == 201, r.text
    ent_id = r.json()["id"]

    # Giả lập used_days = 5 trực tiếp qua DB
    async def _set_used():
        async with _make_session()() as s:
            await s.execute(text(f"UPDATE leave_entitlements SET used_days=5 WHERE id={ent_id}"))
            await s.commit()

    asyncio.run(_set_used())

    r2 = client.get(f"{BASE}/{ent_id}", headers=headers)
    assert r2.json()["remaining_days"] == 11.0


def test_remaining_all_carryover_used_before_cutoff(client: TestClient):
    """used=4 ≥ carryover=4 → cutoff hết hạn: remaining = 12 - 0 = 12."""
    import asyncio
    headers = _login(client)
    past = date(2020, 3, 31)
    r = _create(client, headers, allocated_days=12.0, carryover_days=4.0,
                carryover_expires=past)
    ent_id = r.json()["id"]

    async def _set_used():
        async with _make_session()() as s:
            await s.execute(text(f"UPDATE leave_entitlements SET used_days=4 WHERE id={ent_id}"))
            await s.commit()
    asyncio.run(_set_used())

    r2 = client.get(f"{BASE}/{ent_id}", headers=headers)
    assert r2.json()["remaining_days"] == 12.0


# ── Update & Delete ────────────────────────────────────────────────────────────

def test_update_allocated_days(client: TestClient):
    """PUT allocated_days=15 → 200, remaining thay đổi đúng."""
    headers = _login(client)
    created = _create(client, headers).json()
    r = client.put(f"{BASE}/{created['id']}", json={"allocated_days": 15.0}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["allocated_days"] == 15.0
    assert r.json()["remaining_days"] == 15.0


def test_update_note(client: TestClient):
    """PUT note → 200."""
    headers = _login(client)
    created = _create(client, headers).json()
    r = client.put(f"{BASE}/{created['id']}", json={"note": "Điều chỉnh thâm niên"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["note"] == "Điều chỉnh thâm niên"


def test_delete_no_transactions(client: TestClient):
    """used_days=0 → DELETE → 204."""
    headers = _login(client)
    created = _create(client, headers).json()
    r = client.delete(f"{BASE}/{created['id']}", headers=headers)
    assert r.status_code == 204


def test_delete_with_transactions_rejected(client: TestClient):
    """used_days > 0 → DELETE → 409."""
    import asyncio
    headers = _login(client)
    created = _create(client, headers).json()
    ent_id = created["id"]

    async def _set_used():
        async with _make_session()() as s:
            await s.execute(text(f"UPDATE leave_entitlements SET used_days=3 WHERE id={ent_id}"))
            await s.commit()
    asyncio.run(_set_used())

    r = client.delete(f"{BASE}/{ent_id}", headers=headers)
    assert r.status_code == 409


# ── Bulk allocate ──────────────────────────────────────────────────────────────

def test_bulk_allocate_annual_leave(client: TestClient):
    """Bulk-allocate annual_leave → tất cả nhân viên active có entitlement."""
    headers = _login(client)
    r = client.post(BULK, json={"year": _TEST_YEAR, "leave_type_codes": ["annual_leave"]}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["year"] == _TEST_YEAR
    assert body["allocated"] >= 1
    assert body["skipped"] == 0

    # Verify entitlement tồn tại
    listed = client.get(BASE, params={"year": _TEST_YEAR}, headers=headers).json()
    assert listed["total"] >= 1
    item = listed["items"][0]
    assert item["allocated_days"] >= 12.0  # ≥ 12 (có thể có thâm niên)


def test_bulk_allocate_seniority_bonus(client: TestClient):
    """
    Nhân viên có start_date đủ 5 năm trước _TEST_YEAR
    → allocated_days = 13 (12 + 1 bonus).
    """
    import asyncio

    # Đặt start_date của _BULK_EMP_ID về 6 năm trước _TEST_YEAR
    target_start = date(_TEST_YEAR - 6, 1, 1)

    async def _get_start():
        async with _make_session()() as s:
            r = await s.execute(text(f"SELECT start_date FROM employees WHERE id={_BULK_EMP_ID}"))
            return r.scalar_one()

    async def _set_start(d):
        async with _make_session()() as s:
            await s.execute(text(f"UPDATE employees SET start_date='{d}' WHERE id={_BULK_EMP_ID}"))
            await s.commit()

    original_start = asyncio.run(_get_start())
    asyncio.run(_set_start(target_start))

    try:
        headers = _login(client)
        r = client.post(BULK, json={"year": _TEST_YEAR, "leave_type_codes": ["annual_leave"],
                                    "employee_ids": [_BULK_EMP_ID]}, headers=headers)
        assert r.status_code == 200, r.text

        listed = client.get(BASE, params={"year": _TEST_YEAR, "employee_id": _BULK_EMP_ID}, headers=headers).json()
        assert listed["total"] == 1
        assert listed["items"][0]["allocated_days"] == 13.0
    finally:
        asyncio.run(_set_start(original_start))


def test_bulk_allocate_with_carryover(client: TestClient):
    """
    Có entitlement năm trước (allocated=12, used=8) → carryover=4 cho năm mới.
    """
    import asyncio
    headers = _login(client)

    # Tạo entitlement năm _TEST_YEAR - 1 với 4 ngày dư (dùng _BULK_EMP_ID vì bulk lọc is_active)
    prev_year = _TEST_YEAR - 1
    r_prev = _create(client, headers, year=prev_year, allocated_days=12.0,
                     employee_id=_BULK_EMP_ID)
    assert r_prev.status_code == 201, r_prev.text
    prev_id = r_prev.json()["id"]

    async def _set_used():
        async with _make_session()() as s:
            await s.execute(text(f"UPDATE leave_entitlements SET used_days=8 WHERE id={prev_id}"))
            await s.commit()
    asyncio.run(_set_used())

    # Bulk-allocate năm mới
    r = client.post(BULK, json={"year": _TEST_YEAR, "leave_type_codes": ["annual_leave"],
                                "employee_ids": [_BULK_EMP_ID]}, headers=headers)
    assert r.status_code == 200, r.text

    listed = client.get(BASE, params={"year": _TEST_YEAR, "employee_id": _BULK_EMP_ID}, headers=headers).json()
    assert listed["total"] == 1
    item = listed["items"][0]
    assert item["carryover_days"] == 4.0
    assert item["carryover_expires"] is not None


def test_bulk_allocate_skip_if_has_transactions(client: TestClient):
    """Đã có entitlement với used_days>0 và overwrite=False → skipped."""
    import asyncio
    headers = _login(client)

    r = _create(client, headers, employee_id=_BULK_EMP_ID)
    ent_id = r.json()["id"]

    async def _set_used():
        async with _make_session()() as s:
            await s.execute(text(f"UPDATE leave_entitlements SET used_days=2 WHERE id={ent_id}"))
            await s.commit()
    asyncio.run(_set_used())

    r2 = client.post(BULK, json={"year": _TEST_YEAR, "leave_type_codes": ["annual_leave"],
                                 "employee_ids": [_BULK_EMP_ID], "overwrite": False}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["skipped"] >= 1


def test_bulk_allocate_overwrite_flag(client: TestClient):
    """overwrite=True → ghi đè dù đã có used_days > 0."""
    import asyncio
    headers = _login(client)

    r = _create(client, headers, employee_id=_BULK_EMP_ID, allocated_days=10.0)
    ent_id = r.json()["id"]

    async def _set_used():
        async with _make_session()() as s:
            await s.execute(text(f"UPDATE leave_entitlements SET used_days=2 WHERE id={ent_id}"))
            await s.commit()
    asyncio.run(_set_used())

    r2 = client.post(BULK, json={"year": _TEST_YEAR, "leave_type_codes": ["annual_leave"],
                                 "employee_ids": [_BULK_EMP_ID], "overwrite": True}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["allocated"] >= 1

    listed = client.get(BASE, params={"year": _TEST_YEAR, "employee_id": _BULK_EMP_ID}, headers=headers).json()
    assert listed["items"][0]["allocated_days"] >= 12.0  # đã được ghi đè


def test_bulk_allocate_unknown_leave_type(client: TestClient):
    """leave_type_codes chứa code không tồn tại → 400."""
    headers = _login(client)
    r = client.post(BULK, json={"year": _TEST_YEAR, "leave_type_codes": ["nonexistent_type"]}, headers=headers)
    assert r.status_code == 400


# ── Celery task ───────────────────────────────────────────────────────────────

def test_reset_expired_carryover_task(client: TestClient):
    """
    Entitlement có carryover_expires đã qua và carryover_days > used_days
    → task zeroes out carryover_days.
    """
    import asyncio
    headers = _login(client)

    past = date(2020, 3, 31)
    r = _create(client, headers, allocated_days=12.0, carryover_days=4.0,
                carryover_expires=past)
    assert r.status_code == 201, r.text
    ent_id = r.json()["id"]

    # Chạy task trực tiếp
    from app.workers.tasks import reset_expired_carryover
    result = reset_expired_carryover()
    assert result["reset_rows"] >= 1

    # Verify DB đã zeroed out
    async def _check():
        async with _make_session()() as s:
            row = await s.execute(text(f"SELECT carryover_days FROM leave_entitlements WHERE id={ent_id}"))
            return float(row.scalar_one())
    carry_after = asyncio.run(_check())
    assert carry_after == 0.0


def test_reset_carryover_skips_fully_used(client: TestClient):
    """
    carryover_days <= used_days → task không reset (điều kiện carryover_days > used_days).
    """
    import asyncio
    headers = _login(client)

    past = date(2020, 3, 31)
    r = _create(client, headers, allocated_days=12.0, carryover_days=4.0,
                carryover_expires=past)
    ent_id = r.json()["id"]

    # Set used_days = 4 (≥ carryover_days=4)
    async def _set_used():
        async with _make_session()() as s:
            await s.execute(text(f"UPDATE leave_entitlements SET used_days=4 WHERE id={ent_id}"))
            await s.commit()
    asyncio.run(_set_used())

    from app.workers.tasks import reset_expired_carryover
    reset_expired_carryover()
    # Bản ghi này KHÔNG được reset (carryover_days không > used_days)
    async def _check():
        async with _make_session()() as s:
            row = await s.execute(text(f"SELECT carryover_days FROM leave_entitlements WHERE id={ent_id}"))
            return float(row.scalar_one())
    carry_after = asyncio.run(_check())
    assert carry_after == 4.0  # Không bị zeroed out


# ── RBAC ──────────────────────────────────────────────────────────────────────

def test_unauthenticated_rejected(client: TestClient):
    """Không có token → 401."""
    r = client.get(BASE)
    assert r.status_code == 401


def test_officer_can_list(client: TestClient):
    """Officer có leaves:view → GET → 200."""
    officer = _login(client, _OFFICER_EMAIL)
    r = client.get(BASE, headers=officer)
    assert r.status_code == 200


def test_officer_cannot_delete(client: TestClient):
    """Officer không có leaves:delete → DELETE → 403."""
    admin = _login(client)
    created = _create(client, admin).json()
    officer = _login(client, _OFFICER_EMAIL)
    r = client.delete(f"{BASE}/{created['id']}", headers=officer)
    assert r.status_code == 403
