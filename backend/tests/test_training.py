"""Integration tests cho Plan 9.1 — Đào tạo (Slice 1 + 2).

Covers:
  - CourseCreate / List / Get / Update / Delete
  - PlanCreate / List / Get / Update / Delete
  - Plan approve / cancel
  - Plan-course add / update / remove
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

BASE_COURSES = "/api/v1/training/courses"
BASE_PLANS   = "/api/v1/training/plans"
_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_RUN_ID = uuid.uuid4().hex[:8]


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Course tests ──────────────────────────────────────────────────────────────


class TestCourses:
    def test_create_course_ok(self, client: TestClient):
        h = _admin(client)
        code = f"C{_RUN_ID[:6]}"
        r = client.post(BASE_COURSES, json={
            "code": code,
            "name": f"Khóa học {_RUN_ID}",
            "course_type": "noi_bo",
            "duration_hours": 8,
            "is_mandatory": False,
        }, headers=h)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["code"] == code
        assert data["course_type"] == "noi_bo"
        assert data["course_type_label"] == "Nội bộ"
        assert data["is_active"] is True

    def test_create_course_duplicate_code(self, client: TestClient):
        h = _admin(client)
        code = f"DUP{_RUN_ID[:4]}"
        client.post(BASE_COURSES, json={"code": code, "name": "First", "course_type": "online"}, headers=h)
        r = client.post(BASE_COURSES, json={"code": code, "name": "Second", "course_type": "online"}, headers=h)
        assert r.status_code == 400

    def test_list_courses(self, client: TestClient):
        h = _admin(client)
        r = client.get(BASE_COURSES, headers=h)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_courses_filter_type(self, client: TestClient):
        h = _admin(client)
        r = client.get(BASE_COURSES, params={"course_type": "noi_bo"}, headers=h)
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["course_type"] == "noi_bo"

    def test_get_course(self, client: TestClient):
        h = _admin(client)
        # Create then get
        code = f"GET{_RUN_ID[:5]}"
        created = client.post(BASE_COURSES, json={"code": code, "name": "Get Test", "course_type": "ben_ngoai"}, headers=h).json()
        r = client.get(f"{BASE_COURSES}/{created['id']}", headers=h)
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]

    def test_get_course_not_found(self, client: TestClient):
        h = _admin(client)
        r = client.get(f"{BASE_COURSES}/999999", headers=h)
        assert r.status_code == 404

    def test_update_course(self, client: TestClient):
        h = _admin(client)
        code = f"UPD{_RUN_ID[:5]}"
        created = client.post(BASE_COURSES, json={"code": code, "name": "Before Update", "course_type": "online"}, headers=h).json()
        r = client.put(f"{BASE_COURSES}/{created['id']}", json={"name": "After Update", "is_active": False}, headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "After Update"
        assert data["is_active"] is False

    def test_delete_course_hard(self, client: TestClient):
        h = _admin(client)
        code = f"DEL{_RUN_ID[:5]}"
        created = client.post(BASE_COURSES, json={"code": code, "name": "To Delete", "course_type": "online"}, headers=h).json()
        r = client.delete(f"{BASE_COURSES}/{created['id']}", headers=h)
        assert r.status_code == 204
        # Verify gone
        r2 = client.get(f"{BASE_COURSES}/{created['id']}", headers=h)
        assert r2.status_code == 404


# ── Plan tests ────────────────────────────────────────────────────────────────


class TestPlans:
    def _create_course(self, client, h):
        code = f"PC{_RUN_ID[:6]}{uuid.uuid4().hex[:4]}"
        r = client.post(BASE_COURSES, json={"code": code, "name": f"Plan Course {code}", "course_type": "noi_bo"}, headers=h)
        assert r.status_code == 201
        return r.json()

    def test_create_plan_ok(self, client: TestClient):
        h = _admin(client)
        r = client.post(BASE_PLANS, json={"title": f"KH {_RUN_ID}", "year": 2096}, headers=h)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["status"] == "draft"
        assert data["status_label"] == "Dự thảo"
        assert data["year"] == 2096
        assert data["course_count"] == 0

    def test_list_plans(self, client: TestClient):
        h = _admin(client)
        r = client.get(BASE_PLANS, headers=h)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    def test_get_plan_detail(self, client: TestClient):
        h = _admin(client)
        created = client.post(BASE_PLANS, json={"title": "Detail test", "year": 2095}, headers=h).json()
        r = client.get(f"{BASE_PLANS}/{created['id']}", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert "courses" in data
        assert data["courses"] == []

    def test_update_plan(self, client: TestClient):
        h = _admin(client)
        created = client.post(BASE_PLANS, json={"title": "Old Title", "year": 2094}, headers=h).json()
        r = client.put(f"{BASE_PLANS}/{created['id']}", json={"title": "New Title"}, headers=h)
        assert r.status_code == 200
        assert r.json()["title"] == "New Title"

    def test_approve_plan(self, client: TestClient):
        h = _admin(client)
        created = client.post(BASE_PLANS, json={"title": "To Approve", "year": 2093}, headers=h).json()
        r = client.post(f"{BASE_PLANS}/{created['id']}/approve", headers=h)
        assert r.status_code == 200
        assert r.json()["status"] == "approved"
        assert r.json()["status_label"] == "Đã duyệt"

    def test_approve_already_approved_fails(self, client: TestClient):
        h = _admin(client)
        created = client.post(BASE_PLANS, json={"title": "Double Approve", "year": 2092}, headers=h).json()
        client.post(f"{BASE_PLANS}/{created['id']}/approve", headers=h)
        r = client.post(f"{BASE_PLANS}/{created['id']}/approve", headers=h)
        assert r.status_code == 400

    def test_cancel_plan(self, client: TestClient):
        h = _admin(client)
        created = client.post(BASE_PLANS, json={"title": "To Cancel", "year": 2091}, headers=h).json()
        r = client.post(f"{BASE_PLANS}/{created['id']}/cancel", headers=h)
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    def test_delete_draft_plan(self, client: TestClient):
        h = _admin(client)
        created = client.post(BASE_PLANS, json={"title": "To Delete Draft", "year": 2090}, headers=h).json()
        r = client.delete(f"{BASE_PLANS}/{created['id']}", headers=h)
        assert r.status_code == 204

    def test_delete_approved_plan_fails(self, client: TestClient):
        h = _admin(client)
        created = client.post(BASE_PLANS, json={"title": "Approved No Delete", "year": 2089}, headers=h).json()
        client.post(f"{BASE_PLANS}/{created['id']}/approve", headers=h)
        r = client.delete(f"{BASE_PLANS}/{created['id']}", headers=h)
        assert r.status_code == 400


# ── Plan-course tests ─────────────────────────────────────────────────────────


class TestPlanCourses:
    def _setup(self, client, h):
        code = f"TPC{uuid.uuid4().hex[:6]}"
        course = client.post(BASE_COURSES, json={"code": code, "name": f"TPC {code}", "course_type": "online"}, headers=h).json()
        plan = client.post(BASE_PLANS, json={"title": f"Plan {code}", "year": 2088}, headers=h).json()
        return plan["id"], course["id"]

    def test_add_course_to_plan(self, client: TestClient):
        h = _admin(client)
        plan_id, course_id = self._setup(client, h)
        r = client.post(f"{BASE_PLANS}/{plan_id}/courses", json={"course_id": course_id, "target_count": 10}, headers=h)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["course_id"] == course_id
        assert data["target_count"] == 10

    def test_add_duplicate_course_fails(self, client: TestClient):
        h = _admin(client)
        plan_id, course_id = self._setup(client, h)
        client.post(f"{BASE_PLANS}/{plan_id}/courses", json={"course_id": course_id}, headers=h)
        r = client.post(f"{BASE_PLANS}/{plan_id}/courses", json={"course_id": course_id}, headers=h)
        assert r.status_code == 409

    def test_list_plan_courses(self, client: TestClient):
        h = _admin(client)
        plan_id, course_id = self._setup(client, h)
        client.post(f"{BASE_PLANS}/{plan_id}/courses", json={"course_id": course_id}, headers=h)
        r = client.get(f"{BASE_PLANS}/{plan_id}/courses", headers=h)
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_update_plan_course(self, client: TestClient):
        h = _admin(client)
        plan_id, course_id = self._setup(client, h)
        client.post(f"{BASE_PLANS}/{plan_id}/courses", json={"course_id": course_id, "target_count": 5}, headers=h)
        r = client.put(f"{BASE_PLANS}/{plan_id}/courses/{course_id}", json={"target_count": 15, "note": "Updated"}, headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["target_count"] == 15
        assert data["note"] == "Updated"

    def test_remove_course_from_plan(self, client: TestClient):
        h = _admin(client)
        plan_id, course_id = self._setup(client, h)
        client.post(f"{BASE_PLANS}/{plan_id}/courses", json={"course_id": course_id}, headers=h)
        r = client.delete(f"{BASE_PLANS}/{plan_id}/courses/{course_id}", headers=h)
        assert r.status_code == 204
        # Verify removed
        r2 = client.get(f"{BASE_PLANS}/{plan_id}/courses", headers=h)
        assert r2.json() == []

    def test_course_soft_delete_when_in_plan(self, client: TestClient):
        """Course used in a plan should be soft-deleted (deactivated), not hard-deleted."""
        h = _admin(client)
        plan_id, course_id = self._setup(client, h)
        client.post(f"{BASE_PLANS}/{plan_id}/courses", json={"course_id": course_id}, headers=h)
        r = client.delete(f"{BASE_COURSES}/{course_id}", headers=h)
        assert r.status_code == 204
        # Course still exists but is inactive
        r2 = client.get(f"{BASE_COURSES}/{course_id}", headers=h)
        assert r2.status_code == 200
        assert r2.json()["is_active"] is False
