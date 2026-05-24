"""Integration tests cho Plan 9.3 — Chứng chỉ đào tạo nhân viên."""
from __future__ import annotations

import io
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

BASE_CERTS     = "/api/v1/training/certificates"
BASE_COURSES   = "/api/v1/training/courses"
BASE_EMPLOYEES = "/api/v1/employees"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_RUN_ID = uuid.uuid4().hex[:8]

_TODAY      = date.today()
_ISSUED     = str(_TODAY - timedelta(days=60))
_EXPIRY_OK  = str(_TODAY + timedelta(days=90))   # valid (> 30 days)
_EXPIRY_SOON = str(_TODAY + timedelta(days=15))  # expiring soon (≤ 30 days)
_EXPIRY_OLD  = str(_TODAY - timedelta(days=10))  # expired


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_emp_id(client, h) -> int:
    r = client.get(BASE_EMPLOYEES, headers=h, params={"page_size": 1})
    items = r.json()["items"]
    assert items, "Cần ít nhất 1 nhân viên active trong DB"
    return items[0]["id"]


def _make_course(client, h, suffix: str = "") -> dict:
    code = f"CERT{_RUN_ID}{suffix}"[:50]
    r = client.post(
        BASE_COURSES,
        json={"code": code, "name": f"Cert Course {suffix or _RUN_ID}", "course_type": "noi_bo"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_cert(client, h, emp_id: int, **kwargs) -> dict:
    body = {
        "employee_id": emp_id,
        "certificate_name": f"Cert {_RUN_ID}",
        "issued_date": _ISSUED,
        **kwargs,
    }
    import json
    r = client.post(
        BASE_CERTS,
        data={"body": json.dumps(body)},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── TestCertificateCRUD ───────────────────────────────────────────────────────


class TestCertificateCRUD:
    def test_create_minimal_fields(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        cert = _create_cert(client, h, emp_id)
        assert cert["id"] > 0
        assert cert["employee_id"] == emp_id
        assert cert["issued_date"] == _ISSUED
        assert cert["expiry_date"] is None
        assert cert["has_file"] is False

    def test_create_with_expiry_date(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        cert = _create_cert(client, h, emp_id, expiry_date=_EXPIRY_OK)
        assert cert["expiry_date"] == _EXPIRY_OK
        assert cert["expiry_status"] == "valid"

    def test_create_with_related_course(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        course = _make_course(client, h, suffix="C1")
        cert = _create_cert(client, h, emp_id, related_course_id=course["id"])
        assert cert["related_course_id"] == course["id"]
        assert cert["related_course_name"] == course["name"]

    def test_create_expiry_before_issued_returns_422(self, client: TestClient):
        import json
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        body = {
            "employee_id": emp_id,
            "certificate_name": f"BadCert {_RUN_ID}",
            "issued_date": _ISSUED,
            "expiry_date": str(_TODAY - timedelta(days=100)),  # before issued
        }
        r = client.post(BASE_CERTS, data={"body": json.dumps(body)}, headers=h)
        assert r.status_code == 422

    def test_get_certificate(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        cert = _create_cert(client, h, emp_id)
        r = client.get(f"{BASE_CERTS}/{cert['id']}", headers=h)
        assert r.status_code == 200
        assert r.json()["id"] == cert["id"]

    def test_get_nonexistent_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.get(f"{BASE_CERTS}/999999", headers=h)
        assert r.status_code == 404

    def test_update_certificate(self, client: TestClient):
        import json
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        cert = _create_cert(client, h, emp_id)
        new_name = f"Updated {_RUN_ID}"
        r = client.put(
            f"{BASE_CERTS}/{cert['id']}",
            data={"body": json.dumps({"certificate_name": new_name})},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["certificate_name"] == new_name

    def test_delete_certificate(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        cert = _create_cert(client, h, emp_id)
        r = client.delete(f"{BASE_CERTS}/{cert['id']}", headers=h)
        assert r.status_code == 204
        r2 = client.get(f"{BASE_CERTS}/{cert['id']}", headers=h)
        assert r2.status_code == 404

    def test_delete_nonexistent_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.delete(f"{BASE_CERTS}/999999", headers=h)
        assert r.status_code == 404


# ── TestExpiryStatus ──────────────────────────────────────────────────────────


class TestExpiryStatus:
    def test_no_expiry_status(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        cert = _create_cert(client, h, emp_id)
        assert cert["expiry_status"] == "no_expiry"
        assert cert["days_until_expiry"] is None

    def test_valid_status(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        cert = _create_cert(client, h, emp_id, expiry_date=_EXPIRY_OK)
        assert cert["expiry_status"] == "valid"
        assert cert["days_until_expiry"] is not None
        assert cert["days_until_expiry"] > 30

    def test_expiring_soon_status(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        cert = _create_cert(client, h, emp_id, expiry_date=_EXPIRY_SOON)
        assert cert["expiry_status"] == "expiring_soon"
        assert 0 < cert["days_until_expiry"] <= 30

    def test_expired_status(self, client: TestClient):
        import json
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        # expired: issued even earlier so expiry > issued still
        issued_old = str(_TODAY - timedelta(days=30))
        expiry_old = str(_TODAY - timedelta(days=5))
        body = {
            "employee_id": emp_id,
            "certificate_name": f"Expired {_RUN_ID}",
            "issued_date": issued_old,
            "expiry_date": expiry_old,
        }
        r = client.post(BASE_CERTS, data={"body": json.dumps(body)}, headers=h)
        assert r.status_code == 201, r.text
        cert = r.json()
        assert cert["expiry_status"] == "expired"
        assert cert["days_until_expiry"] is None


# ── TestCertificateList ───────────────────────────────────────────────────────


class TestCertificateList:
    def test_list_returns_items(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_cert(client, h, emp_id)
        r = client.get(BASE_CERTS, headers=h)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_filter_by_employee_id(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_cert(client, h, emp_id)
        r = client.get(BASE_CERTS, headers=h, params={"employee_id": emp_id})
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(i["employee_id"] == emp_id for i in items)

    def test_filter_by_expiry_status_no_expiry(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_cert(client, h, emp_id)  # no expiry
        r = client.get(BASE_CERTS, headers=h, params={"expiry_status": "no_expiry"})
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(i["expiry_status"] == "no_expiry" for i in items)

    def test_filter_by_expiry_status_valid(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_cert(client, h, emp_id, expiry_date=_EXPIRY_OK)
        r = client.get(BASE_CERTS, headers=h, params={"expiry_status": "valid"})
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(i["expiry_status"] == "valid" for i in items)

    def test_filter_by_from_issued(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_cert(client, h, emp_id)
        cutoff = str(_TODAY - timedelta(days=30))
        r = client.get(BASE_CERTS, headers=h, params={"from_issued": cutoff})
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(i["issued_date"] >= cutoff for i in items)

    def test_search_by_cert_name(self, client: TestClient):
        import json
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        unique_name = f"SearchCert_{_RUN_ID}"
        body = {
            "employee_id": emp_id,
            "certificate_name": unique_name,
            "issued_date": _ISSUED,
        }
        client.post(BASE_CERTS, data={"body": json.dumps(body)}, headers=h)
        r = client.get(BASE_CERTS, headers=h, params={"search": unique_name[:10]})
        assert r.status_code == 200
        items = r.json()["items"]
        assert any(i["certificate_name"] == unique_name for i in items)

    def test_pagination(self, client: TestClient):
        h = _admin(client)
        r = client.get(BASE_CERTS, headers=h, params={"page": 1, "page_size": 2})
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) <= 2


# ── TestEmployeeCertificateHistory ───────────────────────────────────────────


class TestEmployeeCertificateHistory:
    def test_get_employee_certs_returns_list(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_cert(client, h, emp_id)
        r = client.get(f"/api/v1/employees/{emp_id}/training/certificates", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert all(i["employee_id"] == emp_id for i in data)

    def test_get_employee_certs_nonexistent_employee_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.get("/api/v1/employees/999999/training/certificates", headers=h)
        assert r.status_code == 404

    def test_employee_certs_ordered_by_issued_desc(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        import json
        for days_ago in [100, 50, 10]:
            body = {
                "employee_id": emp_id,
                "certificate_name": f"Order {_RUN_ID} {days_ago}",
                "issued_date": str(_TODAY - timedelta(days=days_ago)),
            }
            client.post(BASE_CERTS, data={"body": json.dumps(body)}, headers=h)
        r = client.get(f"/api/v1/employees/{emp_id}/training/certificates", headers=h)
        assert r.status_code == 200
        items = r.json()
        dates = [i["issued_date"] for i in items]
        assert dates == sorted(dates, reverse=True)


# ── TestFileUpload ────────────────────────────────────────────────────────────


class TestFileUpload:
    def test_create_with_file(self, client: TestClient):
        import json
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        body = {
            "employee_id": emp_id,
            "certificate_name": f"File Cert {_RUN_ID}",
            "issued_date": _ISSUED,
        }
        fake_file = io.BytesIO(b"fake pdf content")
        r = client.post(
            BASE_CERTS,
            data={"body": json.dumps(body)},
            files={"file": ("test.pdf", fake_file, "application/pdf")},
            headers=h,
        )
        assert r.status_code == 201, r.text
        cert = r.json()
        assert cert["has_file"] is True
        assert cert["file_name"] == "test.pdf"
        assert cert["file_size"] > 0

    def test_update_replaces_file(self, client: TestClient):
        import json
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        # Create with file
        body = {
            "employee_id": emp_id,
            "certificate_name": f"ReplaceFile {_RUN_ID}",
            "issued_date": _ISSUED,
        }
        old_file = io.BytesIO(b"old file")
        r1 = client.post(
            BASE_CERTS,
            data={"body": json.dumps(body)},
            files={"file": ("old.pdf", old_file, "application/pdf")},
            headers=h,
        )
        cert = r1.json()
        # Update with new file
        new_file = io.BytesIO(b"new file content longer")
        r2 = client.put(
            f"{BASE_CERTS}/{cert['id']}",
            data={"body": json.dumps({})},
            files={"file": ("new.pdf", new_file, "application/pdf")},
            headers=h,
        )
        assert r2.status_code == 200, r2.text
        updated = r2.json()
        assert updated["file_name"] == "new.pdf"

    def test_download_without_file_returns_404(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        cert = _create_cert(client, h, emp_id)  # no file
        r = client.get(f"{BASE_CERTS}/{cert['id']}/download", headers=h)
        assert r.status_code == 404
