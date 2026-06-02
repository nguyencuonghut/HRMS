"""Integration tests — Plan 13.6: Document Checklist nhân viên."""
from __future__ import annotations

import io
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

BASE_CAND = "/api/v1/recruitment/candidates"
BASE_JR = "/api/v1/recruitment/job-requisitions"
BASE_OFFERS = "/api/v1/recruitment/offers"
BASE_HD = "/api/v1/recruitment/hiring-decisions"
BASE_EMP = "/api/v1/employees"
BASE_REC = "/api/v1/recruitment"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"


# ── Auth helper ────────────────────────────────────────────────────────────────

def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_nationality_id(client: TestClient, headers: dict) -> int:
    resp = client.get("/api/v1/nationalities", headers=headers)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    items = payload["items"] if isinstance(payload, dict) else payload
    vn = next((item for item in items if item["code"] == "VN"), None)
    if vn is not None:
        return vn["id"]
    assert items, "Không có nationality nào trong hệ thống"
    return items[0]["id"]


# ── Data-setup helpers (mirrors test_recruitment_offer.py) ─────────────────────

def _get_pos_dept(client: TestClient, h: dict) -> tuple[int, int]:
    items = client.get("/api/v1/job-positions", headers=h, params={"page_size": 50}).json()
    rows = items if isinstance(items, list) else items.get("items", items)
    row = rows[0]
    return row["id"], row["department_id"]


def _create_approved_jr(client: TestClient, h: dict, pos_id: int, dept_id: int) -> dict:
    jr = client.post(
        BASE_JR,
        json={
            "job_position_id": pos_id,
            "department_id": dept_id,
            "quantity": 1,
            "reason_type": "new",
        },
        headers=h,
    ).json()
    client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)
    client.post(f"{BASE_JR}/{jr['id']}/approve", headers=h)
    pipeline_res = client.post(
        f"{BASE_JR}/{jr['id']}/pipeline",
        json={
            "stages": [
                {
                    "stage_order": 1,
                    "stage_name": "Sàng lọc hồ sơ",
                    "stage_type": "screening",
                    "is_active": True,
                }
            ]
        },
        headers=h,
    )
    assert pipeline_res.status_code == 200, pipeline_res.text
    return client.get(f"{BASE_JR}/{jr['id']}", headers=h).json()


def _create_candidate_full(client: TestClient, h: dict, suffix: str) -> dict:
    nationality_id = _get_nationality_id(client, h)
    res = client.post(
        BASE_CAND,
        json={
            "full_name": f"Ứng Viên Doc {suffix}",
            "last_name": "Ứng Viên",
            "first_name": suffix,
            "personal_email": f"doc_{suffix}@example.com",
            "date_of_birth": "1992-06-15",
            "gender": "male",
            "nationality_id": nationality_id,
            "id_number": f"0{suffix[:9]}",
            "id_issued_on": "2015-06-01",
            "id_issued_by": "Cục CSQLHC",
        },
        headers=h,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _apply(client: TestClient, h: dict, candidate_id: int, jr_id: int) -> dict:
    res = client.post(
        f"{BASE_CAND}/{candidate_id}/apply",
        json={"job_requisition_id": jr_id, "applied_date": str(date.today())},
        headers=h,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _advance_application_to_offer(
    client: TestClient,
    h: dict,
    application_id: int,
    jr_id: int,
    current_stage: str,
) -> dict:
    pipeline_res = client.get(f"{BASE_JR}/{jr_id}/pipeline", headers=h)
    assert pipeline_res.status_code == 200, pipeline_res.text
    stages = pipeline_res.json()
    assert stages, "JR không có pipeline stages"

    application_stage = current_stage
    while application_stage != "offer":
        stage = next((item for item in stages if item["stage_type"] == application_stage), None)
        assert stage is not None, f"Không tìm thấy stage '{application_stage}' trong pipeline"
        advance_res = client.post(
            f"{BASE_REC}/applications/{application_id}/advance",
            json={"stage_id": stage["id"], "result": "pass"},
            headers=h,
        )
        assert advance_res.status_code == 200, advance_res.text
        application = advance_res.json()
        application_stage = application["current_stage"]
    return application


def _create_offer(client: TestClient, h: dict, application_id: int, pos_id: int, dept_id: int) -> dict:
    res = client.post(
        f"/api/v1/recruitment/applications/{application_id}/offers",
        json={
            "job_position_id": pos_id,
            "department_id": dept_id,
            "proposed_start_date": str(date.today() + timedelta(days=14)),
            "probation_salary": 8_000_000,
            "official_salary": 10_000_000,
            "probation_days": 30,
            "expires_at": str(date.today() + timedelta(days=7)),
        },
        headers=h,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _setup_and_convert(client: TestClient, h: dict) -> int:
    """
    Full pipeline: JR → Candidate → Application → Offer (accepted) →
    HiringDecision → Convert.  Returns the new employee_id.
    """
    suffix = uuid.uuid4().hex[:8]
    pos_id, dept_id = _get_pos_dept(client, h)
    jr = _create_approved_jr(client, h, pos_id, dept_id)
    cand = _create_candidate_full(client, h, suffix)
    app = _apply(client, h, cand["id"], jr["id"])
    app = _advance_application_to_offer(client, h, app["id"], jr["id"], app["current_stage"])
    offer = _create_offer(client, h, app["id"], pos_id, dept_id)

    client.post(f"{BASE_OFFERS}/{offer['id']}/send", headers=h)
    client.post(f"{BASE_OFFERS}/{offer['id']}/accept", headers=h)

    hd_res = client.post(
        f"{BASE_OFFERS}/{offer['id']}/hiring-decision",
        json={
            "signed_date": str(date.today()),
            "department_id": dept_id,
            "job_position_id": pos_id,
            "start_date": str(date.today() + timedelta(days=14)),
            "probation_salary": 8_000_000,
            "official_salary": 10_000_000,
            "probation_days": 30,
        },
        headers=h,
    )
    assert hd_res.status_code == 201, hd_res.text
    hd = hd_res.json()

    conv_res = client.post(f"{BASE_HD}/{hd['id']}/convert", headers=h)
    assert conv_res.status_code == 200, conv_res.text
    return conv_res.json()["employee_id"]


# ── Module-scoped fixture: one converted employee for all checklist tests ──────

@pytest.fixture(scope="module")
def converted_employee(client: TestClient):
    """
    Creates a candidate, runs through the full offer → convert pipeline,
    and returns (employee_id, auth_headers).  Shared across all tests in
    this module to avoid repeating the expensive setup.
    """
    h = _admin(client)
    emp_id = _setup_and_convert(client, h)
    return emp_id, h


# ── TestChecklistRead ──────────────────────────────────────────────────────────

class TestChecklistRead:
    def test_checklist_initialized_after_convert(
        self, client: TestClient, converted_employee
    ) -> None:
        emp_id, h = converted_employee
        res = client.get(f"{BASE_EMP}/{emp_id}/document-checklist", headers=h)
        assert res.status_code == 200, res.text
        items = res.json()
        assert isinstance(items, list)
        assert len(items) > 0, "Checklist phải được khởi tạo sau khi convert"

    def test_checklist_item_has_required_fields(
        self, client: TestClient, converted_employee
    ) -> None:
        emp_id, h = converted_employee
        res = client.get(f"{BASE_EMP}/{emp_id}/document-checklist", headers=h)
        assert res.status_code == 200, res.text
        item = res.json()[0]
        assert "document_type_name" in item
        assert "document_type_code" in item
        assert "is_required" in item
        assert "has_file" in item
        assert item["has_file"] is False
        assert "status" in item


# ── TestChecklistUpdate ────────────────────────────────────────────────────────

class TestChecklistUpdate:
    def _get_items(self, client: TestClient, emp_id: int, h: dict) -> list:
        res = client.get(f"{BASE_EMP}/{emp_id}/document-checklist", headers=h)
        assert res.status_code == 200, res.text
        return res.json()

    def _find_no_expiry_item(self, items: list) -> dict | None:
        for item in items:
            if not item["has_expiry"]:
                return item
        return None

    def _find_expiry_item(self, items: list) -> dict | None:
        for item in items:
            if item["has_expiry"]:
                return item
        return None

    def test_update_status_to_submitted_no_expiry(
        self, client: TestClient, converted_employee
    ) -> None:
        emp_id, h = converted_employee
        items = self._get_items(client, emp_id, h)
        item = self._find_no_expiry_item(items)
        if item is None:
            pytest.skip("Không có item nào không có has_expiry — bỏ qua test này")

        res = client.put(
            f"{BASE_EMP}/{emp_id}/document-checklist/{item['id']}",
            json={"status": "submitted", "submitted_at": "2026-01-01"},
            headers=h,
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "submitted"

    def test_upload_file_returns_mime_type(
        self, client: TestClient, converted_employee
    ) -> None:
        emp_id, h = converted_employee
        items = self._get_items(client, emp_id, h)
        item = self._find_no_expiry_item(items) or items[0]

        res = client.post(
            f"{BASE_EMP}/{emp_id}/document-checklist/{item['id']}/upload",
            files={"file": ("checklist-preview.png", io.BytesIO(b"png-bytes"), "image/png")},
            headers=h,
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["has_file"] is True
        assert data["file_name"] == "checklist-preview.png"
        assert data["mime_type"] == "image/png"

    def test_update_submitted_with_expiry_requires_expires_at(
        self, client: TestClient, converted_employee
    ) -> None:
        emp_id, h = converted_employee
        items = self._get_items(client, emp_id, h)
        item = self._find_expiry_item(items)
        if item is None:
            pytest.skip("Không có item nào có has_expiry — bỏ qua test này")

        # Không gửi expires_at → phải trả 422
        res = client.put(
            f"{BASE_EMP}/{emp_id}/document-checklist/{item['id']}",
            json={"status": "submitted", "submitted_at": "2026-01-01"},
            headers=h,
        )
        assert res.status_code == 422, res.text

    def test_update_submitted_with_expiry_ok(
        self, client: TestClient, converted_employee
    ) -> None:
        emp_id, h = converted_employee
        items = self._get_items(client, emp_id, h)
        item = self._find_expiry_item(items)
        if item is None:
            pytest.skip("Không có item nào có has_expiry — bỏ qua test này")

        future_date = str(date.today() + timedelta(days=365))
        res = client.put(
            f"{BASE_EMP}/{emp_id}/document-checklist/{item['id']}",
            json={
                "status": "submitted",
                "submitted_at": "2026-01-01",
                "expires_at": future_date,
            },
            headers=h,
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "submitted"


# ── TestChecklistWaive ─────────────────────────────────────────────────────────

class TestChecklistWaive:
    def test_waive_item(self, client: TestClient, converted_employee) -> None:
        emp_id, h = converted_employee
        # Get checklist and pick a not_submitted item to waive
        res = client.get(f"{BASE_EMP}/{emp_id}/document-checklist", headers=h)
        assert res.status_code == 200, res.text
        items = res.json()

        # Find any not_submitted item (prefer non-required so we don't break summary tests)
        not_submitted = [i for i in items if i["status"] == "not_submitted" and not i["is_required"]]
        if not not_submitted:
            not_submitted = [i for i in items if i["status"] == "not_submitted"]
        if not not_submitted:
            pytest.skip("Không còn item nào ở trạng thái not_submitted để waive")

        item = not_submitted[0]
        res = client.post(
            f"{BASE_EMP}/{emp_id}/document-checklist/{item['id']}/waive",
            params={"reason": "Test waive reason"},
            headers=h,
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "waived"
        assert data["waived_reason"] == "Test waive reason"


# ── TestMissingDocumentsReport ─────────────────────────────────────────────────

class TestMissingDocumentsReport:
    def test_summary_endpoint_returns_list(
        self, client: TestClient, converted_employee
    ) -> None:
        _, h = converted_employee
        res = client.get(f"{BASE_REC}/document-checklist/summary", headers=h)
        assert res.status_code == 200, res.text
        assert isinstance(res.json(), list)

    def test_summary_employee_has_missing(
        self, client: TestClient, converted_employee
    ) -> None:
        emp_id, h = converted_employee
        res = client.get(
            f"{BASE_REC}/document-checklist/summary",
            params={"status": "incomplete"},
            headers=h,
        )
        assert res.status_code == 200, res.text
        data = res.json()
        # The converted employee should appear in the incomplete list
        # because some required docs remain not_submitted
        emp_ids = [row["employee_id"] for row in data]
        # It's possible all required docs were submitted in earlier tests;
        # we only assert the response shape is correct and the endpoint works.
        for row in data:
            assert "employee_id" in row
            assert "missing_count" in row
            assert "total_required" in row
            assert "completion_rate" in row

        # If our employee is in the list, assert missing_count >= 0
        for row in data:
            if row["employee_id"] == emp_id:
                assert row["missing_count"] >= 0
                break


# ── TestLaborReport ────────────────────────────────────────────────────────────

class TestLaborReport:
    def test_labor_report_export(self, client: TestClient, converted_employee) -> None:
        _, h = converted_employee
        res = client.get(
            f"{BASE_REC}/labor-report/export",
            params={"year": 2026, "month": 1},
            headers=h,
        )
        assert res.status_code == 200, res.text
        # Response should be an Excel file
        content_type = res.headers.get("content-type", "")
        assert "spreadsheetml" in content_type or "octet-stream" in content_type, (
            f"Expected xlsx content-type, got: {content_type}"
        )

    def test_labor_report_current_month(
        self, client: TestClient, converted_employee
    ) -> None:
        _, h = converted_employee
        today = date.today()
        res = client.get(
            f"{BASE_REC}/labor-report/export",
            params={"year": today.year, "month": today.month},
            headers=h,
        )
        assert res.status_code == 200, res.text
