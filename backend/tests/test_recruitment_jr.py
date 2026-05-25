"""Integration tests — Plan 13.1: Headcount Plan & Job Requisition."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

BASE_JR      = "/api/v1/recruitment/job-requisitions"
BASE_HC      = "/api/v1/recruitment/headcount-plans"
BASE_DEPT    = "/api/v1/departments"
BASE_POS     = "/api/v1/job-positions"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"

_TEST_YEAR = 2099   # Năm không có dữ liệu thực


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_dept_id(client: TestClient, h: dict) -> int:
    items = client.get(BASE_DEPT, headers=h, params={"page_size": 1}).json()
    assert items, "Cần ít nhất 1 phòng ban trong DB"
    # departments trả list trực tiếp hoặc có items key
    rows = items if isinstance(items, list) else items.get("items", items)
    assert rows, "Cần ít nhất 1 phòng ban trong DB"
    return rows[0]["id"]


def _get_pos_id(client: TestClient, h: dict) -> int:
    items = client.get(BASE_POS, headers=h, params={"page_size": 1}).json()
    rows = items if isinstance(items, list) else items.get("items", items)
    assert rows, "Cần ít nhất 1 vị trí công việc trong DB"
    return rows[0]["id"]


def _create_jr(client: TestClient, h: dict, dept_id: int, pos_id: int, **kwargs) -> dict:
    payload = {
        "job_position_id": pos_id,
        "department_id": dept_id,
        "quantity": 1,
        "reason_type": "new",
        **kwargs,
    }
    r = client.post(BASE_JR, json=payload, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _delete_jr(client: TestClient, h: dict, jr_id: int):
    """Xóa JR nếu còn ở draft, cancel trước nếu cần."""
    r = client.get(f"{BASE_JR}/{jr_id}", headers=h)
    if r.status_code != 200:
        return
    st = r.json()["status"]
    if st == "draft":
        client.delete(f"{BASE_JR}/{jr_id}", headers=h)
    elif st in ("pending_review", "approved", "in_progress"):
        client.post(f"{BASE_JR}/{jr_id}/cancel", json={}, headers=h)


# ── TestHeadcountPlan ─────────────────────────────────────────────────────────


class TestHeadcountPlan:
    def test_create_plan_success(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        r = client.post(
            BASE_HC,
            json={"year": _TEST_YEAR, "department_id": dept_id, "planned_count": 3},
            headers=h,
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["year"] == _TEST_YEAR
        assert data["planned_count"] == 3
        assert data["department_id"] == dept_id
        # Cleanup
        client.delete(f"{BASE_HC}/{data['id']}", headers=h)

    def test_create_plan_without_department(self, client: TestClient):
        h = _admin(client)
        r = client.post(
            BASE_HC,
            json={"year": _TEST_YEAR, "planned_count": 5},
            headers=h,
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["department_id"] is None
        client.delete(f"{BASE_HC}/{data['id']}", headers=h)

    def test_create_duplicate_plan_returns_409(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        r1 = client.post(
            BASE_HC,
            json={"year": _TEST_YEAR, "department_id": dept_id, "job_position_id": None, "planned_count": 2},
            headers=h,
        )
        assert r1.status_code == 201, r1.text
        plan_id = r1.json()["id"]

        r2 = client.post(
            BASE_HC,
            json={"year": _TEST_YEAR, "department_id": dept_id, "job_position_id": None, "planned_count": 1},
            headers=h,
        )
        assert r2.status_code == 409, r2.text
        client.delete(f"{BASE_HC}/{plan_id}", headers=h)

    def test_list_plans_filter_by_year(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        r = client.post(
            BASE_HC,
            json={"year": _TEST_YEAR, "department_id": dept_id, "job_position_id": pos_id, "planned_count": 4},
            headers=h,
        )
        assert r.status_code == 201, r.text
        plan_id = r.json()["id"]

        r2 = client.get(BASE_HC, headers=h, params={"year": _TEST_YEAR})
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert data["total"] >= 1
        assert all(i["year"] == _TEST_YEAR for i in data["items"])
        client.delete(f"{BASE_HC}/{plan_id}", headers=h)

    def test_update_plan(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        r = client.post(
            BASE_HC,
            json={"year": _TEST_YEAR, "department_id": dept_id, "job_position_id": pos_id,
                  "planned_count": 2, "current_count": 0},
            headers=h,
        )
        plan_id = r.json()["id"]

        ru = client.put(f"{BASE_HC}/{plan_id}", json={"planned_count": 10, "reason": "Mở rộng"}, headers=h)
        assert ru.status_code == 200, ru.text
        assert ru.json()["planned_count"] == 10
        assert ru.json()["reason"] == "Mở rộng"
        client.delete(f"{BASE_HC}/{plan_id}", headers=h)

    def test_delete_plan_with_linked_jr_returns_409(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)

        # Tạo plan dùng năm và vị trí riêng để không đụng duplicate
        r_plan = client.post(
            BASE_HC,
            json={"year": _TEST_YEAR, "department_id": dept_id, "job_position_id": pos_id, "planned_count": 1},
            headers=h,
        )
        assert r_plan.status_code == 201, r_plan.text
        plan_id = r_plan.json()["id"]

        jr = _create_jr(client, h, dept_id, pos_id, headcount_plan_id=plan_id)
        jr_id = jr["id"]

        r_del = client.delete(f"{BASE_HC}/{plan_id}", headers=h)
        assert r_del.status_code == 409, r_del.text

        # Cleanup
        _delete_jr(client, h, jr_id)
        client.delete(f"{BASE_HC}/{plan_id}", headers=h)

    def test_fulfillment_rate_endpoint(self, client: TestClient):
        h = _admin(client)
        r = client.get(
            f"{BASE_HC}/fulfillment",
            headers=h,
            params={"year": _TEST_YEAR},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "year" in data
        assert "fulfillment_rate" in data
        assert data["year"] == _TEST_YEAR


# ── TestJobRequisitionCRUD ────────────────────────────────────────────────────


class TestJobRequisitionCRUD:
    def test_create_jr_success(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)

        assert jr["status"] == "draft"
        assert jr["status_label"] == "Nháp"
        assert jr["quantity"] == 1
        assert jr["quantity_remaining"] == 1
        assert jr["code"].startswith("JR-")
        assert jr["department_id"] == dept_id
        assert jr["job_position_id"] == pos_id
        _delete_jr(client, h, jr["id"])

    def test_create_jr_auto_generates_code(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr1 = _create_jr(client, h, dept_id, pos_id)
        jr2 = _create_jr(client, h, dept_id, pos_id)
        assert jr1["code"] != jr2["code"]
        assert jr1["code"].startswith("JR-")
        assert jr2["code"].startswith("JR-")
        _delete_jr(client, h, jr1["id"])
        _delete_jr(client, h, jr2["id"])

    def test_create_jr_inherits_jd_from_position(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        # effective_description có thể là None (nếu position chưa có JD) hoặc từ position
        assert "effective_description" in jr
        _delete_jr(client, h, jr["id"])

    def test_create_jr_with_jd_override(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id,
                        jd_description="Override JD", jd_requirements="Override Req")
        assert jr["effective_description"] == "Override JD"
        assert jr["effective_requirements"] == "Override Req"
        _delete_jr(client, h, jr["id"])

    def test_get_jr_by_id(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        r = client.get(f"{BASE_JR}/{jr['id']}", headers=h)
        assert r.status_code == 200
        assert r.json()["id"] == jr["id"]
        _delete_jr(client, h, jr["id"])

    def test_get_nonexistent_jr_returns_404(self, client: TestClient):
        h = _admin(client)
        r = client.get(f"{BASE_JR}/999999", headers=h)
        assert r.status_code == 404

    def test_update_jr_in_draft(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        r = client.put(
            f"{BASE_JR}/{jr['id']}",
            json={"quantity": 3, "reason_type": "expansion", "internal_note": "Ghi chú mới"},
            headers=h,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["quantity"] == 3
        assert data["reason_type"] == "expansion"
        assert data["internal_note"] == "Ghi chú mới"
        _delete_jr(client, h, jr["id"])

    def test_delete_draft_jr(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        r = client.delete(f"{BASE_JR}/{jr['id']}", headers=h)
        assert r.status_code == 204
        r2 = client.get(f"{BASE_JR}/{jr['id']}", headers=h)
        assert r2.status_code == 404

    def test_list_jr_pagination(self, client: TestClient):
        h = _admin(client)
        r = client.get(BASE_JR, headers=h, params={"page": 1, "page_size": 5})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5

    def test_list_jr_filter_by_status(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)

        r = client.get(BASE_JR, headers=h, params={"status": "draft"})
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(i["status"] == "draft" for i in items)
        _delete_jr(client, h, jr["id"])

    def test_salary_range_validation(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        r = client.post(
            BASE_JR,
            json={
                "job_position_id": pos_id,
                "department_id": dept_id,
                "quantity": 1,
                "reason_type": "new",
                "salary_min": 20000000,
                "salary_max": 10000000,  # min > max → 422
            },
            headers=h,
        )
        assert r.status_code == 422, r.text

    def test_create_jr_invalid_position_returns_404(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        r = client.post(
            BASE_JR,
            json={"job_position_id": 999999, "department_id": dept_id, "quantity": 1, "reason_type": "new"},
            headers=h,
        )
        assert r.status_code == 404

    def test_read_includes_reason_type_label(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id, reason_type="replacement")
        assert jr["reason_type_label"] == "Thay thế nhân sự"
        _delete_jr(client, h, jr["id"])


# ── TestJRWorkflow ────────────────────────────────────────────────────────────


class TestJRWorkflow:
    def test_submit_draft_to_pending_review(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)

        r = client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "pending_review"
        assert data["submitted_at"] is not None
        # Cleanup
        client.post(f"{BASE_JR}/{jr['id']}/cancel", json={}, headers=h)

    def test_submit_non_draft_returns_409(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)

        r = client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)
        assert r.status_code == 409, r.text
        client.post(f"{BASE_JR}/{jr['id']}/cancel", json={}, headers=h)

    def test_approve_pending_jr(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)

        r = client.post(f"{BASE_JR}/{jr['id']}/approve", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "approved"
        assert data["approved_at"] is not None
        assert data["approved_by_id"] is not None
        client.post(f"{BASE_JR}/{jr['id']}/cancel", json={}, headers=h)

    def test_approve_non_pending_returns_409(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)

        r = client.post(f"{BASE_JR}/{jr['id']}/approve", headers=h)
        assert r.status_code == 409, r.text
        _delete_jr(client, h, jr["id"])

    def test_reject_returns_to_draft_with_note(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)

        r = client.post(
            f"{BASE_JR}/{jr['id']}/reject",
            json={"rejection_note": "Chưa đủ ngân sách"},
            headers=h,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "draft"
        assert data["rejection_note"] == "Chưa đủ ngân sách"
        _delete_jr(client, h, jr["id"])

    def test_reject_without_note_returns_422(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)

        r = client.post(f"{BASE_JR}/{jr['id']}/reject", json={"rejection_note": ""}, headers=h)
        assert r.status_code == 422, r.text
        client.post(f"{BASE_JR}/{jr['id']}/cancel", json={}, headers=h)

    def test_cancel_draft_jr(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)

        r = client.post(f"{BASE_JR}/{jr['id']}/cancel", json={}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "cancelled"

    def test_cancel_approved_jr(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)
        client.post(f"{BASE_JR}/{jr['id']}/approve", headers=h)

        r = client.post(f"{BASE_JR}/{jr['id']}/cancel", json={"reason": "Thay đổi kế hoạch"}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "cancelled"

    def test_delete_non_draft_jr_returns_409(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)

        r = client.delete(f"{BASE_JR}/{jr['id']}", headers=h)
        assert r.status_code == 409, r.text
        client.post(f"{BASE_JR}/{jr['id']}/cancel", json={}, headers=h)

    def test_update_approved_jr_returns_409(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)
        client.post(f"{BASE_JR}/{jr['id']}/approve", headers=h)

        r = client.put(f"{BASE_JR}/{jr['id']}", json={"quantity": 5}, headers=h)
        assert r.status_code == 409, r.text
        client.post(f"{BASE_JR}/{jr['id']}/cancel", json={}, headers=h)

    def test_rejected_jr_can_be_resubmitted(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)
        client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)
        client.post(
            f"{BASE_JR}/{jr['id']}/reject",
            json={"rejection_note": "Cần bổ sung thông tin"},
            headers=h,
        )
        # Sau reject về draft, có thể submit lại
        r = client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "pending_review"
        client.post(f"{BASE_JR}/{jr['id']}/cancel", json={}, headers=h)


# ── TestBudget ────────────────────────────────────────────────────────────────


class TestBudget:
    def test_add_budget_item(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)

        r = client.post(
            f"{BASE_JR}/{jr['id']}/budget",
            json={"item_name": "Phí đăng tin TopCV", "estimated_amount": 5000000},
            headers=h,
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["item_name"] == "Phí đăng tin TopCV"
        assert float(data["estimated_amount"]) == 5000000.0
        assert data["actual_amount"] is None
        _delete_jr(client, h, jr["id"])

    def test_get_budget_summary(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)

        client.post(
            f"{BASE_JR}/{jr['id']}/budget",
            json={"item_name": "Headhunter", "estimated_amount": 10000000, "actual_amount": 9500000},
            headers=h,
        )
        client.post(
            f"{BASE_JR}/{jr['id']}/budget",
            json={"item_name": "Đăng tin nội bộ", "estimated_amount": 0},
            headers=h,
        )

        r = client.get(f"{BASE_JR}/{jr['id']}/budget", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["items"]) == 2
        assert float(data["total_estimated"]) == 10000000.0
        assert float(data["total_actual"]) == 9500000.0
        _delete_jr(client, h, jr["id"])

    def test_update_budget_item(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)

        item = client.post(
            f"{BASE_JR}/{jr['id']}/budget",
            json={"item_name": "Phí tuyển dụng", "estimated_amount": 3000000},
            headers=h,
        ).json()

        r = client.put(
            f"{BASE_JR}/{jr['id']}/budget/{item['id']}",
            json={"actual_amount": 2800000, "note": "Đã thanh toán"},
            headers=h,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert float(data["actual_amount"]) == 2800000.0
        assert data["note"] == "Đã thanh toán"
        _delete_jr(client, h, jr["id"])

    def test_delete_budget_item(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)

        item = client.post(
            f"{BASE_JR}/{jr['id']}/budget",
            json={"item_name": "Sẽ bị xóa", "estimated_amount": 1000000},
            headers=h,
        ).json()

        r = client.delete(f"{BASE_JR}/{jr['id']}/budget/{item['id']}", headers=h)
        assert r.status_code == 204

        # Verify xóa thành công
        summary = client.get(f"{BASE_JR}/{jr['id']}/budget", headers=h).json()
        ids = [i["id"] for i in summary["items"]]
        assert item["id"] not in ids
        _delete_jr(client, h, jr["id"])

    def test_budget_item_wrong_jr_returns_404(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)

        item = client.post(
            f"{BASE_JR}/{jr['id']}/budget",
            json={"item_name": "Test", "estimated_amount": 100000},
            headers=h,
        ).json()

        # Truy cập item_id với jr_id sai → 404
        r = client.put(
            f"{BASE_JR}/999999/budget/{item['id']}",
            json={"actual_amount": 50000},
            headers=h,
        )
        assert r.status_code == 404
        _delete_jr(client, h, jr["id"])

    def test_budget_total_empty_jr(self, client: TestClient):
        h = _admin(client)
        dept_id = _get_dept_id(client, h)
        pos_id = _get_pos_id(client, h)
        jr = _create_jr(client, h, dept_id, pos_id)

        r = client.get(f"{BASE_JR}/{jr['id']}/budget", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert float(data["total_estimated"]) == 0.0
        assert float(data["total_actual"]) == 0.0
        _delete_jr(client, h, jr["id"])
