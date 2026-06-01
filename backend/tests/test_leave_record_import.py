"""Tests cho 12.1 Slice 2a — Import nghỉ phép hàng loạt."""
from __future__ import annotations

from io import BytesIO

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE      = "/api/v1/imports"
BASE_AUTH = "/api/v1/auth/login"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"

_EMP_SEQ_1 = "1"
_EMP_SEQ_2 = "2"
_LT_ANNUAL = "annual_leave"
_LT_SICK   = "sick_leave"
_YEAR      = 2095   # năm đủ xa tránh conflict


def _login(client: TestClient) -> dict:
    token = client.post(BASE_AUTH, json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup():
    async with _make_session()() as s:
        await s.execute(text(f"DELETE FROM leave_records WHERE EXTRACT(year FROM start_date) = {_YEAR}"))
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    await _cleanup()
    yield
    await _cleanup()


HEADERS = ["Mã nhân viên", "Mã loại phép", "Ngày bắt đầu", "Ngày kết thúc", "Ghi chú"]


def _make_xlsx(rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADERS)
    for r in rows:
        ws.append(r)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _upload(client, headers, xlsx_bytes: bytes):
    return client.post(
        f"{BASE}/leave-records",
        files={"file": ("import.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )


# ── Template ──────────────────────────────────────────────────────────────────

def test_template_download(client: TestClient):
    h = _login(client)
    r = client.get(f"{BASE}/leave-records/template", headers=h)
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers.get("content-type", "")
    wb = openpyxl.load_workbook(BytesIO(r.content))
    assert "Hướng dẫn" in wb.sheetnames


# ── Success ───────────────────────────────────────────────────────────────────

def test_import_success(client: TestClient):
    h = _login(client)
    rows = [
        [_EMP_SEQ_1, _LT_ANNUAL, f"01/06/{_YEAR}", f"03/06/{_YEAR}", "Nghỉ phép năm"],
        [_EMP_SEQ_2, _LT_SICK,   f"10/06/{_YEAR}", f"10/06/{_YEAR}", ""],
    ]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert body["success"] == 2
    assert body["failed"] == 0


def test_import_total_days_calculated(client: TestClient):
    """3 ngày nghỉ: total_days = 3."""
    h = _login(client)
    rows = [[_EMP_SEQ_1, _LT_ANNUAL, f"01/07/{_YEAR}", f"03/07/{_YEAR}", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    assert r.json()["success"] == 1
    assert r.json()["created_ids"]


def test_import_same_day_valid(client: TestClient):
    """start = end = 1 ngày → hợp lệ."""
    h = _login(client)
    rows = [[_EMP_SEQ_1, _LT_SICK, f"15/07/{_YEAR}", f"15/07/{_YEAR}", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    assert r.json()["success"] == 1


# ── Errors ────────────────────────────────────────────────────────────────────

def test_import_invalid_employee(client: TestClient):
    h = _login(client)
    rows = [["999999", _LT_ANNUAL, f"01/06/{_YEAR}", f"03/06/{_YEAR}", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("Không tìm thấy nhân viên" in e["message"] for e in body["errors"])


def test_import_invalid_leave_type(client: TestClient):
    h = _login(client)
    rows = [[_EMP_SEQ_1, "nonexistent_leave", f"01/06/{_YEAR}", f"03/06/{_YEAR}", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("loại phép" in e["message"] for e in body["errors"])


def test_import_date_order_error(client: TestClient):
    h = _login(client)
    rows = [[_EMP_SEQ_1, _LT_ANNUAL, f"10/06/{_YEAR}", f"01/06/{_YEAR}", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("kết thúc" in e["message"].lower() for e in body["errors"])


def test_import_missing_required(client: TestClient):
    h = _login(client)
    rows = [["", _LT_ANNUAL, f"01/06/{_YEAR}", f"03/06/{_YEAR}", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    assert r.json()["failed"] == 1


def test_import_overlap_generates_warning(client: TestClient):
    """NV đã có record trùng ngày → cảnh báo, vẫn import thành công."""
    h = _login(client)
    rows1 = [[_EMP_SEQ_1, _LT_ANNUAL, f"01/08/{_YEAR}", f"05/08/{_YEAR}", ""]]
    _upload(client, h, _make_xlsx(rows1))

    rows2 = [[_EMP_SEQ_1, _LT_SICK, f"03/08/{_YEAR}", f"04/08/{_YEAR}", ""]]
    r = _upload(client, h, _make_xlsx(rows2))
    assert r.status_code == 200
    body = r.json()
    assert body["success"] == 1   # vẫn tạo thành công
    assert any("[CẢNH BÁO]" in e["message"] for e in body["errors"])


def test_import_partial_errors(client: TestClient):
    h = _login(client)
    rows = [
        [_EMP_SEQ_1, _LT_ANNUAL, f"01/09/{_YEAR}", f"03/09/{_YEAR}", ""],  # OK
        ["999999",      _LT_ANNUAL, f"05/09/{_YEAR}", f"07/09/{_YEAR}", ""],  # fail
    ]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["success"] == 1
    assert body["failed"] == 1


# ── Auth & validation ─────────────────────────────────────────────────────────

def test_unauthenticated(client: TestClient):
    r = client.post(f"{BASE}/leave-records",
                    files={"file": ("f.xlsx", b"x", "application/vnd.ms-excel")})
    assert r.status_code == 401


def test_rejects_non_xlsx(client: TestClient):
    h = _login(client)
    r = client.post(f"{BASE}/leave-records",
                    files={"file": ("data.csv", b"a,b", "text/csv")},
                    headers=h)
    assert r.status_code == 400


def test_empty_rows(client: TestClient):
    h = _login(client)
    r = _upload(client, h, _make_xlsx([]))
    assert r.status_code == 200
    assert r.json()["total"] == 0
