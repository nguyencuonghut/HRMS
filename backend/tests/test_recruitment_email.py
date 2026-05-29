"""Integration tests — Plan 13.7 Slices 3/4: Candidate Communication emails."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi.testclient import TestClient
from app.core.config import settings

BASE_CAND = "/api/v1/recruitment/candidates"
BASE_TEMPLATES = "/api/v1/recruitment/email-templates"
BASE_JR = "/api/v1/recruitment/job-requisitions"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_TEST_CODE = "test_template_9999"


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _auth_headers(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Data helpers ───────────────────────────────────────────────────────────────

def _get_system_template_id(client: TestClient, headers: dict) -> int:
    """Return the id of the first system template found."""
    res = client.get(BASE_TEMPLATES, headers=headers)
    assert res.status_code == 200, res.text
    items = res.json()
    rows = items if isinstance(items, list) else items.get("items", [])
    for row in rows:
        if row.get("is_system"):
            return row["id"]
    raise AssertionError("No system template found in seed data")


def _create_candidate_no_email(client: TestClient, headers: dict) -> dict:
    """Create a candidate with phone but without personal_email (so email send fails)."""
    suffix = uuid.uuid4().hex[:8]
    res = client.post(
        BASE_CAND,
        json={
            "full_name": f"No Email Candidate {suffix}",
            "phone_number": f"09{suffix[:8]}",
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_candidate_with_email(client: TestClient, headers: dict) -> dict:
    suffix = uuid.uuid4().hex[:8]
    res = client.post(
        BASE_CAND,
        json={
            "full_name": f"Has Email Candidate {suffix}",
            "personal_email": f"cand_{suffix}@example.com",
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _cleanup_test_template(client: TestClient, headers: dict) -> None:
    """Delete the test template if it exists (idempotent)."""
    res = client.get(BASE_TEMPLATES, headers=headers)
    if res.status_code != 200:
        return
    items = res.json()
    rows = items if isinstance(items, list) else items.get("items", [])
    for row in rows:
        if row.get("code") == _TEST_CODE:
            client.delete(f"{BASE_TEMPLATES}/{row['id']}", headers=headers)
            break


# ── TestEmailTemplateCRUD ──────────────────────────────────────────────────────

class TestEmailTemplateCRUD:
    def test_list_templates_returns_seeded(self, client: TestClient) -> None:
        h = _auth_headers(client)
        res = client.get(BASE_TEMPLATES, headers=h)
        assert res.status_code == 200, res.text
        items = res.json()
        rows = items if isinstance(items, list) else items.get("items", [])
        assert len(rows) >= 7, f"Expected at least 7 seeded templates, got {len(rows)}"

    def test_create_template(self, client: TestClient) -> None:
        h = _auth_headers(client)
        _cleanup_test_template(client, h)

        res = client.post(
            BASE_TEMPLATES,
            json={
                "code": _TEST_CODE,
                "name": "Test Template 9999",
                "subject": "Xin chào {{ho_ten}}",
                "body_html": "<p>Kính gửi {{ho_ten}}, công ty {{ten_cong_ty}} xin thông báo.</p>",
                "trigger_event": None,
            },
            headers=h,
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["code"] == _TEST_CODE
        # merge_fields should be auto-detected from subject + body
        merge_fields = data.get("merge_fields", [])
        assert "ho_ten" in merge_fields or len(merge_fields) >= 1

    def test_update_template(self, client: TestClient) -> None:
        h = _auth_headers(client)

        # Ensure test template exists
        res = client.get(BASE_TEMPLATES, headers=h)
        rows = res.json() if isinstance(res.json(), list) else res.json().get("items", [])
        tmpl = next((r for r in rows if r.get("code") == _TEST_CODE), None)
        if tmpl is None:
            # Create it
            create_res = client.post(
                BASE_TEMPLATES,
                json={
                    "code": _TEST_CODE,
                    "name": "Test Template 9999",
                    "subject": "Xin chào {{ho_ten}}",
                    "body_html": "<p>Kính gửi {{ho_ten}}.</p>",
                },
                headers=h,
            )
            assert create_res.status_code == 201, create_res.text
            tmpl = create_res.json()

        res = client.put(
            f"{BASE_TEMPLATES}/{tmpl['id']}",
            json={"name": "Test Template 9999 Updated"},
            headers=h,
        )
        assert res.status_code == 200, res.text
        assert res.json()["name"] == "Test Template 9999 Updated"

    def test_delete_non_system_template(self, client: TestClient) -> None:
        h = _auth_headers(client)

        # Ensure test template exists
        res = client.get(BASE_TEMPLATES, headers=h)
        rows = res.json() if isinstance(res.json(), list) else res.json().get("items", [])
        tmpl = next((r for r in rows if r.get("code") == _TEST_CODE), None)
        if tmpl is None:
            create_res = client.post(
                BASE_TEMPLATES,
                json={
                    "code": _TEST_CODE,
                    "name": "Test Template 9999",
                    "subject": "Subject",
                    "body_html": "<p>Body</p>",
                },
                headers=h,
            )
            assert create_res.status_code == 201, create_res.text
            tmpl = create_res.json()

        tmpl_id = tmpl["id"]
        del_res = client.delete(f"{BASE_TEMPLATES}/{tmpl_id}", headers=h)
        assert del_res.status_code == 204, del_res.text

        get_res = client.get(f"{BASE_TEMPLATES}/{tmpl_id}", headers=h)
        assert get_res.status_code == 404


# ── TestSystemTemplateProtection ───────────────────────────────────────────────

class TestSystemTemplateProtection:
    def test_cannot_update_system_template(self, client: TestClient) -> None:
        h = _auth_headers(client)
        sys_id = _get_system_template_id(client, h)
        res = client.put(
            f"{BASE_TEMPLATES}/{sys_id}",
            json={"name": "Hacked Name"},
            headers=h,
        )
        assert res.status_code == 403, res.text

    def test_cannot_delete_system_template(self, client: TestClient) -> None:
        h = _auth_headers(client)
        sys_id = _get_system_template_id(client, h)
        res = client.delete(f"{BASE_TEMPLATES}/{sys_id}", headers=h)
        assert res.status_code == 403, res.text


# ── TestPreview ────────────────────────────────────────────────────────────────

class TestPreview:
    def _get_any_template_id(self, client: TestClient, h: dict) -> int:
        res = client.get(BASE_TEMPLATES, headers=h)
        assert res.status_code == 200, res.text
        items = res.json()
        rows = items if isinstance(items, list) else items.get("items", [])
        assert rows, "No templates found"
        return rows[0]["id"]

    def test_preview_with_sample_data(self, client: TestClient) -> None:
        h = _auth_headers(client)
        tmpl_id = self._get_any_template_id(client, h)
        res = client.post(
            f"{BASE_TEMPLATES}/{tmpl_id}/preview",
            json={"use_sample_data": True},
            headers=h,
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert "subject" in data
        assert "body_html" in data

    def test_preview_replaces_known_fields(self, client: TestClient) -> None:
        h = _auth_headers(client)
        _cleanup_test_template(client, h)

        # Create a template with a known merge field
        create_res = client.post(
            BASE_TEMPLATES,
            json={
                "code": _TEST_CODE,
                "name": "Preview Test Template",
                "subject": "Thư từ {{ten_cong_ty}}",
                "body_html": "<p>Công ty {{ten_cong_ty}} kính chào.</p>",
            },
            headers=h,
        )
        assert create_res.status_code == 201, create_res.text
        tmpl_id = create_res.json()["id"]

        res = client.post(
            f"{BASE_TEMPLATES}/{tmpl_id}/preview",
            json={"use_sample_data": True},
            headers=h,
        )
        assert res.status_code == 200, res.text
        data = res.json()
        # {{ten_cong_ty}} should be replaced (not literally present in output)
        assert "{{ten_cong_ty}}" not in data.get("body_html", ""), (
            "Merge field {{ten_cong_ty}} was not replaced in preview"
        )

        # Cleanup
        client.delete(f"{BASE_TEMPLATES}/{tmpl_id}", headers=h)


# ── TestSendEmail ──────────────────────────────────────────────────────────────

class TestSendEmail:
    def _get_first_template_id(self, client: TestClient, h: dict) -> int:
        res = client.get(BASE_TEMPLATES, headers=h)
        assert res.status_code == 200, res.text
        items = res.json()
        rows = items if isinstance(items, list) else items.get("items", [])
        assert rows
        return rows[0]["id"]

    def test_send_email_no_recipient_returns_failed(self, client: TestClient) -> None:
        h = _auth_headers(client)
        cand = _create_candidate_no_email(client, h)
        tmpl_id = self._get_first_template_id(client, h)

        res = client.post(
            f"{BASE_CAND}/{cand['id']}/communications/send",
            json={"template_id": tmpl_id},
            headers=h,
        )
        # Should NOT raise HTTP 4xx/5xx — must return 200 with status=failed
        assert res.status_code == 200, res.text
        data = res.json()
        assert data.get("status") == "failed", f"Expected status=failed, got: {data}"

    def test_send_email_with_invalid_smtp_returns_failed(self, client: TestClient, monkeypatch) -> None:
        h = _auth_headers(client)
        cand = _create_candidate_with_email(client, h)
        tmpl_id = self._get_first_template_id(client, h)

        monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1")
        monkeypatch.setattr(settings, "SMTP_PORT", 1)
        monkeypatch.setattr(settings, "SMTP_USE_TLS", False)
        monkeypatch.setattr(settings, "SMTP_USE_STARTTLS", False)
        monkeypatch.setattr(settings, "SMTP_USERNAME", "")
        monkeypatch.setattr(settings, "SMTP_PASSWORD", "")

        res = client.post(
            f"{BASE_CAND}/{cand['id']}/communications/send",
            json={"template_id": tmpl_id},
            headers=h,
        )
        # SMTP is not configured in test env → should store failure, not raise
        assert res.status_code == 200, res.text
        data = res.json()
        assert data.get("status") == "failed", f"Expected status=failed, got: {data}"

        # Verify the failed comm is persisted and appears in the list
        comm_id = data.get("id")
        assert comm_id, "Expected a communication id in the response"
        list_res = client.get(f"{BASE_CAND}/{cand['id']}/communications", headers=h)
        assert list_res.status_code == 200, list_res.text
        items = list_res.json()
        rows = items if isinstance(items, list) else items.get("items", [])
        matching = [r for r in rows if r.get("id") == comm_id]
        assert matching, f"Communication id={comm_id} not found in list"
        assert matching[0].get("status") == "failed"

    def test_communications_list(self, client: TestClient) -> None:
        h = _auth_headers(client)
        cand = _create_candidate_with_email(client, h)

        res = client.get(
            f"{BASE_CAND}/{cand['id']}/communications",
            headers=h,
        )
        assert res.status_code == 200, res.text
        items = res.json()
        # Should return a list (may be empty for a fresh candidate)
        rows = items if isinstance(items, list) else items.get("items", [])
        assert isinstance(rows, list)
