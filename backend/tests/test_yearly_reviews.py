"""Integration tests cho Plan 10.2 — Đánh giá Cuối năm."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

BASE_KPI     = "/api/v1/performance/kpi"
BASE_REVIEWS = "/api/v1/performance/yearly-reviews"
BASE_SUMMARY = "/api/v1/performance/yearly-summary"
BASE_EMP     = "/api/v1/employees"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_RUN_ID = uuid.uuid4().hex[:8]

_BASE        = 2000 + int(_RUN_ID[:2], 16) % 60   # 2000–2059 (giới hạn để +16 ≤ 2075 ≤ 2100)
_YEAR        = _BASE        # TestYearlyReviewCRUD dùng _YEAR đến _YEAR+7
_LIST_YEAR   = _BASE + 8    # TestYearlyReviewList dùng _LIST_YEAR đến _LIST_YEAR+4 (max 2071)

# Summary rating tests — mỗi test dùng năm hoàn toàn riêng + cleanup trước seed
_YEAR_AVG_CALC      = _BASE + 13
_YEAR_COUNT         = _BASE + 14
_YEAR_XUAT_SAC      = _BASE + 15
_YEAR_TOT           = _BASE + 16
_YEAR_DAT           = _BASE + 17
_YEAR_CAN_CAI_THIEN = _BASE + 18
_YEAR_EMPTY         = _BASE + 19   # test_avg_score_none + test_has_review_flag
_YEAR_DISCIPLINE    = _BASE + 20   # test_discipline_overrides_rating


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


def _cleanup_kpi_year(client: TestClient, h: dict, emp_id: int, year: int):
    """Xóa toàn bộ KPI của emp_id trong năm year để đảm bảo trạng thái sạch."""
    r = client.get(BASE_KPI, headers=h, params={"year": year, "page_size": 50})
    for item in r.json().get("items", []):
        if item["employee_id"] == emp_id:
            client.delete(f"{BASE_KPI}/{item['id']}", headers=h)


def _seed_kpi(client: TestClient, h: dict, emp_id: int, year: int, scores: list[tuple[int, float]]):
    """Xóa dữ liệu cũ rồi tạo mới KPI tháng — đảm bảo avg tính đúng."""
    _cleanup_kpi_year(client, h, emp_id, year)
    for month, score in scores:
        r = client.post(BASE_KPI, json={"employee_id": emp_id, "year": year, "month": month, "score": score}, headers=h)
        assert r.status_code == 201, r.text


def _cleanup_review(client: TestClient, h: dict, emp_id: int, year: int):
    """Xóa đánh giá cuối năm của emp_id/year nếu tồn tại (tránh 409 từ previous runs)."""
    r = client.get(BASE_REVIEWS, headers=h, params={"year": year, "page_size": 50})
    for item in r.json().get("items", []):
        if item["employee_id"] == emp_id:
            client.delete(f"{BASE_REVIEWS}/{item['id']}", headers=h)


def _create_review(client: TestClient, h: dict, emp_id: int, year: int, rating: str = "tot", note: str = "") -> dict:
    _cleanup_review(client, h, emp_id, year)  # đảm bảo không có review cũ
    payload: dict = {"employee_id": emp_id, "year": year, "rating": rating}
    if note:
        payload["review_note"] = note
    r = client.post(BASE_REVIEWS, json=payload, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


# ── TestYearlySummary ─────────────────────────────────────────────────────────


class TestYearlySummary:
    def test_avg_score_calculated_from_monthly_kpi(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _seed_kpi(client, h, emp_id, _YEAR_AVG_CALC, [(1, 80.0), (2, 90.0)])
        r = client.get(f"{BASE_SUMMARY}/{emp_id}", headers=h, params={"year": _YEAR_AVG_CALC})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["avg_score"] is not None
        assert abs(float(data["avg_score"]) - 85.0) < 0.01

    def test_avg_score_none_when_no_kpi(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _cleanup_kpi_year(client, h, emp_id, _YEAR_EMPTY)
        r = client.get(f"{BASE_SUMMARY}/{emp_id}", headers=h, params={"year": _YEAR_EMPTY})
        assert r.status_code == 200, r.text
        assert r.json()["avg_score"] is None
        assert r.json()["suggested_rating"] is None

    def test_months_count_correct(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _seed_kpi(client, h, emp_id, _YEAR_COUNT, [(1, 70.0), (2, 75.0), (3, 80.0)])
        r = client.get(f"{BASE_SUMMARY}/{emp_id}", headers=h, params={"year": _YEAR_COUNT})
        assert r.status_code == 200
        assert r.json()["months_count"] == 3

    def test_suggested_rating_xuat_sac(self, client: TestClient):
        # avg > 100 là không thể (max score = 100) → avg = 100 phải ra "tot"
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _seed_kpi(client, h, emp_id, _YEAR_XUAT_SAC, [(1, 100.0), (2, 100.0)])
        r = client.get(f"{BASE_SUMMARY}/{emp_id}", headers=h, params={"year": _YEAR_XUAT_SAC})
        assert r.status_code == 200
        assert r.json()["suggested_rating"] == "tot"

    def test_suggested_rating_tot(self, client: TestClient):
        # avg = 96 ≥ 95 → "tot"
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _seed_kpi(client, h, emp_id, _YEAR_TOT, [(1, 95.0), (2, 97.0)])
        r = client.get(f"{BASE_SUMMARY}/{emp_id}", headers=h, params={"year": _YEAR_TOT})
        assert r.status_code == 200
        assert r.json()["suggested_rating"] == "tot"

    def test_suggested_rating_dat(self, client: TestClient):
        # avg = 88 (85 < 88 < 95) → "dat"
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _seed_kpi(client, h, emp_id, _YEAR_DAT, [(1, 87.0), (2, 89.0)])
        r = client.get(f"{BASE_SUMMARY}/{emp_id}", headers=h, params={"year": _YEAR_DAT})
        assert r.status_code == 200
        assert r.json()["suggested_rating"] == "dat"

    def test_suggested_rating_can_cai_thien(self, client: TestClient):
        # avg = 80 ≤ 85 → "can_cai_thien"
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _seed_kpi(client, h, emp_id, _YEAR_CAN_CAI_THIEN, [(1, 80.0)])
        r = client.get(f"{BASE_SUMMARY}/{emp_id}", headers=h, params={"year": _YEAR_CAN_CAI_THIEN})
        assert r.status_code == 200
        assert r.json()["suggested_rating"] == "can_cai_thien"

    def test_discipline_overrides_high_score(self, client: TestClient):
        import json
        # avg ≥ 95 nhưng có vi phạm kỷ luật → suggested_rating = "can_cai_thien"
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _seed_kpi(client, h, emp_id, _YEAR_DISCIPLINE, [(1, 96.0), (2, 98.0)])

        # Discipline endpoint dùng multipart/form-data với field "body" là JSON string
        disc_body = json.dumps({
            "employee_id": emp_id,
            "discipline_form": "khien_trach",
            "violation_date": f"{_YEAR_DISCIPLINE}-06-15",
            "effective_date": f"{_YEAR_DISCIPLINE}-06-15",
            "title": "Test discipline for rating override",
        })
        dr = client.post("/api/v1/disciplines", data={"body": disc_body}, headers=h)
        assert dr.status_code == 201, dr.text
        disc_id = dr.json()["id"]

        try:
            r = client.get(f"{BASE_SUMMARY}/{emp_id}", headers=h, params={"year": _YEAR_DISCIPLINE})
            assert r.status_code == 200
            data = r.json()
            assert data["has_discipline"] is True
            assert data["suggested_rating"] == "can_cai_thien"
        finally:
            client.delete(f"/api/v1/disciplines/{disc_id}", headers=h)

    def test_summary_404_for_nonexistent_employee(self, client: TestClient):
        h = _admin(client)
        r = client.get(f"{BASE_SUMMARY}/999999", headers=h, params={"year": _YEAR})
        assert r.status_code == 404

    def test_has_review_flag(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _cleanup_review(client, h, emp_id, _YEAR_EMPTY)
        _cleanup_kpi_year(client, h, emp_id, _YEAR_EMPTY)
        r = client.get(f"{BASE_SUMMARY}/{emp_id}", headers=h, params={"year": _YEAR_EMPTY})
        assert r.status_code == 200
        assert r.json()["has_review"] is False


# ── TestYearlyReviewCRUD ──────────────────────────────────────────────────────


class TestYearlyReviewCRUD:
    def test_create_review_success(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        review = _create_review(client, h, emp_id, _YEAR, "tot")
        assert review["id"] > 0
        assert review["rating"] == "tot"
        assert review["rating_label"] == "Tốt"
        assert review["employee_id"] == emp_id
        assert review["year"] == _YEAR

    def test_create_review_includes_avg_score(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        review = _create_review(client, h, emp_id, _YEAR + 6, "tot")
        r = client.get(f"{BASE_REVIEWS}/{review['id']}", headers=h)
        assert r.status_code == 200
        # avg_score field exists (may be None if no KPI seeded for that year)
        assert "avg_score" in r.json()

    def test_create_review_duplicate_returns_409(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_review(client, h, emp_id, _YEAR + 1, "dat")
        r = client.post(BASE_REVIEWS, json={"employee_id": emp_id, "year": _YEAR + 1, "rating": "tot"}, headers=h)
        assert r.status_code == 409, r.text

    def test_create_review_nonexistent_employee_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.post(BASE_REVIEWS, json={"employee_id": 999999, "year": _YEAR, "rating": "tot"}, headers=h)
        assert r.status_code == 404

    def test_get_review_by_id(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        review = _create_review(client, h, emp_id, _YEAR + 2, "xuat_sac")
        r = client.get(f"{BASE_REVIEWS}/{review['id']}", headers=h)
        assert r.status_code == 200
        assert r.json()["id"] == review["id"]

    def test_get_nonexistent_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.get(f"{BASE_REVIEWS}/999999", headers=h)
        assert r.status_code == 404

    def test_update_review_rating_and_note(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        review = _create_review(client, h, emp_id, _YEAR + 3, "dat")
        r = client.put(
            f"{BASE_REVIEWS}/{review['id']}",
            json={"rating": "xuat_sac", "review_note": "updated note"},
            headers=h,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["rating"] == "xuat_sac"
        assert data["review_note"] == "updated note"

    def test_delete_review(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        review = _create_review(client, h, emp_id, _YEAR + 4, "can_cai_thien")
        r = client.delete(f"{BASE_REVIEWS}/{review['id']}", headers=h)
        assert r.status_code == 204
        r2 = client.get(f"{BASE_REVIEWS}/{review['id']}", headers=h)
        assert r2.status_code == 404

    def test_delete_nonexistent_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.delete(f"{BASE_REVIEWS}/999999", headers=h)
        assert r.status_code == 404

    def test_review_read_includes_months_count(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        review = _create_review(client, h, emp_id, _YEAR + 5, "tot")
        r = client.get(f"{BASE_REVIEWS}/{review['id']}", headers=h)
        assert r.status_code == 200
        assert "months_count" in r.json()
        assert "avg_score" in r.json()


# ── TestYearlyReviewList ──────────────────────────────────────────────────────


class TestYearlyReviewList:
    def test_list_returns_items(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_review(client, h, emp_id, _LIST_YEAR, "tot")
        r = client.get(BASE_REVIEWS, headers=h)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_filter_by_year(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_review(client, h, emp_id, _LIST_YEAR + 1, "dat")
        r = client.get(BASE_REVIEWS, headers=h, params={"year": _LIST_YEAR + 1})
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        assert all(i["year"] == _LIST_YEAR + 1 for i in items)

    def test_filter_by_rating(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_review(client, h, emp_id, _LIST_YEAR + 2, "xuat_sac")
        r = client.get(BASE_REVIEWS, headers=h, params={"rating": "xuat_sac"})
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        assert all(i["rating"] == "xuat_sac" for i in items)

    def test_search_by_employee_name(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_review(client, h, emp_id, _LIST_YEAR + 3, "tot")
        emp_name = client.get(f"{BASE_EMP}/{emp_id}", headers=h).json()["full_name"]
        r = client.get(BASE_REVIEWS, headers=h, params={"search": emp_name[:4]})
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_pagination(self, client: TestClient):
        h = _admin(client)
        r = client.get(BASE_REVIEWS, headers=h, params={"page": 1, "page_size": 2})
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) <= 2

    def test_response_includes_rating_label(self, client: TestClient):
        h = _admin(client)
        emp_id = _get_emp_id(client, h)
        _create_review(client, h, emp_id, _LIST_YEAR + 4, "can_cai_thien")
        r = client.get(BASE_REVIEWS, headers=h, params={"rating": "can_cai_thien"})
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        assert items[0]["rating_label"] == "Cần cải thiện"
