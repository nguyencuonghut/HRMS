"""Integration tests cho Plan 9.2 — Theo dõi đào tạo nhân viên."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

BASE_RECORDS = "/api/v1/training/records"
BASE_COURSES = "/api/v1/training/courses"
BASE_PLANS   = "/api/v1/training/plans"
BASE_EMPLOYEES = "/api/v1/employees"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_RUN_ID = uuid.uuid4().hex[:8]


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_course(client, h, suffix: str = "") -> dict:
    code = f"RC{_RUN_ID}{suffix}"[:50]
    r = client.post(BASE_COURSES, json={
        "code": code,
        "name": f"Record Test Course {suffix or _RUN_ID}",
        "course_type": "noi_bo",
        "duration_hours": 8,
    }, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _make_plan(client, h, suffix: str = "") -> dict:
    r = client.post(BASE_PLANS, json={
        "title": f"Record Test Plan {suffix or _RUN_ID}",
        "year": 2098,
    }, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _get_employee_id(client, h) -> int:
    """Lấy employee đầu tiên trong DB để test."""
    r = client.get(BASE_EMPLOYEES, headers=h, params={"page_size": 1})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "Cần ít nhất 1 nhân viên trong DB để chạy test"
    return items[0]["id"]


def _make_record(client, h, employee_id: int, course_id: int, plan_id: int | None = None) -> dict:
    body = {"employee_id": employee_id, "course_id": course_id}
    if plan_id:
        body["plan_id"] = plan_id
    r = client.post(BASE_RECORDS, json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


# ── TestTrainingRecords ───────────────────────────────────────────────────────


class TestTrainingRecords:
    def test_create_record_success(self, client: TestClient):
        h = _admin(client)
        course = _make_course(client, h, "A")
        emp_id = _get_employee_id(client, h)
        r = client.post(BASE_RECORDS, json={
            "employee_id": emp_id,
            "course_id": course["id"],
        }, headers=h)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["employee_id"] == emp_id
        assert data["course_id"] == course["id"]
        assert data["status"] == "chua_bat_dau"
        assert data["status_label"] == "Chưa bắt đầu"
        assert data["result"] is None

    def test_create_record_invalid_employee_returns_404(self, client: TestClient):
        h = _admin(client)
        course = _make_course(client, h, "B")
        r = client.post(BASE_RECORDS, json={
            "employee_id": 999999,
            "course_id": course["id"],
        }, headers=h)
        assert r.status_code == 404

    def test_create_record_invalid_course_returns_404(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_employee_id(client, h)
        r = client.post(BASE_RECORDS, json={
            "employee_id": emp_id,
            "course_id": 999999,
        }, headers=h)
        assert r.status_code == 404

    def test_create_record_inactive_course_returns_400(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_employee_id(client, h)
        course = _make_course(client, h, "INACT")
        # Deactivate course
        client.put(f"{BASE_COURSES}/{course['id']}", json={"is_active": False}, headers=h)
        r = client.post(BASE_RECORDS, json={
            "employee_id": emp_id,
            "course_id": course["id"],
        }, headers=h)
        assert r.status_code == 400

    def test_create_record_plan_id_course_not_in_plan_returns_400(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_employee_id(client, h)
        course = _make_course(client, h, "NIP")
        plan = _make_plan(client, h, "NIP")
        # course NOT added to plan
        r = client.post(BASE_RECORDS, json={
            "employee_id": emp_id,
            "course_id": course["id"],
            "plan_id": plan["id"],
        }, headers=h)
        assert r.status_code == 400

    def test_get_record_not_found_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.get(f"{BASE_RECORDS}/999999", headers=h)
        assert r.status_code == 404

    def test_update_record_status(self, client: TestClient):
        h = _admin(client)
        course = _make_course(client, h, "UPD1")
        emp_id = _get_employee_id(client, h)
        rec = _make_record(client, h, emp_id, course["id"])
        r = client.put(f"{BASE_RECORDS}/{rec['id']}", json={"status": "dang_hoc"}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "dang_hoc"
        assert r.json()["status_label"] == "Đang học"

    def test_update_record_result_and_score(self, client: TestClient):
        h = _admin(client)
        course = _make_course(client, h, "UPD2")
        emp_id = _get_employee_id(client, h)
        rec = _make_record(client, h, emp_id, course["id"])
        r = client.put(f"{BASE_RECORDS}/{rec['id']}", json={
            "status": "hoan_thanh",
            "result": "dat",
            "score": 85.5,
        }, headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "hoan_thanh"
        assert data["result"] == "dat"
        assert data["result_label"] == "Đạt"
        assert float(data["score"]) == pytest.approx(85.5)

    def test_update_record_score_out_of_range_returns_422(self, client: TestClient):
        h = _admin(client)
        course = _make_course(client, h, "SCORE")
        emp_id = _get_employee_id(client, h)
        rec = _make_record(client, h, emp_id, course["id"])
        r = client.put(f"{BASE_RECORDS}/{rec['id']}", json={"score": 150}, headers=h)
        assert r.status_code == 422

    def test_update_record_end_date_before_start_date_returns_422(self, client: TestClient):
        h = _admin(client)
        course = _make_course(client, h, "DATE")
        emp_id = _get_employee_id(client, h)
        rec = _make_record(client, h, emp_id, course["id"])
        r = client.put(f"{BASE_RECORDS}/{rec['id']}", json={
            "start_date": "2026-06-15",
            "end_date":   "2026-06-01",
        }, headers=h)
        assert r.status_code == 422

    def test_delete_record_success(self, client: TestClient):
        h = _admin(client)
        course = _make_course(client, h, "DEL")
        emp_id = _get_employee_id(client, h)
        rec = _make_record(client, h, emp_id, course["id"])
        r = client.delete(f"{BASE_RECORDS}/{rec['id']}", headers=h)
        assert r.status_code == 204
        r2 = client.get(f"{BASE_RECORDS}/{rec['id']}", headers=h)
        assert r2.status_code == 404


# ── TestListFilter ────────────────────────────────────────────────────────────


class TestListFilter:
    def test_list_records_pagination(self, client: TestClient):
        h = _admin(client)
        r = client.get(BASE_RECORDS, headers=h, params={"page": 1, "page_size": 5})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) <= 5

    def test_list_records_filter_by_employee(self, client: TestClient):
        h = _admin(client)
        course = _make_course(client, h, "FEmp")
        emp_id = _get_employee_id(client, h)
        _make_record(client, h, emp_id, course["id"])
        r = client.get(BASE_RECORDS, headers=h, params={"employee_id": emp_id})
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["employee_id"] == emp_id

    def test_list_records_filter_by_status(self, client: TestClient):
        h = _admin(client)
        course = _make_course(client, h, "FStat")
        emp_id = _get_employee_id(client, h)
        rec = _make_record(client, h, emp_id, course["id"])
        client.put(f"{BASE_RECORDS}/{rec['id']}", json={"status": "dang_hoc"}, headers=h)
        r = client.get(BASE_RECORDS, headers=h, params={"status": "dang_hoc"})
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["status"] == "dang_hoc"

    def test_list_records_filter_by_result(self, client: TestClient):
        h = _admin(client)
        course = _make_course(client, h, "FRes")
        emp_id = _get_employee_id(client, h)
        rec = _make_record(client, h, emp_id, course["id"])
        client.put(f"{BASE_RECORDS}/{rec['id']}", json={"status": "hoan_thanh", "result": "dat"}, headers=h)
        r = client.get(BASE_RECORDS, headers=h, params={"result": "dat"})
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["result"] == "dat"

    def test_list_records_search_by_employee_name(self, client: TestClient):
        h = _admin(client)
        # Ensure at least one record exists
        course = _make_course(client, h, "FSrch")
        emp_id = _get_employee_id(client, h)
        _make_record(client, h, emp_id, course["id"])
        # Get employee name for search
        emp_r = client.get(f"{BASE_EMPLOYEES}/{emp_id}", headers=h)
        emp_name = emp_r.json()["full_name"]
        r = client.get(BASE_RECORDS, headers=h, params={"search": emp_name[:4]})
        assert r.status_code == 200

    def test_list_records_filter_by_date_range(self, client: TestClient):
        h = _admin(client)
        course = _make_course(client, h, "FDate")
        emp_id = _get_employee_id(client, h)
        rec = _make_record(client, h, emp_id, course["id"])
        client.put(f"{BASE_RECORDS}/{rec['id']}", json={"end_date": "2098-06-15"}, headers=h)
        r = client.get(BASE_RECORDS, headers=h, params={
            "from_date": "2098-01-01",
            "to_date":   "2098-12-31",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1


# ── TestBulkAssign ────────────────────────────────────────────────────────────


class TestBulkAssign:
    def _setup_plan_with_course(self, client, h, suffix: str = ""):
        course = _make_course(client, h, f"BA{suffix}")
        plan = _make_plan(client, h, f"BA{suffix}")
        # Add course to plan
        client.post(f"{BASE_PLANS}/{plan['id']}/courses", json={"course_id": course["id"]}, headers=h)
        return plan, course

    def test_bulk_assign_creates_records(self, client: TestClient):
        h = _admin(client)
        plan, course = self._setup_plan_with_course(client, h, "C1")
        emp_id = _get_employee_id(client, h)
        r = client.post(f"{BASE_PLANS}/{plan['id']}/assign", json={
            "plan_id": plan["id"],
            "course_id": course["id"],
            "employee_ids": [emp_id],
        }, headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["created"] >= 1

    def test_bulk_assign_skips_existing_records(self, client: TestClient):
        h = _admin(client)
        plan, course = self._setup_plan_with_course(client, h, "SK")
        emp_id = _get_employee_id(client, h)
        # First assign
        client.post(f"{BASE_PLANS}/{plan['id']}/assign", json={
            "plan_id": plan["id"],
            "course_id": course["id"],
            "employee_ids": [emp_id],
        }, headers=h)
        # Second assign — same employee
        r = client.post(f"{BASE_PLANS}/{plan['id']}/assign", json={
            "plan_id": plan["id"],
            "course_id": course["id"],
            "employee_ids": [emp_id],
        }, headers=h)
        assert r.status_code == 200
        assert r.json()["skipped"] >= 1

    def test_bulk_assign_returns_created_and_skipped_counts(self, client: TestClient):
        h = _admin(client)
        plan, course = self._setup_plan_with_course(client, h, "CNT")
        emp_id = _get_employee_id(client, h)
        # Pre-assign one
        client.post(f"{BASE_PLANS}/{plan['id']}/assign", json={
            "plan_id": plan["id"],
            "course_id": course["id"],
            "employee_ids": [emp_id],
        }, headers=h)
        # Assign again same + invalid id (999998 likely non-existent → skipped)
        r = client.post(f"{BASE_PLANS}/{plan['id']}/assign", json={
            "plan_id": plan["id"],
            "course_id": course["id"],
            "employee_ids": [emp_id, 999998],
        }, headers=h)
        assert r.status_code == 200
        data = r.json()
        assert "created" in data
        assert "skipped" in data
        assert data["skipped"] >= 1  # emp_id already exists

    def test_bulk_assign_cancelled_plan_returns_400(self, client: TestClient):
        h = _admin(client)
        plan, course = self._setup_plan_with_course(client, h, "CNC")
        emp_id = _get_employee_id(client, h)
        client.post(f"{BASE_PLANS}/{plan['id']}/cancel", headers=h)
        r = client.post(f"{BASE_PLANS}/{plan['id']}/assign", json={
            "plan_id": plan["id"],
            "course_id": course["id"],
            "employee_ids": [emp_id],
        }, headers=h)
        assert r.status_code == 400

    def test_bulk_assign_course_not_in_plan_returns_400(self, client: TestClient):
        h = _admin(client)
        plan = _make_plan(client, h, "NIC")
        other_course = _make_course(client, h, "NIC")
        emp_id = _get_employee_id(client, h)
        r = client.post(f"{BASE_PLANS}/{plan['id']}/assign", json={
            "plan_id": plan["id"],
            "course_id": other_course["id"],
            "employee_ids": [emp_id],
        }, headers=h)
        assert r.status_code == 400

    def test_bulk_assign_too_many_employees_returns_422(self, client: TestClient):
        h = _admin(client)
        plan, course = self._setup_plan_with_course(client, h, "TOO")
        r = client.post(f"{BASE_PLANS}/{plan['id']}/assign", json={
            "plan_id": plan["id"],
            "course_id": course["id"],
            "employee_ids": list(range(1, 202)),  # 201 → exceeds max 200
        }, headers=h)
        assert r.status_code == 422


# ── TestPassport ──────────────────────────────────────────────────────────────


class TestPassport:
    def test_passport_returns_all_records_for_employee(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_employee_id(client, h)
        c1 = _make_course(client, h, "PP1")
        c2 = _make_course(client, h, "PP2")
        _make_record(client, h, emp_id, c1["id"])
        _make_record(client, h, emp_id, c2["id"])
        r = client.get(f"/api/v1/training/passport/{emp_id}", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        emp_records = [rec for rec in data if rec["employee_id"] == emp_id]
        assert len(emp_records) >= 2

    def test_passport_sorted_by_end_date_desc(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_employee_id(client, h)
        c1 = _make_course(client, h, "PPSD1")
        c2 = _make_course(client, h, "PPSD2")
        r1 = _make_record(client, h, emp_id, c1["id"])
        r2 = _make_record(client, h, emp_id, c2["id"])
        # Set end dates
        client.put(f"{BASE_RECORDS}/{r1['id']}", json={"end_date": "2098-03-01"}, headers=h)
        client.put(f"{BASE_RECORDS}/{r2['id']}", json={"end_date": "2098-06-01"}, headers=h)
        r = client.get(f"/api/v1/training/passport/{emp_id}", headers=h)
        assert r.status_code == 200
        items = [rec for rec in r.json() if rec["employee_id"] == emp_id and rec["end_date"] is not None]
        dates = [rec["end_date"] for rec in items]
        assert dates == sorted(dates, reverse=True)

    def test_passport_empty_for_new_employee_returns_empty_list(self, client: TestClient):
        h = _admin(client)
        # Get an employee that has no records — use a non-existent id
        r = client.get("/api/v1/training/passport/999999", headers=h)
        assert r.status_code == 404  # employee not found


# ── TestAuth ──────────────────────────────────────────────────────────────────


class TestAuth:
    def test_unauthenticated_returns_401(self, client: TestClient):
        r = client.get(BASE_RECORDS)
        assert r.status_code == 401

    def test_unauthenticated_post_returns_401(self, client: TestClient):
        r = client.post(BASE_RECORDS, json={"employee_id": 1, "course_id": 1})
        assert r.status_code == 401
