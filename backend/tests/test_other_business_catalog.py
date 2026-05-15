from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds import other_business_catalog

CONTRACT_CATEGORY_BASE = "/api/v1/contract-categories"
BANK_BASE = "/api/v1/banks"
SKILL_BASE = "/api/v1/skills"
LEAVE_TYPE_BASE = "/api/v1/leave-types"
TEMPLATE_BASE = "/api/v1/contract-templates"
LOOKUP_SKILLS = "/api/v1/lookups/skills"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_OFFICER_EMAIL = "hrofficer@hrms.local"


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


async def _cleanup_test_rows():
    async with _make_session()() as s:
        await s.execute(text("DELETE FROM contract_template_placeholders WHERE template_id IN (SELECT id FROM contract_templates WHERE code LIKE 'test_template_%')"))
        await s.execute(text("DELETE FROM contract_templates WHERE code LIKE 'test_template_%'"))
        await s.execute(text("DELETE FROM banks WHERE code LIKE 'TEST_BANK_%'"))
        await s.execute(text("DELETE FROM leave_types WHERE code LIKE 'TEST_LEAVE_%'"))
        await s.commit()


import pytest


@pytest.fixture(scope="session", autouse=True)
async def seed_other_business_catalog_data():
    async with _make_session()() as session:
        await other_business_catalog.seed_required_other_business_catalog(session)
        await other_business_catalog.seed_sample_other_business_catalog(session)
        await session.commit()
    yield


@pytest.fixture(autouse=True)
async def session_cleanup():
    await _cleanup_test_rows()
    yield
    await _cleanup_test_rows()


def test_list_contract_categories_supports_filters(client: TestClient):
    resp = client.get(CONTRACT_CATEGORY_BASE, params={"document_kind": "labor_contract"}, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 2
    assert any(item["code"] == "labor_indefinite" for item in body["items"])


def test_create_and_update_bank_success(client: TestClient):
    created = client.post(
        BANK_BASE,
        json={
            "code": "TEST_BANK_001",
            "name": "Ngân hàng Kiểm thử 01",
            "short_name": "Test Bank",
            "bin_code": "999999",
            "swift_code": "TESTVNVX",
        },
        headers=_admin(client),
    )
    assert created.status_code == 201, created.text
    row = created.json()
    assert row["code"] == "TEST_BANK_001"

    updated = client.put(
        f"{BANK_BASE}/{row['id']}",
        json={"name": "Ngân hàng Kiểm thử 01 Updated", "short_name": "Test Bank U"},
        headers=_admin(client),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Ngân hàng Kiểm thử 01 Updated"

    logs = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "bank", "action": "UPDATE", "limit": 10},
        headers=_admin(client),
    )
    assert logs.status_code == 200, logs.text
    assert any(item["entity_name"] == "Ngân hàng Kiểm thử 01 Updated" for item in logs.json())


def test_lookup_skills_supports_keyword_search(client: TestClient):
    resp = client.get(LOOKUP_SKILLS, params={"keyword": "xuat nhap khau"}, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert any(item["code"] == "import_export_ops" for item in rows)


def test_delete_leave_type_soft_deactivate(client: TestClient):
    created = client.post(
        LEAVE_TYPE_BASE,
        json={"code": "TEST_LEAVE_001", "name": "Nghỉ kiểm thử", "is_paid_leave": False},
        headers=_admin(client),
    )
    assert created.status_code == 201, created.text
    row_id = created.json()["id"]

    deleted = client.delete(f"{LEAVE_TYPE_BASE}/{row_id}", headers=_admin(client))
    assert deleted.status_code == 200, deleted.text

    detail = client.get(f"{LEAVE_TYPE_BASE}/{row_id}", headers=_admin(client))
    assert detail.status_code == 200, detail.text
    assert detail.json()["is_active"] is False


def test_contract_template_create_and_replace_placeholders(client: TestClient):
    category_resp = client.get(CONTRACT_CATEGORY_BASE, params={"keyword": "HĐLĐ xác định"}, headers=_admin(client))
    assert category_resp.status_code == 200, category_resp.text
    category_id = category_resp.json()["items"][0]["id"]

    created = client.post(
        TEMPLATE_BASE,
        json={
            "code": "test_template_contract_001",
            "name": "Mẫu test hợp đồng 001",
            "contract_category_id": category_id,
            "document_kind": "labor_contract",
            "template_engine": "docx_placeholders",
            "file_name": "test_contract_001.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "version_no": 1,
        },
        headers=_admin(client),
    )
    assert created.status_code == 201, created.text
    template_id = created.json()["id"]

    put_placeholders = client.put(
        f"{TEMPLATE_BASE}/{template_id}/placeholders",
        json=[
            {
                "placeholder_key": "employee.full_name",
                "label": "Họ tên",
                "source_scope": "employee",
                "source_path": "employee.full_name",
                "data_type": "text",
                "is_required": True,
                "sort_order": 10,
            },
            {
                "placeholder_key": "contract.contract_number",
                "label": "Số hợp đồng",
                "source_scope": "contract_draft",
                "source_path": "contract.contract_number",
                "data_type": "text",
                "is_required": True,
                "sort_order": 20,
            },
        ],
        headers=_admin(client),
    )
    assert put_placeholders.status_code == 200, put_placeholders.text
    rows = put_placeholders.json()
    assert len(rows) == 2
    assert rows[0]["placeholder_key"] == "employee.full_name"


def test_inspect_contract_template_docx_reads_real_sample_placeholders(client: TestClient):
    templates = client.get(TEMPLATE_BASE, params={"keyword": "xac dinh thoi han 12 thang"}, headers=_admin(client))
    assert templates.status_code == 200, templates.text
    template_id = templates.json()["items"][0]["id"]

    inspected = client.post(f"{TEMPLATE_BASE}/{template_id}/inspect-docx", headers=_admin(client))
    assert inspected.status_code == 200, inspected.text
    body = inspected.json()

    keys = {item["placeholder_key"] for item in body["detected_placeholders"]}
    assert "employee_full_name" in keys
    assert "employee_cccd_issued_on" in keys
    assert "Ngày" in keys
    assert "SĐT" in keys
    assert body["supported_count"] >= 1
    assert any("MERGEFIELD" in warning for warning in body["warnings"])


def test_lookup_contract_template_fields_returns_registry(client: TestClient):
    resp = client.get("/api/v1/lookups/contract-template-fields", headers=_admin(client))
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert any(item["token"] == "employee_full_name" and item["source_path"] == "employee.full_name" for item in rows)
    assert any(item["token"] == "Ngày" and item["recommended_token"] == "contract_signing_day" for item in rows)


def test_officer_cannot_delete_leave_type(client: TestClient):
    created = client.post(
        LEAVE_TYPE_BASE,
        json={"code": "TEST_LEAVE_002", "name": "Nghỉ officer test"},
        headers=_admin(client),
    )
    assert created.status_code == 201, created.text

    deleted = client.delete(f"{LEAVE_TYPE_BASE}/{created.json()['id']}", headers=_officer(client))
    assert deleted.status_code == 403


def test_other_business_catalog_endpoints_require_token(client: TestClient):
    resp = client.get(BANK_BASE)
    assert resp.status_code == 401


# ── Bước 6: Audit log coverage ──────────────────────────────────────────────────

def test_catalog_create_writes_audit_log(client: TestClient):
    """Tạo catalog item phải sinh audit log entity_type tương ứng."""
    created = client.post(
        BANK_BASE,
        json={"code": "TEST_BANK_AUDIT_01", "name": "Ngân hàng audit test"},
        headers=_admin(client),
    )
    assert created.status_code == 201, created.text
    bank_id = created.json()["id"]

    logs = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "bank", "action": "CREATE", "limit": 5},
        headers=_admin(client),
    )
    assert logs.status_code == 200, logs.text
    items = logs.json()
    assert any(item["entity_id"] == bank_id for item in items)


def test_contract_template_operations_write_audit_log(client: TestClient):
    """Tạo template + thay đổi placeholder phải sinh audit log."""
    category_resp = client.get(CONTRACT_CATEGORY_BASE, params={"keyword": "HĐLĐ xác định"}, headers=_admin(client))
    assert category_resp.status_code == 200, category_resp.text
    category_id = category_resp.json()["items"][0]["id"]

    created = client.post(
        TEMPLATE_BASE,
        json={
            "code": "test_template_audit_01",
            "name": "Template audit test",
            "contract_category_id": category_id,
            "document_kind": "labor_contract",
            "template_engine": "docx_placeholders",
            "file_name": "audit_test.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        headers=_admin(client),
    )
    assert created.status_code == 201, created.text
    tmpl_id = created.json()["id"]

    # Replace placeholders → should log
    client.put(
        f"{TEMPLATE_BASE}/{tmpl_id}/placeholders",
        json=[{
            "placeholder_key": "employee_full_name",
            "label": "Họ và tên",
            "source_scope": "employee",
            "source_path": "employee.full_name",
            "data_type": "text",
            "is_required": True,
            "sort_order": 10,
        }],
        headers=_admin(client),
    )

    logs = client.get(
        "/api/v1/audit-logs",
        params={"entity_type": "contract_template", "limit": 10},
        headers=_admin(client),
    )
    assert logs.status_code == 200, logs.text
    items = logs.json()
    entity_ids = [item["entity_id"] for item in items]
    assert tmpl_id in entity_ids

    actions = {item["action"] for item in items if item["entity_id"] == tmpl_id}
    assert "CREATE" in actions
    assert "UPDATE" in actions  # placeholder replace dùng action UPDATE
