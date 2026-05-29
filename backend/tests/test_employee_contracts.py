"""Tests cho quản lý hợp đồng lao động nhân viên (4.1)."""

import asyncio
import io
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.employee import Employee

BASE_EMP = "/api/v1/employees"
BASE_CON = "/api/v1/contracts"

_ADMIN_EMAIL      = "admin@hrms.local"
_ADMIN_PASSWORD   = "Hrms@2026"
_HR_MANAGER_EMAIL = "hrmanager@hrms.local"   # có contracts:view nhưng không phải admin

# ID từ seed data (labor_indefinite)
CAT_LABOR_INDEFINITE = 1
CAT_LABOR_DEFINITE   = 2
CAT_APPENDIX_SALARY  = 3

_PREFIX = "TESTCON"


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict:
    token = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient) -> dict:   return _login(client)
def _viewer(client: TestClient) -> dict:  return _login(client, _HR_MANAGER_EMAIL)


# ── Cleanup ────────────────────────────────────────────────────────────────────

def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup():
    async with _make_session()() as s:
        employee_ids = [e.id for e in (await s.execute(select(Employee))).scalars().all() if e.id_number.startswith(_PREFIX)]
        await s.execute(text(
            f"DELETE FROM employee_contracts WHERE contract_number LIKE '{_PREFIX}%'"
        ))
        if employee_ids:
            await s.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await _cleanup()


# ── Setup: tạo 1 nhân viên mẫu ────────────────────────────────────────────────

def _create_employee(client: TestClient, headers: dict, suffix: str = "001") -> int:
    resp = client.post(BASE_EMP, json={
        "employee_code_sequence_id": 1,
        "full_name": f"Test Contract {suffix}",
        "last_name": "Test",
        "first_name": f"Contract {suffix}",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": 1,
        "id_number": f"{_PREFIX}{suffix}",
        "id_issued_on": "2020-01-01",
        "id_issued_by": "Cục CA",
        "status": "official",
        "start_date": "2020-01-01",
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _contract_payload(suffix: str, category_id: int = CAT_LABOR_INDEFINITE, **kwargs) -> dict:
    today = date.today().isoformat()
    base = {
        "contract_category_id": category_id,
        "contract_number": f"{_PREFIX}-HĐ-{suffix}",
        "signed_date": today,
        "effective_from": today,
        "effective_to": None,
        "insurance_salary": "10000000",
    }
    base.update(kwargs)
    return base


# ── Tests: CRUD ────────────────────────────────────────────────────────────────

def test_create_contract_success(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C01")

    resp = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C01"), headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["contract_number"] == f"{_PREFIX}-HĐ-C01"
    assert data["status"] == "active"
    assert data["document_kind"] == "labor_contract"
    assert data["has_file"] is False
    assert data["appendices"] == []


def test_create_contract_definite_term(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C02")
    today   = date.today()
    end     = (today + timedelta(days=365)).isoformat()

    resp = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload(
        "C02", category_id=CAT_LABOR_DEFINITE,
        effective_to=end,
    ), headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["effective_to"] == end
    assert data["days_until_expiry"] is not None
    assert data["days_until_expiry"] > 0


def test_create_contract_duplicate_number_409(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C03")

    client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C03"), headers=headers)
    resp = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C03"), headers=headers)
    assert resp.status_code == 409


def test_create_appendix_linked_to_parent(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C04")

    parent = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C04"), headers=headers).json()
    parent_id = parent["id"]

    appendix_payload = _contract_payload(
        "C04-PL1",
        category_id=CAT_APPENDIX_SALARY,
        parent_contract_id=parent_id,
        insurance_salary="12000000",
    )
    resp = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=appendix_payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["parent_contract_id"] == parent_id
    assert data["document_kind"] == "contract_appendix"


def test_create_appendix_wrong_employee_400(client: TestClient):
    headers  = _admin(client)
    emp_id1  = _create_employee(client, headers, "C05a")
    emp_id2  = _create_employee(client, headers, "C05b")

    parent = client.post(f"{BASE_EMP}/{emp_id1}/contracts", json=_contract_payload("C05"), headers=headers).json()

    appendix_payload = _contract_payload(
        "C05-PL1",
        category_id=CAT_APPENDIX_SALARY,
        parent_contract_id=parent["id"],
    )
    # Dùng emp_id2 nhưng trỏ parent thuộc emp_id1 → 400
    resp = client.post(f"{BASE_EMP}/{emp_id2}/contracts", json=appendix_payload, headers=headers)
    assert resp.status_code == 400


def test_get_contract_detail_with_appendices(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C06")

    parent = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C06"), headers=headers).json()
    client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload(
        "C06-PL1", category_id=CAT_APPENDIX_SALARY, parent_contract_id=parent["id"]
    ), headers=headers)

    resp = client.get(f"{BASE_EMP}/{emp_id}/contracts/{parent['id']}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["appendices"]) == 1


def test_list_contracts_includes_all(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C07")

    client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C07a"), headers=headers)
    client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C07b",
        category_id=CAT_LABOR_DEFINITE,
        effective_to=(date.today() + timedelta(days=180)).isoformat(),
    ), headers=headers)

    resp = client.get(f"{BASE_EMP}/{emp_id}/contracts", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_contract_success(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C08")
    cid     = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C08"), headers=headers).json()["id"]

    resp = client.put(f"{BASE_EMP}/{emp_id}/contracts/{cid}",
        json={"insurance_salary": "15000000", "notes": "Tăng lương"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert Decimal(resp.json()["insurance_salary"]) == Decimal("15000000")


def test_update_terminated_contract_400(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C09")
    cid     = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C09"), headers=headers).json()["id"]

    client.delete(f"{BASE_EMP}/{emp_id}/contracts/{cid}", headers=headers)
    resp = client.put(f"{BASE_EMP}/{emp_id}/contracts/{cid}", json={"notes": "Edit"}, headers=headers)
    assert resp.status_code == 400


def test_terminate_contract_success(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C10")
    cid     = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C10"), headers=headers).json()["id"]

    resp = client.delete(f"{BASE_EMP}/{emp_id}/contracts/{cid}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "terminated"
    assert resp.json()["status_display"] == "Đã hủy"


def test_terminate_already_terminated_400(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C11")
    cid     = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C11"), headers=headers).json()["id"]

    client.delete(f"{BASE_EMP}/{emp_id}/contracts/{cid}", headers=headers)
    resp = client.delete(f"{BASE_EMP}/{emp_id}/contracts/{cid}", headers=headers)
    assert resp.status_code == 400


def test_contract_not_found_404(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C12")
    resp    = client.get(f"{BASE_EMP}/{emp_id}/contracts/99999999", headers=headers)
    assert resp.status_code == 404


def test_contract_invalid_dates_422(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C13")
    payload = _contract_payload("C13", category_id=CAT_LABOR_DEFINITE,
        effective_from="2026-12-31", effective_to="2026-01-01")  # ngày kết thúc < ngày bắt đầu

    resp = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=payload, headers=headers)
    assert resp.status_code == 422


# ── Tests: File upload ─────────────────────────────────────────────────────────

def test_upload_contract_file_success(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C14")
    cid     = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C14"), headers=headers).json()["id"]

    fake_pdf = b"%PDF-1.4 fake content"
    resp = client.post(
        f"{BASE_EMP}/{emp_id}/contracts/{cid}/upload",
        files={"file": ("hop_dong.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_file"] is True
    assert data["file_name"] == "hop_dong.pdf"


def test_upload_contract_file_invalid_type_400(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C15")
    cid     = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C15"), headers=headers).json()["id"]

    resp = client.post(
        f"{BASE_EMP}/{emp_id}/contracts/{cid}/upload",
        files={"file": ("data.csv", io.BytesIO(b"a,b,c"), "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_download_contract_file_no_file_404(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C16")
    cid     = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C16"), headers=headers).json()["id"]

    resp = client.get(f"{BASE_EMP}/{emp_id}/contracts/{cid}/download", headers=headers)
    assert resp.status_code == 404


# ── Tests: Permissions ─────────────────────────────────────────────────────────

def test_viewer_can_read_contracts(client: TestClient):
    headers_admin  = _admin(client)
    headers_viewer = _viewer(client)
    emp_id = _create_employee(client, headers_admin, "C17")
    client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C17"), headers=headers_admin)

    resp = client.get(f"{BASE_EMP}/{emp_id}/contracts", headers=headers_viewer)
    assert resp.status_code == 200


def test_viewer_cannot_create_403(client: TestClient):
    headers_admin  = _admin(client)
    headers_no_perm = _login(client, "linemanager@hrms.local")
    emp_id = _create_employee(client, headers_admin, "C18")

    resp = client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C18"), headers=headers_no_perm)
    assert resp.status_code == 403


def test_unauth_401(client: TestClient):
    resp = client.get(f"{BASE_EMP}/1/contracts")
    assert resp.status_code == 401


# ── Tests: Global list ─────────────────────────────────────────────────────────

def test_global_list_200(client: TestClient):
    headers = _admin(client)
    resp = client.get(BASE_CON, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


def test_global_list_filter_document_kind(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C19")
    client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload("C19"), headers=headers)

    resp_all       = client.get(BASE_CON, headers=headers)
    resp_labor     = client.get(BASE_CON, params={"document_kind": "labor_contract"}, headers=headers)
    resp_appendix  = client.get(BASE_CON, params={"document_kind": "contract_appendix"}, headers=headers)

    assert resp_labor.json()["total"] >= 1
    # Tất cả item trong labor list phải là labor_contract
    for item in resp_labor.json()["items"]:
        assert item["document_kind"] == "labor_contract"
    for item in resp_appendix.json()["items"]:
        assert item["document_kind"] == "contract_appendix"


def test_global_list_filter_expiring_within(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C20")
    # Tạo HĐ hết hạn trong 10 ngày
    near_expiry = (date.today() + timedelta(days=10)).isoformat()
    client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload(
        "C20", category_id=CAT_LABOR_DEFINITE, effective_to=near_expiry
    ), headers=headers)

    resp_30 = client.get(BASE_CON, params={"expiring_within": 30}, headers=headers)
    resp_5  = client.get(BASE_CON, params={"expiring_within": 5}, headers=headers)

    assert resp_30.json()["total"] >= 1
    # HĐ hết hạn trong 10 ngày → không xuất hiện trong filter 5 ngày
    assert resp_30.json()["total"] > resp_5.json()["total"]


def test_global_list_viewer_200(client: TestClient):
    assert client.get(BASE_CON, headers=_viewer(client)).status_code == 200


def test_global_list_unauth_401(client: TestClient):
    assert client.get(BASE_CON).status_code == 401


# ── Tests: Reminder contract_expiry ───────────────────────────────────────────

def test_reminder_contract_expiry_included(client: TestClient):
    headers = _admin(client)
    emp_id  = _create_employee(client, headers, "C21")

    near = (date.today() + timedelta(days=15)).isoformat()
    client.post(f"{BASE_EMP}/{emp_id}/contracts", json=_contract_payload(
        "C21", category_id=CAT_LABOR_DEFINITE, effective_to=near
    ), headers=headers)

    resp = client.get("/api/v1/reminders", params={"days": 30, "types": "contract_expiry"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "contract_expiry" in data
    # Phải có ít nhất HĐ vừa tạo
    contract_numbers = [e.get("extra", {}).get("contract_number") for e in data["contract_expiry"]]
    assert f"{_PREFIX}-HĐ-C21" in contract_numbers


def test_reminder_default_includes_contract_expiry(client: TestClient):
    headers = _admin(client)
    resp = client.get("/api/v1/reminders", headers=headers)
    assert resp.status_code == 200
    assert "contract_expiry" in resp.json()
