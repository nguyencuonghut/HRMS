"""Tests cho module nhân viên (3.1)."""

import io

import openpyxl
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
            "DELETE FROM employee_job_records WHERE department_id IN "
            "(SELECT id FROM departments WHERE code LIKE 'TESTDEPT%')"
        ))
        await s.execute(text(
            "DELETE FROM employee_bank_accounts WHERE employee_id IN "
            "(SELECT id FROM employees WHERE id_number LIKE 'TEST%')"
        ))
        await s.execute(text("DELETE FROM employees WHERE id_number LIKE 'TEST%'"))
        await s.execute(text("DELETE FROM departments WHERE code LIKE 'TESTDEPT%'"))
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
        "employee_code_sequence_id": 1,
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


def _get_department(client: TestClient, headers: dict, code: str = "HC") -> dict:
    resp = client.get("/api/v1/departments", headers=headers)
    payload = resp.json()
    items = payload["items"] if isinstance(payload, dict) else payload
    dept = next((x for x in items if x["code"] == code), None)
    assert dept is not None, f"Department '{code}' not found"
    return dept


def _create_department(client: TestClient, headers: dict, code: str, name: str) -> dict:
    resp = client.post(
        "/api/v1/departments",
        json={"code": code, "name": name, "dept_type": "PHONG"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _get_job_position(client: TestClient, headers: dict, department_id: int | None = None) -> dict:
    params = {"is_active": True}
    if department_id is not None:
        params["department_id"] = department_id
    resp = client.get("/api/v1/job-positions", params=params, headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert items, f"No active job position for department_id={department_id}"
    return items[0]


async def _set_employee_sequence_config(id_number: str, *, sequence_code: str, min_digits: int) -> None:
    async with _make_session()() as s:
        await s.execute(
            text(
                """
                UPDATE employee_code_sequences
                SET min_digits = :min_digits
                WHERE code = :sequence_code
                """
            ),
            {"sequence_code": sequence_code, "min_digits": min_digits},
        )
        await s.execute(
            text(
                """
                UPDATE employees
                SET employee_code_sequence_id = (
                    SELECT id FROM employee_code_sequences WHERE code = :sequence_code
                )
                WHERE id_number = :id_number
                """
            ),
            {"sequence_code": sequence_code, "id_number": id_number},
        )
        await s.commit()


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


def test_create_employee_without_sequence_or_job_context_rejected(client: TestClient):
    headers = _admin(client)
    payload = _valid_payload("TEST999000040")
    payload.pop("employee_code_sequence_id", None)
    resp = client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 422


def test_create_employee_with_initial_job_context_creates_current_job(client: TestClient):
    headers = _admin(client)
    position = _get_job_position(client, headers)
    dept_payload = client.get("/api/v1/departments", headers=headers).json()
    departments = dept_payload["items"] if isinstance(dept_payload, dict) else dept_payload
    dept = next(d for d in departments if d["id"] == position["department_id"])

    payload = {
        **_valid_payload("TEST999000042"),
        "initial_department_id": dept["id"],
        "initial_job_title_id": position["job_title_id"],
        "initial_job_position_id": position["id"],
        "initial_job_effective_from": "2026-01-01",
    }
    resp = client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["current_job"] is not None
    assert data["current_job"]["department_id"] == dept["id"]
    assert data["current_job"]["job_position_id"] == position["id"]
    assert data["current_job"]["is_current"] is True
    assert data["display_code"].startswith(data["current_job"]["department"]["display_prefix"] or "")


def test_create_employee_rejects_job_position_department_mismatch(client: TestClient):
    headers = _admin(client)
    position = _get_job_position(client, headers)
    other_resp = client.get("/api/v1/departments", headers=headers)
    payload = other_resp.json()
    depts = payload["items"] if isinstance(payload, dict) else payload
    other_dept = next((x for x in depts if x["id"] != position["department_id"]), None)
    assert other_dept is not None

    payload = {
        **_valid_payload("TEST999000043"),
        "initial_department_id": other_dept["id"],
        "initial_job_position_id": position["id"],
        "initial_job_effective_from": "2026-01-01",
    }
    resp = client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 422
    assert "không thuộc phòng ban" in resp.json()["detail"]


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


@pytest.mark.asyncio
async def test_lookup_uses_current_job_prefix(client: TestClient):
    headers = _admin(client)
    id_number = "TEST999LOOKUP001"
    created = client.post(BASE, json=_valid_payload(id_number), headers=headers).json()

    dept_items = client.get("/api/v1/departments", headers=headers).json()
    items = dept_items["items"] if isinstance(dept_items, dict) else dept_items
    hc = next(d for d in items if d["code"] == "HC")
    client.post(
        f"{BASE}/{created['id']}/job-records",
        json={"department_id": hc["id"], "effective_from": "2026-01-01"},
        headers=headers,
    )

    resp = client.get(f"{BASE}/lookup?keyword={id_number}", headers=headers)
    assert resp.status_code == 200
    found = next(item for item in resp.json() if item["id"] == created["id"])
    assert found["display_code"].startswith("HC")


def test_list_and_lookup_fall_back_to_department_code_when_prefix_missing(client: TestClient):
    headers = _admin(client)
    id_number = "TEST999LOOKUP002"
    created = client.post(BASE, json=_valid_payload(id_number), headers=headers).json()
    dept = _create_department(client, headers, "TESTDEPTNP1", "Test Dept No Prefix")

    job_record_resp = client.post(
        f"{BASE}/{created['id']}/job-records",
        json={"department_id": dept["id"], "effective_from": "2026-01-01"},
        headers=headers,
    )
    assert job_record_resp.status_code == 201, job_record_resp.text

    list_resp = client.get(f"{BASE}?keyword={id_number}", headers=headers)
    assert list_resp.status_code == 200
    list_item = next(item for item in list_resp.json()["items"] if item["id"] == created["id"])
    assert list_item["display_code"].startswith(dept["code"])

    lookup_resp = client.get(f"{BASE}/lookup?keyword={id_number}", headers=headers)
    assert lookup_resp.status_code == 200
    lookup_item = next(item for item in lookup_resp.json() if item["id"] == created["id"])
    assert lookup_item["display_code"].startswith(dept["code"])

    detail_resp = client.get(f"{BASE}/{created['id']}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["display_code"].startswith(dept["code"])


@pytest.mark.asyncio
async def test_prefixed_display_code_uses_four_digits_even_if_sequence_min_digits_is_higher(client: TestClient):
    headers = _admin(client)
    id_number = "TEST999LOOKUP003"
    created = client.post(BASE, json=_valid_payload(id_number), headers=headers).json()
    hc = _get_department(client, headers, "HC")

    job_record_resp = client.post(
        f"{BASE}/{created['id']}/job-records",
        json={"department_id": hc["id"], "effective_from": "2026-01-01"},
        headers=headers,
    )
    assert job_record_resp.status_code == 201, job_record_resp.text

    await _set_employee_sequence_config(id_number, sequence_code="SYS3", min_digits=7)

    detail_resp = client.get(f"{BASE}/{created['id']}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["display_code"] == f"HC{created['employee_seq']:04d}"

    list_resp = client.get(f"{BASE}?keyword={id_number}", headers=headers)
    assert list_resp.status_code == 200
    list_item = next(item for item in list_resp.json()["items"] if item["id"] == created["id"])
    assert list_item["display_code"] == f"HC{created['employee_seq']:04d}"

    lookup_resp = client.get(f"{BASE}/lookup?keyword={id_number}", headers=headers)
    assert lookup_resp.status_code == 200
    lookup_item = next(item for item in lookup_resp.json() if item["id"] == created["id"])
    assert lookup_item["display_code"] == f"HC{created['employee_seq']:04d}"


@pytest.mark.asyncio
async def test_detail_and_list_use_sequence_min_digits(client: TestClient):
    headers = _admin(client)
    id_number = "TEST999SEQDIG001"
    created = client.post(BASE, json=_valid_payload(id_number), headers=headers).json()

    await _set_employee_sequence_config(id_number, sequence_code="SYS2", min_digits=6)

    detail = client.get(f"{BASE}/{created['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["display_code"] == f"{created['employee_seq']:06d}"

    list_resp = client.get(f"{BASE}?keyword={id_number}", headers=headers)
    assert list_resp.status_code == 200
    list_item = next(item for item in list_resp.json()["items"] if item["id"] == created["id"])
    assert list_item["display_code"] == f"{created['employee_seq']:06d}"


@pytest.mark.asyncio
async def test_export_list_uses_sequence_min_digits(client: TestClient):
    headers = _admin(client)
    id_number = "TEST999EXPORTSEQ1"
    created = client.post(BASE, json=_valid_payload(id_number), headers=headers).json()

    await _set_employee_sequence_config(id_number, sequence_code="SYS3", min_digits=7)

    resp = client.get(f"{BASE}/export?keyword={id_number}", headers=headers)
    assert resp.status_code == 200

    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    ws = wb.active
    assert ws.cell(row=2, column=1).value == f"{created['employee_seq']:07d}"


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
