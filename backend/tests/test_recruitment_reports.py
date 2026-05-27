"""Integration tests — Plan 13.8: Recruitment Analytics Reports."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

BASE = "/api/v1/recruitment/reports"
BASE_JR = "/api/v1/recruitment/job-requisitions"
BASE_DEPT = "/api/v1/departments"
BASE_POS = "/api/v1/job-positions"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"

_TEST_YEAR = 2099
_START = f"{_TEST_YEAR}-01-01"
_END = f"{_TEST_YEAR}-12-31"


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_dept_id(client: TestClient, h: dict) -> int:
    items = client.get(BASE_DEPT, headers=h, params={"page_size": 1}).json()
    rows = items if isinstance(items, list) else items.get("items", items)
    assert rows, "Cần ít nhất 1 phòng ban trong DB"
    return rows[0]["id"]


def _get_pos_id(client: TestClient, h: dict) -> int:
    items = client.get(BASE_POS, headers=h, params={"page_size": 1}).json()
    rows = items if isinstance(items, list) else items.get("items", items)
    assert rows, "Cần ít nhất 1 vị trí công việc trong DB"
    return rows[0]["id"]


def _create_jr(client: TestClient, h: dict, dept_id: int, pos_id: int) -> dict:
    payload = {
        "job_position_id": pos_id,
        "department_id": dept_id,
        "quantity": 1,
        "reason_type": "new",
    }
    r = client.post(BASE_JR, json=payload, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _cleanup_jr(client: TestClient, h: dict, jr_id: int) -> None:
    r = client.get(f"{BASE_JR}/{jr_id}", headers=h)
    if r.status_code != 200:
        return
    st = r.json().get("status")
    if st == "draft":
        client.delete(f"{BASE_JR}/{jr_id}", headers=h)
    elif st in ("pending_review", "approved", "in_progress"):
        client.post(f"{BASE_JR}/{jr_id}/cancel", json={}, headers=h)


# ── TestSummaryReport ─────────────────────────────────────────────────────────


class TestSummaryReport:
    def test_summary_empty_period(self, client: TestClient):
        """Kỳ không có dữ liệu → trả về zeros."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/summary",
            headers=h,
            params={"start_date": _START, "end_date": _END},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total_jr"] == 0
        assert data["total_applications"] == 0
        assert data["total_hired"] == 0
        assert data["period_start"] == _START
        assert data["period_end"] == _END

    def test_summary_with_jr(self, client: TestClient):
        """Kỳ có JR → total_jr > 0."""
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        jr_id = jr["id"]

        try:
            r = client.get(
                f"{BASE}/summary",
                headers=h,
                params={"start_date": "2020-01-01", "end_date": "2030-12-31"},
            )
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["total_jr"] >= 1
            assert "avg_time_to_hire" in data
            assert "offer_acceptance_rate" in data
        finally:
            _cleanup_jr(client, h, jr_id)

    def test_summary_with_department_filter(self, client: TestClient):
        """Filter theo phòng ban → chỉ trả dữ liệu của phòng ban đó."""
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        r = client.get(
            f"{BASE}/summary",
            headers=h,
            params={"start_date": _START, "end_date": _END, "department_id": dept_id},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # Kỳ 2099 không có dữ liệu nên total = 0
        assert data["total_jr"] == 0

    def test_summary_schema_fields(self, client: TestClient):
        """Response có đủ các field theo schema."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/summary",
            headers=h,
            params={"start_date": _START, "end_date": _END},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        required = [
            "period_start", "period_end", "total_jr", "total_applications",
            "total_screened", "total_interviewed", "total_offered", "total_hired",
        ]
        for field in required:
            assert field in data, f"Thiếu field: {field}"

    def test_summary_requires_auth(self, client: TestClient):
        """Không có token → 401/403."""
        r = client.get(f"{BASE}/summary", params={"start_date": _START, "end_date": _END})
        assert r.status_code in (401, 403)

    def test_summary_invalid_dates(self, client: TestClient):
        """Thiếu start_date → 422."""
        h = _admin(client)
        r = client.get(f"{BASE}/summary", headers=h, params={"end_date": _END})
        assert r.status_code == 422


# ── TestFunnelReport ──────────────────────────────────────────────────────────


class TestFunnelReport:
    def test_funnel_returns_all_stages(self, client: TestClient):
        """Funnel phải trả đủ 8 stage theo thứ tự cố định."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/funnel",
            headers=h,
            params={"start_date": _START, "end_date": _END},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "stages" in data
        stages = data["stages"]
        assert len(stages) == 8
        expected_order = ["new", "screening", "test", "interview", "offer", "hired", "rejected", "withdrawn"]
        for i, stage_key in enumerate(expected_order):
            assert stages[i]["stage"] == stage_key

    def test_funnel_stage_schema(self, client: TestClient):
        """Mỗi stage có đủ field."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/funnel",
            headers=h,
            params={"start_date": _START, "end_date": _END},
        )
        assert r.status_code == 200, r.text
        for stage in r.json()["stages"]:
            assert "stage" in stage
            assert "stage_label" in stage
            assert "count" in stage
            assert isinstance(stage["count"], int)

    def test_funnel_empty_period_zero_counts(self, client: TestClient):
        """Kỳ không có dữ liệu → tất cả stage có count = 0."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/funnel",
            headers=h,
            params={"start_date": _START, "end_date": _END},
        )
        assert r.status_code == 200, r.text
        for stage in r.json()["stages"]:
            assert stage["count"] == 0

    def test_funnel_with_jr_filter(self, client: TestClient):
        """Filter theo job_requisition_id → không lỗi."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/funnel",
            headers=h,
            params={"start_date": _START, "end_date": _END, "job_requisition_id": 999999},
        )
        assert r.status_code == 200, r.text
        assert "stages" in r.json()

    def test_funnel_with_department_filter(self, client: TestClient):
        """Filter theo department_id → không lỗi."""
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        r = client.get(
            f"{BASE}/funnel",
            headers=h,
            params={"start_date": _START, "end_date": _END, "department_id": dept_id},
        )
        assert r.status_code == 200, r.text


# ── TestChannelEffectiveness ──────────────────────────────────────────────────


class TestChannelEffectiveness:
    def test_channel_returns_list(self, client: TestClient):
        """Endpoint trả list (có thể rỗng)."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/channel-effectiveness",
            headers=h,
            params={"start_date": _START, "end_date": _END},
        )
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_channel_empty_period(self, client: TestClient):
        """Kỳ 2099 không có dữ liệu → danh sách rỗng."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/channel-effectiveness",
            headers=h,
            params={"start_date": _START, "end_date": _END},
        )
        assert r.status_code == 200, r.text
        assert r.json() == []

    def test_channel_schema_fields(self, client: TestClient):
        """Nếu có item, phải có đủ field."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/channel-effectiveness",
            headers=h,
            params={"start_date": "2020-01-01", "end_date": "2030-12-31"},
        )
        assert r.status_code == 200, r.text
        items = r.json()
        for item in items:
            for field in ["channel_id", "channel_name", "total_candidates", "hired_count", "hire_rate"]:
                assert field in item, f"Thiếu field: {field}"
            assert 0.0 <= item["hire_rate"] <= 100.0

    def test_channel_requires_auth(self, client: TestClient):
        """Không có token → 401/403."""
        r = client.get(f"{BASE}/channel-effectiveness", params={"start_date": _START, "end_date": _END})
        assert r.status_code in (401, 403)


# ── TestDepartmentBreakdown ───────────────────────────────────────────────────


class TestDepartmentBreakdown:
    def test_dept_returns_list(self, client: TestClient):
        """Endpoint trả list."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/by-department",
            headers=h,
            params={"start_date": _START, "end_date": _END},
        )
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_dept_empty_period(self, client: TestClient):
        """Kỳ 2099 không có dữ liệu → rỗng."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/by-department",
            headers=h,
            params={"start_date": _START, "end_date": _END},
        )
        assert r.status_code == 200, r.text
        assert r.json() == []

    def test_dept_schema_fields(self, client: TestClient):
        """Nếu có dữ liệu, item có đủ field."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/by-department",
            headers=h,
            params={"start_date": "2020-01-01", "end_date": "2030-12-31"},
        )
        assert r.status_code == 200, r.text
        for item in r.json():
            for field in ["department_id", "department_name", "total_jr", "open_jr", "hired_count"]:
                assert field in item, f"Thiếu field: {field}"
            assert item["total_jr"] >= item["open_jr"]


# ── TestTimeMetrics ───────────────────────────────────────────────────────────


class TestTimeMetrics:
    def test_time_metrics_returns_12_months(self, client: TestClient):
        """Luôn trả đủ 12 tháng dù không có dữ liệu."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/time-metrics",
            headers=h,
            params={"year": _TEST_YEAR},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["year"] == _TEST_YEAR
        assert len(data["monthly"]) == 12

    def test_time_metrics_month_sequence(self, client: TestClient):
        """Các tháng phải theo thứ tự 1 → 12."""
        h = _admin(client)
        r = client.get(f"{BASE}/time-metrics", headers=h, params={"year": _TEST_YEAR})
        assert r.status_code == 200, r.text
        monthly = r.json()["monthly"]
        for i, m in enumerate(monthly, 1):
            assert m["month"] == i
            assert m["year"] == _TEST_YEAR

    def test_time_metrics_empty_year_zero_counts(self, client: TestClient):
        """Năm 2099 → tất cả hired_count và applications_count = 0."""
        h = _admin(client)
        r = client.get(f"{BASE}/time-metrics", headers=h, params={"year": _TEST_YEAR})
        assert r.status_code == 200, r.text
        for m in r.json()["monthly"]:
            assert m["hired_count"] == 0
            assert m["applications_count"] == 0

    def test_time_metrics_schema_fields(self, client: TestClient):
        """Mỗi monthly item có đủ field."""
        h = _admin(client)
        r = client.get(f"{BASE}/time-metrics", headers=h, params={"year": _TEST_YEAR})
        assert r.status_code == 200, r.text
        for m in r.json()["monthly"]:
            for field in ["month", "year", "hired_count", "applications_count"]:
                assert field in m, f"Thiếu field: {field}"

    def test_time_metrics_with_department_filter(self, client: TestClient):
        """Filter theo department_id → không lỗi."""
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        r = client.get(
            f"{BASE}/time-metrics",
            headers=h,
            params={"year": _TEST_YEAR, "department_id": dept_id},
        )
        assert r.status_code == 200, r.text
        assert len(r.json()["monthly"]) == 12

    def test_time_metrics_invalid_year(self, client: TestClient):
        """Year ngoài range → 422."""
        h = _admin(client)
        r = client.get(f"{BASE}/time-metrics", headers=h, params={"year": 1900})
        assert r.status_code == 422

    def test_time_metrics_requires_auth(self, client: TestClient):
        """Không có token → 401/403."""
        r = client.get(f"{BASE}/time-metrics", params={"year": _TEST_YEAR})
        assert r.status_code in (401, 403)


# ── TestExportExcel ───────────────────────────────────────────────────────────


class TestExportExcel:
    def test_export_returns_xlsx(self, client: TestClient):
        """Export endpoint trả file Excel đúng content-type."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/export",
            headers=h,
            params={"start_date": _START, "end_date": _END},
        )
        assert r.status_code == 200, r.text
        assert "spreadsheetml" in r.headers.get("content-type", "")
        assert len(r.content) > 0

    def test_export_filename_contains_dates(self, client: TestClient):
        """Content-Disposition chứa ngày báo cáo."""
        h = _admin(client)
        r = client.get(
            f"{BASE}/export",
            headers=h,
            params={"start_date": _START, "end_date": _END},
        )
        assert r.status_code == 200, r.text
        cd = r.headers.get("content-disposition", "")
        assert "BaoCaoTuyenDung" in cd
        assert str(_TEST_YEAR) in cd

    def test_export_requires_auth(self, client: TestClient):
        """Không có token → 401/403."""
        r = client.get(f"{BASE}/export", params={"start_date": _START, "end_date": _END})
        assert r.status_code in (401, 403)
