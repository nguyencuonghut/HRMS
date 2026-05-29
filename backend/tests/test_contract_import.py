"""Tests cho 12.1 Slice 1 — Import hợp đồng hàng loạt."""
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

# Dữ liệu seed: employee_seq=1 (Nguyễn Văn An), seq=2 (Trần Thị Bình)
_EMP_SEQ_1 = "1"
_EMP_SEQ_2 = "2"

# Contract category codes từ seed
_CAT_INDEFINITE = "labor_indefinite"    # document_kind = labor_contract
_CAT_DEFINITE   = "labor_definite"      # document_kind = labor_contract
_CAT_APPENDIX   = "appendix_salary_change"  # document_kind = contract_appendix

_PREFIX = "TESTIMP"   # prefix số HĐ test → dễ cleanup


def _login(client: TestClient) -> dict:
    token = client.post(BASE_AUTH, json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup():
    async with _make_session()() as s:
        await s.execute(text(f"DELETE FROM employee_contracts WHERE contract_number LIKE '{_PREFIX}%'"))
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    await _cleanup()
    yield
    await _cleanup()


HEADERS = [
    "Mã nhân viên", "Số hợp đồng", "Loại văn bản",
    "Mã loại hợp đồng", "Ngày ký", "Ngày hiệu lực",
    "Ngày hết hạn", "Mức lương BHXH",
]


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
        f"{BASE}/contracts",
        files={"file": ("import.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )


# ── Template ──────────────────────────────────────────────────────────────────

def test_template_download(client: TestClient):
    h = _login(client)
    r = client.get(f"{BASE}/contracts/template", headers=h)
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers.get("content-type", "")
    assert "mau_import_hop_dong" in r.headers.get("content-disposition", "")
    # Verify xlsx is readable và có sheet Hướng dẫn
    wb = openpyxl.load_workbook(BytesIO(r.content))
    assert "Hướng dẫn" in wb.sheetnames


# ── Import success ────────────────────────────────────────────────────────────

def test_import_success(client: TestClient):
    h = _login(client)
    rows = [
        [_EMP_SEQ_1, f"{_PREFIX}-001", "labor_contract", _CAT_INDEFINITE, "01/01/2026", "01/01/2026", "", "5000000"],
        [_EMP_SEQ_2, f"{_PREFIX}-002", "labor_contract", _CAT_DEFINITE,   "01/01/2026", "01/01/2026", "31/12/2026", "4500000"],
    ]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert body["success"] == 2
    assert body["failed"] == 0
    assert body["errors"] == []


def test_import_no_expiry_is_valid(client: TestClient):
    """Ngày hết hạn bỏ trống = vô thời hạn → hợp lệ."""
    h = _login(client)
    rows = [[_EMP_SEQ_1, f"{_PREFIX}-003", "labor_contract", _CAT_INDEFINITE, "01/01/2026", "01/01/2026", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    assert r.json()["success"] == 1


# ── Validation errors ─────────────────────────────────────────────────────────

def test_import_invalid_employee(client: TestClient):
    h = _login(client)
    rows = [["999999", f"{_PREFIX}-004", "labor_contract", _CAT_INDEFINITE, "01/01/2026", "01/01/2026", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("Không tìm thấy nhân viên" in e["message"] for e in body["errors"])


def test_import_invalid_document_kind(client: TestClient):
    h = _login(client)
    rows = [[_EMP_SEQ_1, f"{_PREFIX}-005", "invalid_kind", _CAT_INDEFINITE, "01/01/2026", "01/01/2026", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("labor_contract" in e["message"] for e in body["errors"])


def test_import_invalid_category_code(client: TestClient):
    h = _login(client)
    rows = [[_EMP_SEQ_1, f"{_PREFIX}-006", "labor_contract", "nonexistent_cat", "01/01/2026", "01/01/2026", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("loại hợp đồng" in e["message"].lower() for e in body["errors"])


def test_import_date_order_error(client: TestClient):
    """effective_to < effective_from → lỗi."""
    h = _login(client)
    rows = [[_EMP_SEQ_1, f"{_PREFIX}-007", "labor_contract", _CAT_INDEFINITE, "01/01/2026", "01/06/2026", "01/01/2026", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("hết hạn" in e["message"].lower() for e in body["errors"])


def test_import_duplicate_contract_number(client: TestClient):
    h = _login(client)
    rows_first = [[_EMP_SEQ_1, f"{_PREFIX}-008", "labor_contract", _CAT_INDEFINITE, "01/01/2026", "01/01/2026", "", ""]]
    _upload(client, h, _make_xlsx(rows_first))  # lần 1 thành công

    rows_dup = [[_EMP_SEQ_2, f"{_PREFIX}-008", "labor_contract", _CAT_DEFINITE, "01/02/2026", "01/02/2026", "", ""]]
    r = _upload(client, h, _make_xlsx(rows_dup))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("đã tồn tại" in e["message"] for e in body["errors"])


def test_import_missing_required_field(client: TestClient):
    h = _login(client)
    # Bỏ trống "Số hợp đồng"
    rows = [[_EMP_SEQ_1, "", "labor_contract", _CAT_INDEFINITE, "01/01/2026", "01/01/2026", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    assert r.json()["failed"] == 1


def test_import_document_kind_mismatch_category(client: TestClient):
    """document_kind='labor_contract' nhưng category là appendix → lỗi mismatch."""
    h = _login(client)
    rows = [[_EMP_SEQ_1, f"{_PREFIX}-009", "labor_contract", _CAT_APPENDIX, "01/01/2026", "01/01/2026", "", ""]]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == 1
    assert any("không khớp" in e["message"] for e in body["errors"])


def test_import_partial_errors(client: TestClient):
    """Dòng valid và invalid xen kẽ — dòng valid vẫn được tạo."""
    h = _login(client)
    rows = [
        [_EMP_SEQ_1, f"{_PREFIX}-010", "labor_contract", _CAT_INDEFINITE, "01/01/2026", "01/01/2026", "", ""],  # OK
        ["999", f"{_PREFIX}-011", "labor_contract", _CAT_INDEFINITE, "01/01/2026", "01/01/2026", "", ""],       # NV không tồn tại
    ]
    r = _upload(client, h, _make_xlsx(rows))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["success"] == 1
    assert body["failed"] == 1


# ── Permission ────────────────────────────────────────────────────────────────

def test_import_unauthenticated(client: TestClient):
    r = client.post(f"{BASE}/contracts",
                    files={"file": ("f.xlsx", b"x", "application/vnd.ms-excel")})
    assert r.status_code == 401


def test_template_unauthenticated(client: TestClient):
    r = client.get(f"{BASE}/contracts/template")
    assert r.status_code == 401


# ── File validation ───────────────────────────────────────────────────────────

def test_import_rejects_non_xlsx(client: TestClient):
    h = _login(client)
    r = client.post(f"{BASE}/contracts",
                    files={"file": ("data.csv", b"a,b,c", "text/csv")},
                    headers=h)
    assert r.status_code == 400
    assert "xlsx" in r.json()["detail"].lower()


def test_import_empty_file_rows(client: TestClient):
    """File chỉ có header, không có data → success=0."""
    h = _login(client)
    r = _upload(client, h, _make_xlsx([]))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["success"] == 0
