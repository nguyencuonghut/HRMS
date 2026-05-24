"""Integration tests cho Plan 10.3 — Liên kết kết quả đánh giá."""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

BASE_KPI      = "/api/v1/performance/kpi"
BASE_REVIEWS  = "/api/v1/performance/yearly-reviews"
BASE_COURSES  = "/api/v1/training/courses"
BASE_EMP      = "/api/v1/employees"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_RUN_ID = uuid.uuid4().hex[:8]

_TEST_YEAR_KPI    = 2090
_TEST_YEAR_REVIEW = 2091


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_emp_id(client: TestClient, h: dict) -> int:
    items = client.get(BASE_EMP, headers=h, params={"page_size": 1}).json()["items"]
    assert items, "Cần ít nhất 1 nhân viên trong DB"
    return items[0]["id"]


def _get_reward_type_id(client: TestClient, h: dict) -> int:
    r = client.get("/api/v1/rewards/types", headers=h)
    assert r.status_code == 200
    items = r.json()
    assert items, "Cần ít nhất 1 loại khen thưởng trong DB"
    # Prefer non-monetary to avoid amount requirement
    for item in items:
        if not item["is_monetary"] and item["is_active"]:
            return item["id"]
    for item in items:
        if item["is_active"]:
            return item["id"]
    pytest.skip("Không có loại khen thưởng active trong DB")


_course_counter = 0

def _make_course(client: TestClient, h: dict) -> dict:
    global _course_counter
    _course_counter += 1
    code = f"LK{_RUN_ID}{_course_counter}"[:50]
    r = client.post(BASE_COURSES, json={
        "code": code,
        "name": f"Link Test Course {_RUN_ID} #{_course_counter}",
        "course_type": "noi_bo",
        "duration_hours": 8,
    }, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _seed_kpi(client: TestClient, h: dict, emp_id: int, year: int, scores: list):
    # Cleanup existing
    r = client.get(BASE_KPI, headers=h, params={"year": year, "page_size": 50})
    for item in r.json().get("items", []):
        if item["employee_id"] == emp_id:
            client.delete(f"{BASE_KPI}/{item['id']}", headers=h)
    for month, score in scores:
        r = client.post(BASE_KPI, json={"employee_id": emp_id, "year": year, "month": month, "score": score}, headers=h)
        assert r.status_code == 201, r.text


def _create_review(client: TestClient, h: dict, emp_id: int, year: int, rating: str = "tot") -> dict:
    # Cleanup existing review
    r = client.get(BASE_REVIEWS, headers=h, params={"year": year, "page_size": 50})
    for item in r.json().get("items", []):
        if item["employee_id"] == emp_id:
            client.delete(f"{BASE_REVIEWS}/{item['id']}", headers=h)
    r = client.post(BASE_REVIEWS, json={"employee_id": emp_id, "year": year, "rating": rating}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


# ── TestEmployeeHistory ───────────────────────────────────────────────────────


class TestEmployeeHistory:
    def test_get_kpi_history_returns_correct_employee(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _seed_kpi(client, h, emp_id, _TEST_YEAR_KPI, [(1, 88.0), (2, 92.0)])

        r = client.get(f"/api/v1/employees/{emp_id}/performance/kpi", headers=h)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 2
        assert all(i["employee_id"] == emp_id for i in items)

    def test_get_kpi_history_filter_by_year(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _seed_kpi(client, h, emp_id, _TEST_YEAR_KPI, [(3, 75.0)])

        r = client.get(
            f"/api/v1/employees/{emp_id}/performance/kpi",
            headers=h,
            params={"year": _TEST_YEAR_KPI},
        )
        assert r.status_code == 200, r.text
        items = r.json()
        assert all(i["year"] == _TEST_YEAR_KPI for i in items)

    def test_get_review_history_includes_avg_score(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _seed_kpi(client, h, emp_id, _TEST_YEAR_REVIEW, [(1, 96.0), (2, 98.0)])
        _create_review(client, h, emp_id, _TEST_YEAR_REVIEW, "tot")

        r = client.get(f"/api/v1/employees/{emp_id}/performance/reviews", headers=h)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        found = [i for i in items if i["year"] == _TEST_YEAR_REVIEW]
        assert found, f"Không tìm thấy review năm {_TEST_YEAR_REVIEW}"
        assert found[0]["avg_score"] is not None
        assert abs(float(found[0]["avg_score"]) - 97.0) < 0.1

    def test_nonexistent_employee_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.get("/api/v1/employees/999999/performance/kpi", headers=h)
        assert r.status_code == 404

    def test_nonexistent_employee_reviews_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.get("/api/v1/employees/999999/performance/reviews", headers=h)
        assert r.status_code == 404


# ── TestCreateFromReview ──────────────────────────────────────────────────────


class TestCreateFromReview:
    def test_create_reward_from_review_sets_source_review_id(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        review = _create_review(client, h, emp_id, 2092, "tot")
        rt_id = _get_reward_type_id(client, h)

        r = client.post(
            f"{BASE_REVIEWS}/{review['id']}/create-reward",
            json={"reward_type_id": rt_id, "decision_date": "2092-12-31"},
            headers=h,
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["source_review_id"] == review["id"]
        assert data["employee_id"] == emp_id

    def test_create_training_from_review_sets_source_review_id(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        review = _create_review(client, h, emp_id, 2093, "can_cai_thien")
        course = _make_course(client, h)

        r = client.post(
            f"{BASE_REVIEWS}/{review['id']}/create-training",
            json={"course_id": course["id"]},
            headers=h,
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["source_review_id"] == review["id"]
        assert data["employee_id"] == emp_id

    def test_create_from_nonexistent_review_returns_404(self, client: TestClient):
        h = _admin(client)
        rt_id = _get_reward_type_id(client, h)
        r = client.post(
            f"{BASE_REVIEWS}/999999/create-reward",
            json={"reward_type_id": rt_id, "decision_date": "2099-01-01"},
            headers=h,
        )
        assert r.status_code == 404

    def test_reward_prefills_employee_id_from_review(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        review = _create_review(client, h, emp_id, 2094, "dat")
        rt_id = _get_reward_type_id(client, h)

        r = client.post(
            f"{BASE_REVIEWS}/{review['id']}/create-reward",
            json={"reward_type_id": rt_id, "decision_date": "2094-12-31"},
            headers=h,
        )
        assert r.status_code == 201, r.text
        assert r.json()["employee_id"] == emp_id

    def test_training_prefills_note_from_review_year(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        review = _create_review(client, h, emp_id, 2095, "can_cai_thien")
        course = _make_course(client, h)

        r = client.post(
            f"{BASE_REVIEWS}/{review['id']}/create-training",
            json={"course_id": course["id"]},
            headers=h,
        )
        assert r.status_code == 201, r.text
        note = r.json()["note"]
        assert "2095" in note

    def test_create_training_nonexistent_review_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.post(
            f"{BASE_REVIEWS}/999999/create-training",
            json={"course_id": 1},
            headers=h,
        )
        assert r.status_code == 404
