"""Tests cho module nhân viên (3.1)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds import employees as employees_seed
from app.seeds import other_business_catalog

BASE = "/api/v1/employees"
AUDIT_BASE = "/api/v1/audit-logs"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_OFFICER_EMAIL = "hrofficer@hrms.local"
_LINE_MANAGER_EMAIL = "linemanager@hrms.local"


def _login(client: TestClient, email: str = _ADMIN_EMAIL, password: str = _ADMIN_PASSWORD) -> dict:
    token = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient) -> dict:
    return _login(client)


def _officer(client: TestClient) -> dict:
    return _login(client, _OFFICER_EMAIL)


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup_test_employees():
    async with _make_session()() as s:
        await s.execute(text(
            "DELETE FROM employee_bank_accounts WHERE employee_id IN "
            "(SELECT id FROM employees WHERE id_number LIKE 'TEST%')"
        ))
        await s.execute(text("DELETE FROM employees WHERE id_number LIKE 'TEST%'"))
        await s.commit()


@pytest.fixture(scope="session", autouse=True)
async def seed_employee_data():
    async with _make_session()() as session:
        await other_business_catalog.seed_required_other_business_catalog(session)
        await employees_seed.seed_sample_employees(session)
        await session.commit()
    yield


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await _cleanup_test_employees()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _valid_payload(id_number: str = "TEST001234567890") -> dict:
    return {
        "full_name": "Nguyễn Test Viên",
        "last_name": "Nguyễn",
        "first_name": "Test Viên",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": 1,
        "id_number": id_number,
        "id_issued_on": "2020-01-01",
        "id_issued_by": "Cục Cảnh sát ĐKQLCƯ",
        "status": "probation",
        "start_date": "2026-01-01",
    }


def _get_nationality_id(client: TestClient, headers: dict) -> int:
    resp = client.get("/api/v1/nationalities", headers=headers)
    items = resp.json().get("items", resp.json())
    vn = next((x for x in items if x["code"] == "VN"), None)
    return vn["id"] if vn else 1


# ── List & filter ──────────────────────────────────────────────────────────────

def test_list_employees_returns_page(client: TestClient):
    headers = _admin(client)
    resp = client.get(BASE, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data and "total" in data
    assert data["total"] >= 10  # seed đã có 10 nhân viên


def test_list_employees_filter_status(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}?status=official", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["status"] == "official"


def test_list_employees_filter_keyword(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}?keyword=Nguyễn Văn An", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any("An" in i["full_name"] for i in items)


def test_list_employees_requires_auth(client: TestClient):
    resp = client.get(BASE)
    assert resp.status_code == 401


# ── Create ─────────────────────────────────────────────────────────────────────

def test_create_employee_success(client: TestClient):
    headers = _admin(client)
    payload = _valid_payload("TEST999000001")
    resp = client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["full_name"] == payload["full_name"]
    assert "employee_seq" in data
    assert "display_code" in data
    assert data["display_code"] == f"{data['employee_seq']:04d}"
    assert data["addresses"] == []
    assert data["bank_accounts"] == []


def test_create_employee_auto_seq(client: TestClient):
    headers = _admin(client)
    r1 = client.post(BASE, json=_valid_payload("TEST999000011"), headers=headers)
    r2 = client.post(BASE, json=_valid_payload("TEST999000012"), headers=headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r2.json()["employee_seq"] == r1.json()["employee_seq"] + 1


def test_create_employee_duplicate_id_number(client: TestClient):
    headers = _admin(client)
    payload = _valid_payload("TEST999000021")
    client.post(BASE, json=payload, headers=headers)
    resp = client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 409


def test_create_employee_requires_create_permission(client: TestClient):
    headers = _officer(client)
    resp = client.post(BASE, json=_valid_payload("TEST999000031"), headers=headers)
    # hr_officer có employees:create → 201
    assert resp.status_code == 201


def test_create_employee_unauthorized(client: TestClient):
    resp = client.post(BASE, json=_valid_payload("TEST999000041"))
    assert resp.status_code == 401


# ── Get by ID ──────────────────────────────────────────────────────────────────

def test_get_employee_detail(client: TestClient):
    headers = _admin(client)
    created = client.post(BASE, json=_valid_payload("TEST999000051"), headers=headers).json()
    resp = client.get(f"{BASE}/{created['id']}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["display_code"] == created["display_code"]
    assert "addresses" in data
    assert "bank_accounts" in data


def test_get_employee_not_found(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}/999999", headers=headers)
    assert resp.status_code == 404


# ── Update ─────────────────────────────────────────────────────────────────────

def test_update_employee(client: TestClient):
    headers = _admin(client)
    created = client.post(BASE, json=_valid_payload("TEST999000061"), headers=headers).json()
    resp = client.put(
        f"{BASE}/{created['id']}",
        json={"status": "official", "personal_tax_code": "1234567890"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "official"
    assert data["personal_tax_code"] == "1234567890"
    assert data["employee_seq"] == created["employee_seq"]


def test_update_employee_not_found(client: TestClient):
    headers = _admin(client)
    resp = client.put(f"{BASE}/999999", json={"status": "official"}, headers=headers)
    assert resp.status_code == 404


# ── Soft delete ────────────────────────────────────────────────────────────────

def test_delete_employee(client: TestClient):
    headers = _admin(client)
    created = client.post(BASE, json=_valid_payload("TEST999000071"), headers=headers).json()
    resp = client.delete(f"{BASE}/{created['id']}", headers=headers)
    assert resp.status_code == 204
    # Vẫn lấy được nhưng is_active = False
    detail = client.get(f"{BASE}/{created['id']}", headers=headers).json()
    assert detail["is_active"] is False


def test_delete_employee_not_found(client: TestClient):
    headers = _admin(client)
    resp = client.delete(f"{BASE}/999999", headers=headers)
    assert resp.status_code == 404


# ── Lookup ─────────────────────────────────────────────────────────────────────

def test_lookup_employees(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}/lookup?keyword=Nguyễn", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    for item in items:
        assert "display_code" in item
        assert "employee_seq" in item


def test_lookup_returns_list_not_page(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}/lookup", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Addresses ──────────────────────────────────────────────────────────────────

def test_upsert_address(client: TestClient):
    headers = _admin(client)
    created = client.post(BASE, json=_valid_payload("TEST999000081"), headers=headers).json()
    emp_id = created["id"]

    payload = {
        "address_type": "permanent",
        "old_address_line": "123 Đường ABC, Phường X, Quận Y, TP.HCM",
        "full_address_text": "123 Đường ABC, Phường X, Quận Y, TP.HCM",
    }
    resp = client.put(f"{BASE}/{emp_id}/addresses", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["address_type"] == "permanent"
    assert data["full_address_text"] == payload["full_address_text"]


def test_upsert_address_updates_existing(client: TestClient):
    headers = _admin(client)
    created = client.post(BASE, json=_valid_payload("TEST999000082"), headers=headers).json()
    emp_id = created["id"]

    payload = {"address_type": "permanent", "full_address_text": "Địa chỉ cũ"}
    client.put(f"{BASE}/{emp_id}/addresses", json=payload, headers=headers)

    payload2 = {"address_type": "permanent", "full_address_text": "Địa chỉ mới"}
    resp = client.put(f"{BASE}/{emp_id}/addresses", json=payload2, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["full_address_text"] == "Địa chỉ mới"

    # Chỉ có 1 bản ghi permanent
    addrs = client.get(f"{BASE}/{emp_id}/addresses", headers=headers).json()
    permanent = [a for a in addrs if a["address_type"] == "permanent"]
    assert len(permanent) == 1


# ── Bank Accounts ──────────────────────────────────────────────────────────────

def _get_bank_id(client: TestClient, headers: dict) -> int:
    resp = client.get("/api/v1/banks", headers=headers)
    items = resp.json().get("items", resp.json())
    return items[0]["id"] if items else 1


def test_add_bank_account(client: TestClient):
    headers = _admin(client)
    created = client.post(BASE, json=_valid_payload("TEST999000091"), headers=headers).json()
    emp_id = created["id"]
    bank_id = _get_bank_id(client, headers)

    payload = {
        "bank_id": bank_id,
        "account_number": "1234567890",
        "account_name": "NGUYEN TEST VIEN",
        "is_primary": True,
    }
    resp = client.post(f"{BASE}/{emp_id}/bank-accounts", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_primary"] is True
    assert data["account_number"] == "1234567890"


def test_add_bank_account_sets_primary_exclusively(client: TestClient):
    headers = _admin(client)
    created = client.post(BASE, json=_valid_payload("TEST999000092"), headers=headers).json()
    emp_id = created["id"]
    bank_id = _get_bank_id(client, headers)

    client.post(f"{BASE}/{emp_id}/bank-accounts", json={
        "bank_id": bank_id, "account_number": "111", "account_name": "A", "is_primary": True
    }, headers=headers)
    client.post(f"{BASE}/{emp_id}/bank-accounts", json={
        "bank_id": bank_id, "account_number": "222", "account_name": "B", "is_primary": True
    }, headers=headers)

    accounts = client.get(f"{BASE}/{emp_id}/bank-accounts", headers=headers).json()
    primary_count = sum(1 for a in accounts if a["is_primary"])
    assert primary_count == 1


def test_delete_bank_account(client: TestClient):
    headers = _admin(client)
    created = client.post(BASE, json=_valid_payload("TEST999000093"), headers=headers).json()
    emp_id = created["id"]
    bank_id = _get_bank_id(client, headers)

    acc = client.post(f"{BASE}/{emp_id}/bank-accounts", json={
        "bank_id": bank_id, "account_number": "333", "account_name": "C"
    }, headers=headers).json()
    resp = client.delete(f"{BASE}/{emp_id}/bank-accounts/{acc['id']}", headers=headers)
    assert resp.status_code == 204

    accounts = client.get(f"{BASE}/{emp_id}/bank-accounts", headers=headers).json()
    assert not any(a["id"] == acc["id"] for a in accounts)


# ── Audit log ──────────────────────────────────────────────────────────────────

def test_create_employee_writes_audit_log(client: TestClient):
    headers = _admin(client)
    resp = client.post(BASE, json=_valid_payload("TEST999000101"), headers=headers)
    assert resp.status_code == 201
    emp_id = resp.json()["id"]

    logs = client.get(
        f"{AUDIT_BASE}?entity_type=employee&entity_id={emp_id}",
        headers=headers,
    ).json()
    assert any(
        log["action"] == "CREATE" and log["entity_type"] == "employee"
        for log in logs
    )


def test_update_employee_writes_audit_log(client: TestClient):
    headers = _admin(client)
    created = client.post(BASE, json=_valid_payload("TEST999000102"), headers=headers).json()
    emp_id = created["id"]

    client.put(f"{BASE}/{emp_id}", json={"status": "official"}, headers=headers)

    logs = client.get(
        f"{AUDIT_BASE}?entity_type=employee&entity_id={emp_id}",
        headers=headers,
    ).json()
    assert any(log["action"] == "UPDATE" for log in logs)


def test_delete_employee_writes_audit_log(client: TestClient):
    headers = _admin(client)
    created = client.post(BASE, json=_valid_payload("TEST999000103"), headers=headers).json()
    emp_id = created["id"]

    client.delete(f"{BASE}/{emp_id}", headers=headers)

    logs = client.get(
        f"{AUDIT_BASE}?entity_type=employee&entity_id={emp_id}",
        headers=headers,
    ).json()
    assert any(log["action"] == "DELETE" for log in logs)


# ── Seeded data sanity check ────────────────────────────────────────────────────

def test_seeded_employees_loaded(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}?page_size=100", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    names = [i["full_name"] for i in data["items"]]
    assert "Nguyễn Văn An" in names
    assert "Trần Thị Bình" in names


def test_seeded_resigned_employee(client: TestClient):
    headers = _admin(client)
    resp = client.get(f"{BASE}?status=resigned&page_size=50", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(i["full_name"] == "Trịnh Thị Kim" for i in items)
