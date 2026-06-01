"""Tests cho 12.1 Slice 2b — Import bảo hiểm hàng loạt."""
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
_EMP_SEQ_3 = "3"
_BHYT_CODE = "01001"   # code từ seed bhyt_clinics


def _login(client: TestClient) -> dict:
    token = client.post(BASE_AUTH, json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup():
    async with _make_session()() as s:
        # Xoá insurance profile của emp 1, 2, 3 (nếu có) sau test
        # Dùng bhxh_code test để tránh xóa nhầm dữ liệu thật
        await s.execute(text("DELETE FROM employee_insurance_profiles WHERE bhxh_code LIKE 'TESTIMP_%'"))
        # Reset về null profile nếu cần
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    await _cleanup()
    yield
    await _cleanup()


HEADERS = ["Mã nhân viên", "Mã BHXH", "Ngày tham gia", "Mức lương đóng", "Mã bệnh viện KCB", "Trạng thái"]


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
        f"{BASE}/insurance",
        files={"file": ("import.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )


# ── Template ──────────────────────────────────────────────────────────────────

def test_template_download(client: TestClient):
    h = _login(client)
    r = client.get(f"{BASE}/insurance/template", headers=h)
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers.get("content-type", "")
    wb = openpyxl.load_workbook(BytesIO(r.content))
    assert "Hướng dẫn" in wb.sheetnames


# ── Success ───────────────────────────────────────────────────────────────────

def test_import_success_create(client: TestClient):
    h = _login(client)
    rows = [[_EMP_SEQ_1, "TESTIMP_001", "01/01/2026", "5000000", _BHYT_CODE, "active"]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    assert body["success"] == 1
    assert body["failed"] == 0


def test_import_without_optional_fields(client: TestClient):
    """Không điền mã BHXH, bệnh viện, trạng thái → vẫn hợp lệ."""
    h = _login(client)
    rows = [[_EMP_SEQ_2, "", "01/02/2026", "4500000", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    assert r.json()["success"] == 1


def test_import_upsert_existing_profile(client: TestClient):
    """NV đã có hồ sơ BHXH → update (không báo lỗi, không tạo trùng)."""
    h = _login(client)
    # Tạo lần 1
    rows1 = [[_EMP_SEQ_3, "TESTIMP_003", "01/01/2026", "5000000", "", "active"]]
    r1 = _upload(client, h, _make_xlsx(rows1))
    assert r1.json()["success"] == 1

    # Update lần 2 cùng employee → upsert thành công
    rows2 = [[_EMP_SEQ_3, "TESTIMP_003b", "01/02/2026", "6000000", _BHYT_CODE, "active"]]
    r2 = _upload(client, h, _make_xlsx(rows2))
    assert r2.status_code == 200
    body = r2.json()
    assert body["success"] == 1   # không fail
    assert body["failed"] == 0


# ── Errors ────────────────────────────────────────────────────────────────────

def test_import_invalid_employee(client: TestClient):
    h = _login(client)
    rows = [["999999", "TESTIMP_X", "01/01/2026", "5000000", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("Không tìm thấy nhân viên" in e["message"] for e in body["errors"])


def test_import_invalid_salary_zero(client: TestClient):
    h = _login(client)
    rows = [[_EMP_SEQ_1, "TESTIMP_Z", "01/01/2026", "0", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("lương" in e["message"].lower() for e in body["errors"])


def test_import_invalid_salary_text(client: TestClient):
    h = _login(client)
    rows = [[_EMP_SEQ_1, "TESTIMP_T", "01/01/2026", "abc", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    assert r.json()["failed"] == 1


def test_import_invalid_clinic_code(client: TestClient):
    h = _login(client)
    rows = [[_EMP_SEQ_1, "TESTIMP_C", "01/01/2026", "5000000", "INVALID_CODE", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("bệnh viện" in e["message"].lower() for e in body["errors"])


def test_import_invalid_status(client: TestClient):
    h = _login(client)
    rows = [[_EMP_SEQ_1, "TESTIMP_S", "01/01/2026", "5000000", "", "unknown_status"]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    assert r.json()["failed"] == 1


def test_import_missing_required_salary(client: TestClient):
    h = _login(client)
    rows = [[_EMP_SEQ_1, "TESTIMP_M", "01/01/2026", "", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    assert r.json()["failed"] == 1


def test_import_invalid_date(client: TestClient):
    h = _login(client)
    rows = [[_EMP_SEQ_1, "TESTIMP_D", "not-a-date", "5000000", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    assert r.json()["failed"] == 1


def test_import_partial_errors(client: TestClient):
    h = _login(client)
    rows = [
        [_EMP_SEQ_1, "TESTIMP_OK", "01/03/2026", "5000000", "", ""],   # OK
        ["999999",      "TESTIMP_BAD", "01/03/2026", "5000000", "", ""],  # fail
    ]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["success"] == 1
    assert body["failed"] == 1


# ── Auth & validation ─────────────────────────────────────────────────────────

def test_unauthenticated(client: TestClient):
    r = client.post(f"{BASE}/insurance",
                    files={"file": ("f.xlsx", b"x", "application/vnd.ms-excel")})
    assert r.status_code == 401


def test_rejects_non_xlsx(client: TestClient):
    h = _login(client)
    r = client.post(f"{BASE}/insurance",
                    files={"file": ("data.csv", b"a,b", "text/csv")},
                    headers=h)
    assert r.status_code == 400


def test_empty_rows(client: TestClient):
    h = _login(client)
    r = _upload(client, h, _make_xlsx([]))
    assert r.status_code == 200
    assert r.json()["total"] == 0
