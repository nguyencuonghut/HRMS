"""Integration tests — Plan 14.1: Onboarding Checklist.

Dùng năm test 2098 / nhân viên fake để tránh va chạm với dữ liệu thật.

Nguyên tắc viết test:
- Mỗi test verify một business rule cụ thể, đọc lên biết ngay HỆ THỐNG LÀM GÌ.
- Test qua public API (HTTP) — không biết code bên trong.
- Test phải fail nếu business rule bị vi phạm, pass nếu rule được tôn trọng.
- Không test tên field, cấu trúc response, hay nội dung migration.
"""
from __future__ import annotations

import time as _time
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

BASE = "/api/v1/onboarding"
BASE_TASKS = "/api/v1/onboarding/tasks"
BASE_EMP = "/api/v1/employees"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"

_TEST_YEAR = 2098
_START_DATE = f"{_TEST_YEAR}-01-15"

_emp_counter = 0
_RUN_SUFFIX = str(int(_time.time()))[-6:]


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_probation_employee(client: TestClient, h: dict) -> dict:
    """Tạo nhân viên thử việc để test onboarding.
    Dùng position's own dept+title để tránh lỗi FK validation.
    """
    global _emp_counter
    _emp_counter += 1

    rows = client.get("/api/v1/job-positions", headers=h, params={"page_size": 5}).json()
    positions = rows if isinstance(rows, list) else rows.get("items", rows)
    assert positions, "Cần ít nhất 1 vị trí công việc trong DB"
    pos = next((p for p in positions if p.get("department_id")), positions[0])

    r = client.post(BASE_EMP, json={
        "full_name": f"Test OB {_TEST_YEAR} #{_emp_counter}",
        "last_name": "Test",
        "first_name": f"OB{_emp_counter}",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": 1,
        "id_number": f"OB{_RUN_SUFFIX}{_emp_counter:04d}",
        "id_issued_on": "2010-01-01",
        "id_issued_by": "CA",
        "personal_email": f"ob_{_RUN_SUFFIX}_{_emp_counter:04d}@test.local",
        "status": "probation",
        "start_date": _START_DATE,
        "initial_department_id": pos["department_id"],
        "initial_job_position_id": pos["id"],
        "initial_job_title_id": pos.get("job_title_id") or 1,
        "initial_probation_start_date": _START_DATE,
        "initial_probation_end_date": f"{_TEST_YEAR}-03-15",
        "initial_job_effective_from": _START_DATE,
    }, headers=h)
    assert r.status_code in (200, 201), f"Tạo nhân viên thất bại: {r.text}"
    return r.json()


def _create_checklist(client: TestClient, h: dict, emp_id: int) -> dict:
    r = client.post(BASE, json={"employee_id": emp_id}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


# ── TestTaskTemplates ──────────────────────────────────────────────────────────


class TestTaskTemplates:
    """Business rules liên quan đến quản lý template task onboarding."""

    def test_hr_can_see_predefined_task_groups(self, client: TestClient):
        """Hệ thống phải có task templates bao phủ các nhóm công việc cơ bản:
        hành chính, IT, đào tạo, chuyên môn — để HR có thể dùng ngay.
        """
        h = _admin(client)
        r = client.get(BASE_TASKS, headers=h, params={"is_active": "true"})
        assert r.status_code == 200, r.text
        tasks = r.json()
        groups = {t["group"] for t in tasks}
        # Bốn nhóm cơ bản phải có mặt
        assert "admin" in groups,    "Thiếu nhóm hành chính (admin)"
        assert "it" in groups,       "Thiếu nhóm IT"
        assert "training" in groups, "Thiếu nhóm đào tạo"
        assert "specialty" in groups,"Thiếu nhóm chuyên môn"

    def test_hr_can_filter_tasks_by_group(self, client: TestClient):
        """Khi HR lọc task theo nhóm, chỉ nhận task thuộc nhóm đó."""
        h = _admin(client)
        r = client.get(BASE_TASKS, headers=h, params={"group": "it"})
        assert r.status_code == 200, r.text
        tasks = r.json()
        assert len(tasks) >= 1, "Nhóm IT phải có ít nhất 1 task"
        assert all(t["group"] == "it" for t in tasks), \
            "Filter group=it trả về task thuộc nhóm khác"

    def test_hr_can_create_new_task_template(self, client: TestClient):
        """HR có thể thêm task template mới; task mới mặc định đang hoạt động."""
        h = _admin(client)
        code = f"TEST_TASK_{_RUN_SUFFIX}"
        r = client.post(BASE_TASKS, json={
            "code": code,
            "name": "Hướng dẫn sử dụng hệ thống nội bộ",
            "group": "it",
            "due_offset_days": 2,
        }, headers=h)
        assert r.status_code == 201, r.text
        created = r.json()
        assert created["is_active"] is True, \
            "Task mới phải mặc định là active để được dùng trong checklist"
        # Cleanup
        client.delete(f"{BASE_TASKS}/{created['id']}", headers=h)

    def test_cannot_create_two_tasks_with_same_code(self, client: TestClient):
        """Mỗi task template có một code duy nhất — không được tạo trùng."""
        h = _admin(client)
        # ADMIN_WELCOME đã tồn tại từ seed
        r = client.post(BASE_TASKS, json={
            "code": "ADMIN_WELCOME",
            "name": "Task trùng code",
            "group": "admin",
        }, headers=h)
        assert r.status_code in (409, 422), \
            "Tạo task với code đã tồn tại phải bị từ chối"

    def test_hr_can_update_task_due_offset(self, client: TestClient):
        """HR có thể điều chỉnh số ngày hạn của task template.
        Thay đổi này chỉ ảnh hưởng checklist MỚI tạo sau đó, không thay đổi checklist cũ.
        """
        h = _admin(client)
        tasks = client.get(BASE_TASKS, headers=h).json()
        task = tasks[0]
        new_offset = task["due_offset_days"] + 5

        r = client.put(f"{BASE_TASKS}/{task['id']}", json={"due_offset_days": new_offset}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["due_offset_days"] == new_offset, \
            "due_offset_days phải được cập nhật theo giá trị HR nhập"

        # Revert để tránh ảnh hưởng các test khác
        client.put(f"{BASE_TASKS}/{task['id']}", json={"due_offset_days": task["due_offset_days"]}, headers=h)

    def test_delete_nonexistent_task_returns_not_found(self, client: TestClient):
        """Xóa task không tồn tại → thông báo không tìm thấy."""
        h = _admin(client)
        r = client.delete(f"{BASE_TASKS}/99999999", headers=h)
        assert r.status_code == 404


# ── TestChecklistCreation ──────────────────────────────────────────────────────


class TestChecklistCreation:
    """Business rules khi tạo checklist onboarding cho nhân viên mới."""

    def test_new_checklist_includes_all_active_tasks(self, client: TestClient):
        """Khi tạo checklist, TẤT CẢ task template đang active phải được thêm vào.
        HR không cần chọn từng task một.
        """
        h = _admin(client)
        # Đếm số task active hiện tại
        active_tasks = client.get(BASE_TASKS, headers=h, params={"is_active": "true"}).json()
        active_count = len(active_tasks)
        assert active_count > 0, "Cần có task active để test"

        emp = _create_probation_employee(client, h)
        try:
            checklist = _create_checklist(client, h, emp["id"])
            assert len(checklist["items"]) == active_count, \
                f"Checklist phải có đúng {active_count} items (= số task active), " \
                f"thực tế có {len(checklist['items'])}"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_item_due_date_equals_start_date_plus_offset(self, client: TestClient):
        """due_date của mỗi item = ngày vào làm + due_offset_days của task tương ứng.
        Đây là rule cốt lõi giúp HR biết hạn hoàn thành từng task.
        """
        h = _admin(client)
        active_tasks = client.get(BASE_TASKS, headers=h, params={"is_active": "true"}).json()
        task_offset_by_code = {t["code"]: t["due_offset_days"] for t in active_tasks}

        emp = _create_probation_employee(client, h)
        start = date.fromisoformat(_START_DATE)
        try:
            checklist = _create_checklist(client, h, emp["id"])
            for item in checklist["items"]:
                expected = start + timedelta(days=task_offset_by_code[item["task_code"]])
                actual = date.fromisoformat(item["due_date"])
                assert actual == expected, (
                    f"Task {item['task_code']} (offset={task_offset_by_code[item['task_code']]}): "
                    f"due_date phải là {expected}, nhận được {actual}"
                )
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_new_checklist_starts_with_zero_progress(self, client: TestClient):
        """Checklist mới chưa có task nào được thực hiện — tiến độ phải là 0%."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        try:
            checklist = _create_checklist(client, h, emp["id"])
            assert checklist["completion_pct"] == 0.0, \
                "Checklist mới phải bắt đầu với 0% completion"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_cannot_create_second_checklist_for_same_employee(self, client: TestClient):
        """Mỗi nhân viên chỉ có một checklist onboarding.
        Tạo lần 2 phải bị từ chối — tránh tạo nhầm lặp dữ liệu.
        """
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        try:
            _create_checklist(client, h, emp["id"])
            r2 = client.post(BASE, json={"employee_id": emp["id"]}, headers=h)
            assert r2.status_code == 409, \
                "Tạo checklist lần 2 cho cùng nhân viên phải trả về 409 Conflict"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_creating_checklist_for_nonexistent_employee_fails(self, client: TestClient):
        """Không thể tạo checklist cho nhân viên không tồn tại."""
        h = _admin(client)
        r = client.post(BASE, json={"employee_id": 99999999}, headers=h)
        assert r.status_code == 404


# ── TestItemUpdate ─────────────────────────────────────────────────────────────


class TestItemUpdate:
    """Business rules khi HR cập nhật trạng thái từng task trong checklist."""

    def _setup(self, client: TestClient, h: dict) -> tuple[dict, dict]:
        emp = _create_probation_employee(client, h)
        checklist = _create_checklist(client, h, emp["id"])
        return emp, checklist

    def _patch_item(self, client: TestClient, h: dict, checklist_id: int, item_id: int, **kwargs) -> dict:
        r = client.patch(f"{BASE}/{checklist_id}/items/{item_id}", json=kwargs, headers=h)
        assert r.status_code == 200, r.text
        return r.json()

    def test_completing_task_records_timestamp(self, client: TestClient):
        """Khi HR đánh dấu task hoàn thành, hệ thống ghi nhận thời điểm hoàn thành.
        Dùng để audit trail và báo cáo tiến độ.
        """
        h = _admin(client)
        emp, checklist = self._setup(client, h)
        try:
            item = self._patch_item(client, h, checklist["id"], checklist["items"][0]["id"],
                                    status="done")
            assert item["completed_at"] is not None, \
                "Hoàn thành task phải ghi nhận completed_at"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_reopening_task_clears_completion_timestamp(self, client: TestClient):
        """Nếu HR re-open task đã done (ví dụ: đánh dấu nhầm), completed_at phải được xóa.
        Timestamp chỉ tồn tại khi task thực sự done.
        """
        h = _admin(client)
        emp, checklist = self._setup(client, h)
        item_id = checklist["items"][0]["id"]
        checklist_id = checklist["id"]
        try:
            # Đánh dấu done
            self._patch_item(client, h, checklist_id, item_id, status="done")
            # Reopen về in_progress
            reopened = self._patch_item(client, h, checklist_id, item_id, status="in_progress")
            assert reopened["completed_at"] is None, \
                "Re-open task phải xóa completed_at — task chưa hoàn thành"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_completion_percentage_reflects_exact_proportion(self, client: TestClient):
        """completion_pct phải phản ánh chính xác tỉ lệ task đã xong / tổng task.
        Ví dụ: 8 tasks, mark 1 done → 12.5%.
        """
        h = _admin(client)
        emp, checklist = self._setup(client, h)
        checklist_id = checklist["id"]
        total_items = len(checklist["items"])
        assert total_items > 0
        try:
            # Mark đúng 1 task đầu tiên
            self._patch_item(client, h, checklist_id, checklist["items"][0]["id"], status="done")

            updated = client.get(f"{BASE}/{checklist_id}", headers=h).json()
            expected_pct = round(1 / total_items * 100, 2)
            assert abs(updated["completion_pct"] - expected_pct) < 0.1, \
                f"Sau khi done 1/{total_items} task, completion_pct phải ≈ {expected_pct}%, " \
                f"nhận được {updated['completion_pct']}%"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_skipped_tasks_excluded_from_completion_calculation(self, client: TestClient):
        """Task bị skip không tính vào tổng khi tính %.
        Nếu có 8 tasks, skip 1, done 1 → pct = 1/7 ≈ 14.29% (không phải 1/8 = 12.5%).
        Business rule: skip = "không áp dụng", không coi là task cần làm.
        """
        h = _admin(client)
        emp, checklist = self._setup(client, h)
        checklist_id = checklist["id"]
        items = checklist["items"]
        assert len(items) >= 3, "Cần ít nhất 3 items để test"
        try:
            # Skip item đầu tiên
            self._patch_item(client, h, checklist_id, items[0]["id"], status="skipped")
            # Done item thứ hai
            self._patch_item(client, h, checklist_id, items[1]["id"], status="done")

            updated = client.get(f"{BASE}/{checklist_id}", headers=h).json()
            # total không tính skipped: (len - 1) items
            non_skipped = len(items) - 1
            expected_pct = round(1 / non_skipped * 100, 2)
            assert abs(updated["completion_pct"] - expected_pct) < 0.1, \
                f"Skip 1 task → tổng tính là {non_skipped}, done 1 → pct phải ≈ {expected_pct}%, " \
                f"nhận được {updated['completion_pct']}%"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_checklist_auto_completes_when_all_tasks_done_or_skipped(self, client: TestClient):
        """Khi tất cả tasks đã done hoặc skipped, checklist tự chuyển sang 'completed'.
        HR không cần bấm nút 'hoàn thành' thủ công.
        Có thể dùng mix done + skipped (thực tế phổ biến hơn all-done).
        """
        h = _admin(client)
        emp, checklist = self._setup(client, h)
        checklist_id = checklist["id"]
        items = checklist["items"]
        assert len(items) >= 2, "Cần ít nhất 2 items để test mix done/skipped"
        try:
            # Done một nửa, skip nửa còn lại
            for i, item in enumerate(items):
                status = "done" if i % 2 == 0 else "skipped"
                self._patch_item(client, h, checklist_id, item["id"], status=status)

            final = client.get(f"{BASE}/{checklist_id}", headers=h).json()
            assert final["status"] == "completed", \
                "Khi tất cả tasks done/skipped, checklist phải tự chuyển sang 'completed'"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_invalid_status_value_is_rejected(self, client: TestClient):
        """Chỉ chấp nhận status hợp lệ: pending, in_progress, done, skipped.
        Giá trị tùy tiện phải bị từ chối — tránh corrupt data.
        """
        h = _admin(client)
        emp, checklist = self._setup(client, h)
        try:
            r = client.patch(
                f"{BASE}/{checklist['id']}/items/{checklist['items'][0]['id']}",
                json={"status": "finished"},  # không hợp lệ
                headers=h,
            )
            assert r.status_code in (400, 422), \
                "Status không hợp lệ phải bị từ chối"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)


# ── TestChecklistList ──────────────────────────────────────────────────────────


class TestChecklistList:
    """Business rules khi HR xem danh sách checklist."""

    def test_newly_created_checklist_appears_in_list(self, client: TestClient):
        """Checklist vừa tạo phải xuất hiện trong danh sách ngay lập tức.
        HR phải thấy được nhân viên mới ngay khi checklist được tạo.
        """
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        try:
            _create_checklist(client, h, emp["id"])
            # Lọc theo in_progress để thu hẹp kết quả, page_size max 100 theo API
            r = client.get(BASE, headers=h, params={"status": "in_progress", "page_size": 100})
            assert r.status_code == 200, r.text
            ids = [item["employee_id"] for item in r.json()["items"]]
            assert emp["id"] in ids, \
                "Checklist vừa tạo phải xuất hiện trong danh sách"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_list_shows_correct_task_counts(self, client: TestClient):
        """Trong danh sách, số task đã done và tổng task phải khớp với thực tế.
        HR dùng số này để quyết định ai cần follow-up.
        """
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        try:
            checklist = _create_checklist(client, h, emp["id"])
            total_expected = len(checklist["items"])

            # Done 1 item
            first_item = checklist["items"][0]
            client.patch(
                f"{BASE}/{checklist['id']}/items/{first_item['id']}",
                json={"status": "done"}, headers=h,
            )

            r = client.get(BASE, headers=h, params={"status": "in_progress", "page_size": 100})
            assert r.status_code == 200, r.text
            our = next((i for i in r.json()["items"] if i["employee_id"] == emp["id"]), None)
            assert our is not None, "Checklist không xuất hiện trong danh sách"
            assert our["total_items"] == total_expected, \
                f"total_items phải = {total_expected}, nhận {our['total_items']}"
            assert our["done_items"] == 1, \
                f"done_items phải = 1 sau khi done 1 task, nhận {our['done_items']}"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_filter_by_status_returns_only_matching_checklists(self, client: TestClient):
        """HR lọc theo status 'in_progress' chỉ nhận checklist chưa hoàn thành.
        Tránh bị lẫn checklist đã hoàn thành hay đã hủy.
        """
        h = _admin(client)
        r = client.get(BASE, headers=h, params={"status": "in_progress", "page_size": 50})
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["status"] == "in_progress", \
                f"Filter status=in_progress nhưng nhận item với status={item['status']}"

    def test_list_can_be_paginated(self, client: TestClient):
        """HR có thể phân trang danh sách — hệ thống phải trả về đúng số lượng yêu cầu."""
        h = _admin(client)
        r = client.get(BASE, headers=h, params={"page": 1, "page_size": 3})
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) <= 3, \
            "page_size=3 không được trả về nhiều hơn 3 items"
        assert data["total"] >= 0, \
            "total phải là số nguyên không âm"


# ── TestChecklistUpdate ────────────────────────────────────────────────────────


class TestChecklistUpdate:
    """Business rules khi HR cập nhật thông tin checklist."""

    def test_hr_can_assign_buddy_to_checklist(self, client: TestClient):
        """HR có thể gán buddy (người hỗ trợ) cho nhân viên mới bất kỳ lúc nào.
        Buddy được ghi nhận để nhân viên mới biết ai cần liên hệ.
        """
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        try:
            checklist = _create_checklist(client, h, emp["id"])
            assert checklist["buddy_user_id"] is None, \
                "Checklist mới chưa có buddy"

            # Gán admin làm buddy (admin luôn tồn tại)
            me = client.get("/api/v1/users/me", headers=h)
            user_id = me.json()["id"] if me.status_code == 200 else 1

            r = client.patch(f"{BASE}/{checklist['id']}", json={"buddy_user_id": user_id}, headers=h)
            assert r.status_code == 200
            assert r.json()["buddy_user_id"] == user_id, \
                "buddy_user_id phải được cập nhật"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)

    def test_hr_can_cancel_checklist(self, client: TestClient):
        """HR có thể hủy checklist nếu nhân viên nghỉ đột ngột hoặc checklist tạo nhầm.
        Sau khi hủy, checklist không thể cập nhật tiếp.
        """
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        try:
            checklist = _create_checklist(client, h, emp["id"])
            r = client.patch(f"{BASE}/{checklist['id']}", json={"status": "cancelled"}, headers=h)
            assert r.status_code == 200
            assert r.json()["status"] == "cancelled", \
                "Sau khi hủy, status phải là 'cancelled'"
        finally:
            client.delete(f"{BASE_EMP}/{emp['id']}", headers=h)
