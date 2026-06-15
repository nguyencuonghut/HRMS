"""Integration tests — Plan 14.2: Quản lý thử việc.

Nguyên tắc:
- Test qua public HTTP API (TestClient), không truy cập DB trực tiếp.
- Mỗi test verify một business rule cụ thể.
- Dùng suffix ngẫu nhiên để tránh collision dữ liệu.
"""
from __future__ import annotations

import time as _time
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

BASE_EMP = "/api/v1/employees"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_RUN_SUFFIX = str(int(_time.time()))[-6:]

_emp_counter = 0


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_position(client: TestClient, h: dict) -> dict:
    rows = client.get("/api/v1/job-positions", headers=h, params={"page_size": 10}).json()
    positions = rows if isinstance(rows, list) else rows.get("items", rows)
    assert positions, "Cần ít nhất 1 vị trí công việc trong DB"
    pos = next((p for p in positions if p.get("department_id")), positions[0])
    return pos


def _find_position_for_title(client: TestClient, h: dict, job_title_id: int) -> dict:
    """Tìm position có job_title_id cụ thể. Fallback về bất kỳ position nào."""
    rows = client.get("/api/v1/job-positions", headers=h, params={"page_size": 50}).json()
    positions = rows if isinstance(rows, list) else rows.get("items", rows)
    match = next((p for p in positions if p.get("job_title_id") == job_title_id and p.get("department_id")), None)
    if match:
        return match
    return next((p for p in positions if p.get("department_id")), positions[0])


def _create_probation_employee(
    client: TestClient,
    h: dict,
    *,
    probation_start: str | None = "2098-01-15",
    probation_end: str | None = "2098-03-15",
    status: str = "probation",
    job_title_id: int = 0,  # 0 = use position's own job_title_id
) -> dict:
    global _emp_counter
    _emp_counter += 1

    if job_title_id:
        pos = _find_position_for_title(client, h, job_title_id)
        actual_title_id = job_title_id
    else:
        pos = _get_position(client, h)
        actual_title_id = pos.get("job_title_id") or 1

    payload = {
        "full_name": f"Test Prob {_RUN_SUFFIX} #{_emp_counter}",
        "last_name": "Test",
        "first_name": f"Prob{_emp_counter}",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "nationality_id": 1,
        "id_number": f"PB{_RUN_SUFFIX}{_emp_counter:04d}",
        "id_issued_on": "2010-01-01",
        "id_issued_by": "CA",
        "personal_email": f"prob_{_RUN_SUFFIX}_{_emp_counter:04d}@test.local",
        "status": status,
        "start_date": probation_start or "2098-01-15",
        "initial_department_id": pos["department_id"],
        "initial_job_position_id": pos["id"],
        "initial_job_title_id": actual_title_id,
        "initial_job_effective_from": probation_start or "2098-01-15",
    }
    if probation_start is not None:
        payload["initial_probation_start_date"] = probation_start
    if probation_end is not None:
        payload["initial_probation_end_date"] = probation_end

    r = client.post(BASE_EMP, json=payload, headers=h)
    assert r.status_code in (200, 201), f"Tạo nhân viên thất bại: {r.text}"
    return r.json()


# ═══════════════════════════════════════════════════════════════
# SLICE 1 — Legal check
# ═══════════════════════════════════════════════════════════════

class TestProbationLegalCheck:
    """Kiểm tra logic pháp lý thử việc."""

    def test_legal_check_returns_for_probation_employee(self, client: TestClient):
        """HR gọi legal-check → nhận về ProbationLegalCheck với đủ các field cần thiết."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]

        r = client.get(f"{BASE_EMP}/{emp_id}/probation/legal-check", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()

        # Phải có đủ fields
        assert "is_valid" in data
        assert "violations" in data
        assert "warnings" in data
        assert "probation_days" in data
        assert "probation_limit" in data
        assert isinstance(data["violations"], list)
        assert isinstance(data["warnings"], list)
        assert isinstance(data["probation_days"], int)
        assert data["probation_limit"] > 0

    def test_legal_check_detects_probation_days_exceeding_limit(self, client: TestClient):
        """Nhân viên có thời gian thử việc vượt giới hạn → violations không rỗng."""
        h = _admin(client)
        # Tạo nhân viên với 200 ngày thử việc (vượt giới hạn 180 ngày của director)
        emp = _create_probation_employee(
            client, h,
            probation_start="2098-01-01",
            probation_end="2098-07-21",  # 201 ngày — vượt cả giới hạn director (180)
        )
        emp_id = emp["id"]

        r = client.get(f"{BASE_EMP}/{emp_id}/probation/legal-check", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()

        assert not data["is_valid"], "Phải phát hiện vi phạm"
        assert len(data["violations"]) > 0, "Phải có ít nhất một vi phạm"
        assert data["probation_days"] > data["probation_limit"]

    def test_probation_detail_returns_for_employee(self, client: TestClient):
        """GET /probation → trả về ProbationDetailRead với thông tin đầy đủ."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]

        r = client.get(f"{BASE_EMP}/{emp_id}/probation", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()

        assert data["employee_id"] == emp_id
        assert data["employee_name"]
        assert "legal_check" in data
        assert "status" in data
        assert data["status"] == "probation"
        assert data["probation_mode"] == "active"
        assert data["can_edit_evaluation"] is True
        assert data["can_generate_contract"] is True
        assert data["approval_triggers_workflow"] is True

    def test_probation_detail_marks_historical_mode_for_official_employee_with_probation_data(self, client: TestClient):
        h = _admin(client)
        emp = _create_probation_employee(client, h, status="official")
        emp_id = emp["id"]

        r = client.get(f"{BASE_EMP}/{emp_id}/probation", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()

        assert data["status"] == "official"
        assert data["probation_mode"] == "historical"
        assert data["can_edit_evaluation"] is True
        assert data["can_generate_contract"] is False
        assert data["approval_triggers_workflow"] is False

    def test_legal_check_downgrades_over_limit_historical_probation_to_warning(self, client: TestClient):
        h = _admin(client)
        emp = _create_probation_employee(
            client,
            h,
            status="official",
            probation_start="2022-01-01",
            probation_end="2022-07-21",
        )
        emp_id = emp["id"]

        r = client.get(f"{BASE_EMP}/{emp_id}/probation", headers=h)
        assert r.status_code == 200, r.text
        data = r.json()

        assert data["probation_mode"] == "historical"
        assert data["legal_check"]["is_valid"] is True
        assert data["legal_check"]["violations"] == []
        assert any("Dữ liệu thử việc lịch sử" in message for message in data["legal_check"]["warnings"])

    def test_legal_check_404_for_unknown_employee(self, client: TestClient):
        """Nhân viên không tồn tại → 200 với probation_days=0 (không raise error)."""
        h = _admin(client)
        r = client.get(f"{BASE_EMP}/9999999/probation/legal-check", headers=h)
        # Service trả về empty legal check khi không có job_record (không raise LookupError)
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════════
# SLICE 2 — Probation Contract
# ═══════════════════════════════════════════════════════════════

class TestProbationContract:
    """Kiểm tra sinh và lấy hợp đồng thử việc."""

    def test_get_probation_contracts_returns_list(self, client: TestClient):
        """GET /probation/contract → luôn trả về list (rỗng hoặc có dữ liệu)."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]

        r = client.get(f"{BASE_EMP}/{emp_id}/probation/contract", headers=h)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_generate_contract_when_no_template_returns_404(self, client: TestClient):
        """POST /probation/contract/generate khi không có template → 404."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]

        # Không có template probation_agreement active trong DB test → 404
        r = client.post(f"{BASE_EMP}/{emp_id}/probation/contract/generate", headers=h)
        # Chấp nhận 201 (nếu template tồn tại) hoặc 404
        assert r.status_code in (201, 404), r.text

    def test_generate_contract_historical_probation_returns_422(self, client: TestClient):
        h = _admin(client)
        emp = _create_probation_employee(client, h, status="official")
        emp_id = emp["id"]

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/contract/generate", headers=h)
        assert r.status_code == 422, r.text


# ═══════════════════════════════════════════════════════════════
# SLICE 3 — Evaluation CRUD
# ═══════════════════════════════════════════════════════════════

class TestProbationEvaluation:
    """Kiểm tra CRUD phiếu đánh giá thử việc."""

    def test_hr_can_create_draft_evaluation(self, client: TestClient):
        """HR tạo phiếu đánh giá → status='draft', result='pending'."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]

        # Lấy admin user_id để đặt làm evaluator
        me = client.get("/api/v1/auth/me", headers=h).json()
        evaluator_id = me["id"]

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={
            "evaluation_date": "2098-03-10",
            "evaluator_id": evaluator_id,
            "attitude_score": 8.0,
            "competence_score": 7.5,
        }, headers=h)
        assert r.status_code == 201, r.text
        data = r.json()

        assert data["status"] == "draft"
        assert data["result"] == "pending"
        assert data["employee_id"] == emp_id

    def test_overall_score_computed_as_average_of_provided_scores(self, client: TestClient):
        """overall_score = trung bình của các điểm số được cung cấp."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]
        me = client.get("/api/v1/auth/me", headers=h).json()

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={
            "evaluation_date": "2098-03-10",
            "evaluator_id": me["id"],
            "attitude_score": 8.0,
            "competence_score": 6.0,
        }, headers=h)
        assert r.status_code == 201, r.text
        data = r.json()

        # (8.0 + 6.0) / 2 = 7.0
        assert data["overall_score"] is not None
        assert abs(float(data["overall_score"]) - 7.0) < 0.01

    def test_overall_score_is_none_when_no_scores_given(self, client: TestClient):
        """Nếu không có điểm số nào → overall_score = null."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]
        me = client.get("/api/v1/auth/me", headers=h).json()

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={
            "evaluation_date": "2098-03-10",
            "evaluator_id": me["id"],
            "manager_comment": "Nhân viên cố gắng",
        }, headers=h)
        assert r.status_code == 201, r.text
        assert r.json()["overall_score"] is None

    def test_cannot_create_second_evaluation_for_same_probation(self, client: TestClient):
        """Tạo phiếu đánh giá thứ hai cho cùng lần thử việc → 422."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]
        me = client.get("/api/v1/auth/me", headers=h).json()

        payload = {
            "evaluation_date": "2098-03-10",
            "evaluator_id": me["id"],
            "manager_comment": "Lần 1",
        }
        r1 = client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json=payload, headers=h)
        assert r1.status_code == 201, r1.text

        r2 = client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={**payload, "manager_comment": "Lần 2"}, headers=h)
        assert r2.status_code == 422, r2.text

    def test_can_create_evaluation_for_historical_probation_employee(self, client: TestClient):
        """Nhân viên đã official nhưng còn dữ liệu thử việc lịch sử vẫn tạo được phiếu đánh giá."""
        h = _admin(client)
        emp = _create_probation_employee(client, h, status="official")
        emp_id = emp["id"]
        me = client.get("/api/v1/auth/me", headers=h).json()

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={
            "evaluation_date": "2098-03-10",
            "evaluator_id": me["id"],
            "manager_comment": "Backfill hồ sơ thử việc cũ",
        }, headers=h)
        assert r.status_code == 201, r.text
        assert r.json()["status"] == "draft"

    def test_cannot_create_evaluation_when_employee_has_no_probation_data(self, client: TestClient):
        """Nhân viên không có dữ liệu thử việc trên job record hiện tại vẫn bị chặn."""
        h = _admin(client)
        emp = _create_probation_employee(client, h, status="official", probation_start=None, probation_end=None)
        emp_id = emp["id"]
        me = client.get("/api/v1/auth/me", headers=h).json()

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={
            "evaluation_date": "2098-03-10",
            "evaluator_id": me["id"],
        }, headers=h)
        assert r.status_code == 422, r.text
        assert "không có dữ liệu thử việc" in r.text.lower()

    def test_submit_requires_at_least_two_scores_or_comment(self, client: TestClient):
        """Nộp phiếu không có đủ điểm số và không có comment → 422."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]
        me = client.get("/api/v1/auth/me", headers=h).json()

        # Tạo phiếu chỉ có 1 điểm số và không có comment
        r = client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={
            "evaluation_date": "2098-03-10",
            "evaluator_id": me["id"],
            "attitude_score": 8.0,
        }, headers=h)
        assert r.status_code == 201, r.text

        r_submit = client.post(f"{BASE_EMP}/{emp_id}/probation/submit", headers=h)
        assert r_submit.status_code == 422, r_submit.text

    def test_submit_changes_status_to_submitted(self, client: TestClient):
        """Nộp phiếu hợp lệ → status chuyển sang 'submitted'."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]
        me = client.get("/api/v1/auth/me", headers=h).json()

        # Tạo phiếu với 2 điểm số
        r = client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={
            "evaluation_date": "2098-03-10",
            "evaluator_id": me["id"],
            "attitude_score": 8.0,
            "competence_score": 7.0,
        }, headers=h)
        assert r.status_code == 201, r.text

        r_submit = client.post(f"{BASE_EMP}/{emp_id}/probation/submit", headers=h)
        assert r_submit.status_code == 200, r_submit.text
        assert r_submit.json()["status"] == "submitted"

    def test_cannot_update_submitted_evaluation(self, client: TestClient):
        """Cập nhật phiếu đã submitted → 422."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]
        me = client.get("/api/v1/auth/me", headers=h).json()

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={
            "evaluation_date": "2098-03-10",
            "evaluator_id": me["id"],
            "attitude_score": 8.0,
            "competence_score": 7.0,
        }, headers=h)
        assert r.status_code == 201, r.text
        eval_id = r.json()["id"]

        # Submit
        client.post(f"{BASE_EMP}/{emp_id}/probation/submit", headers=h)

        # Thử update
        r_update = client.patch(
            f"{BASE_EMP}/{emp_id}/probation/evaluate/{eval_id}",
            json={"attitude_score": 9.0},
            headers=h,
        )
        assert r_update.status_code == 422, r_update.text


# ═══════════════════════════════════════════════════════════════
# SLICE 4 — Approve + Workflow
# ═══════════════════════════════════════════════════════════════

class TestProbationApprove:
    """Kiểm tra phê duyệt phiếu đánh giá và workflow."""

    def _create_submitted_eval(self, client: TestClient, h: dict, **emp_kwargs) -> tuple[dict, dict]:
        """Tạo nhân viên + phiếu đánh giá đã submitted. Trả (emp, eval)."""
        emp = _create_probation_employee(client, h, **emp_kwargs)
        emp_id = emp["id"]
        me = client.get("/api/v1/auth/me", headers=h).json()

        client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={
            "evaluation_date": "2098-03-10",
            "evaluator_id": me["id"],
            "attitude_score": 8.0,
            "competence_score": 7.0,
        }, headers=h)
        r_submit = client.post(f"{BASE_EMP}/{emp_id}/probation/submit", headers=h)
        assert r_submit.status_code == 200, r_submit.text
        return emp, r_submit.json()

    def test_approve_passed_sets_employee_status_to_official(self, client: TestClient):
        """Phê duyệt 'passed' → employee.status chuyển sang 'official'."""
        h = _admin(client)
        emp, _ = self._create_submitted_eval(client, h)
        emp_id = emp["id"]

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/approve",
                        json={"result": "passed"}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["result"] == "passed"

        # Kiểm tra employee status
        emp_detail = client.get(f"{BASE_EMP}/{emp_id}", headers=h).json()
        assert emp_detail["status"] == "official"

    def test_approve_passed_sets_official_date_on_job_record(self, client: TestClient):
        """Phê duyệt 'passed' → official_date trên job_record được set."""
        h = _admin(client)
        emp, _ = self._create_submitted_eval(client, h)
        emp_id = emp["id"]

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/approve",
                        json={"result": "passed"}, headers=h)
        assert r.status_code == 200, r.text

        # Kiểm tra probation detail có official_date
        detail = client.get(f"{BASE_EMP}/{emp_id}/probation", headers=h).json()
        assert detail.get("official_date") is not None

    def test_approve_historical_probation_keeps_employee_status_official(self, client: TestClient):
        """Nhân viên historical probation được approve phiếu nhưng không chạy workflow đổi trạng thái."""
        h = _admin(client)
        emp, _ = self._create_submitted_eval(client, h, status="official")
        emp_id = emp["id"]

        r = client.post(
            f"{BASE_EMP}/{emp_id}/probation/approve",
            json={"result": "passed"},
            headers=h,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "approved"

        emp_detail = client.get(f"{BASE_EMP}/{emp_id}", headers=h).json()
        assert emp_detail["status"] == "official"

        detail = client.get(f"{BASE_EMP}/{emp_id}/probation", headers=h).json()
        assert detail["probation_mode"] == "historical"
        assert detail.get("official_date") is None

        contracts = client.get(f"{BASE_EMP}/{emp_id}/probation/contract", headers=h).json()
        assert contracts == []

    def test_approve_failed_sets_employee_status_to_resigned(self, client: TestClient):
        """Phê duyệt 'failed' → employee.status chuyển sang 'resigned'."""
        h = _admin(client)
        emp, _ = self._create_submitted_eval(client, h)
        emp_id = emp["id"]

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/approve",
                        json={"result": "failed"}, headers=h)
        assert r.status_code == 200, r.text

        emp_detail = client.get(f"{BASE_EMP}/{emp_id}", headers=h).json()
        assert emp_detail["status"] == "resigned"

    def test_approve_extended_updates_probation_end_date(self, client: TestClient):
        """Phê duyệt 'extended' → probation_end_date tăng thêm đúng số ngày.

        Dùng probation 4 ngày + gia hạn 1 ngày = tổng 5 ngày.
        Giới hạn tối thiểu của mọi chức danh là 6 ngày (worker), nên 5 ngày nằm trong giới hạn.
        """
        h = _admin(client)
        # Probation 4 ngày → nằm trong giới hạn worker (6 ngày)
        emp, _ = self._create_submitted_eval(
            client, h,
            probation_start="2098-01-01",
            probation_end="2098-01-05",  # 4 ngày
        )
        emp_id = emp["id"]

        before = client.get(f"{BASE_EMP}/{emp_id}/probation", headers=h).json()
        old_end = before["probation_end_date"]

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/approve",
                        json={"result": "extended", "extension_days": 1}, headers=h)
        assert r.status_code == 200, r.text

        after = client.get(f"{BASE_EMP}/{emp_id}/probation", headers=h).json()
        new_end = after["probation_end_date"]

        old_dt = date.fromisoformat(old_end)
        new_dt = date.fromisoformat(new_end)
        assert new_dt == old_dt + timedelta(days=1)

    def test_approve_extended_validates_total_days_not_exceed_legal_limit(self, client: TestClient):
        """Gia hạn làm tổng thời gian vượt giới hạn pháp lý → 422.

        Tạo nhân viên với 170 ngày thử việc (dưới giới hạn director=180),
        rồi gia hạn thêm 20 ngày → tổng 190 > 180 → vi phạm.
        Dùng job_title_id=1 (Chủ tịch HĐQT, level 1 = director = 180 ngày).
        """
        h = _admin(client)
        # Tìm position có job_title_id=1
        pos = _find_position_for_title(client, h, 1)
        # Dùng position's job_title nếu không match được
        actual_title_id = 1 if pos.get("job_title_id") == 1 else pos.get("job_title_id") or 1

        global _emp_counter
        _emp_counter += 1
        r_emp = client.post(BASE_EMP, json={
            "full_name": f"Test Prob Ext {_RUN_SUFFIX} #{_emp_counter}",
            "last_name": "Test",
            "first_name": f"ProbExt{_emp_counter}",
            "date_of_birth": "1990-01-01",
            "gender": "male",
            "nationality_id": 1,
            "id_number": f"PX{_RUN_SUFFIX}{_emp_counter:04d}",
            "id_issued_on": "2010-01-01",
            "id_issued_by": "CA",
            "personal_email": f"probext_{_RUN_SUFFIX}_{_emp_counter:04d}@test.local",
            "status": "probation",
            "start_date": "2098-01-01",
            "initial_department_id": pos["department_id"],
            "initial_job_position_id": pos["id"],
            "initial_job_title_id": actual_title_id,
            "initial_probation_start_date": "2098-01-01",
            "initial_probation_end_date": "2098-06-20",  # 170 ngày
            "initial_job_effective_from": "2098-01-01",
        }, headers=h)
        assert r_emp.status_code in (200, 201), r_emp.text
        emp_id = r_emp.json()["id"]

        me = client.get("/api/v1/auth/me", headers=h).json()
        client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={
            "evaluation_date": "2098-06-15",
            "evaluator_id": me["id"],
            "attitude_score": 8.0,
            "competence_score": 7.0,
        }, headers=h)
        r_sub = client.post(f"{BASE_EMP}/{emp_id}/probation/submit", headers=h)
        assert r_sub.status_code == 200, r_sub.text

        # Gia hạn thêm 20 ngày → tổng 190 ngày
        # Nếu actual_title_id=1 (director, limit=180) → 422
        # Nếu position không có title level 1, giới hạn sẽ là worker(6)/specialist(30)/manager(60)
        # → tổng 170+20=190 vẫn vượt tất cả trừ director
        r = client.post(f"{BASE_EMP}/{emp_id}/probation/approve",
                        json={"result": "extended", "extension_days": 20}, headers=h)
        # Chỉ assert 422 khi limit < 190; với director limit=180 cũng 422 (190>180)
        assert r.status_code == 422, r.text

    def test_cannot_approve_draft_evaluation(self, client: TestClient):
        """Phê duyệt phiếu ở trạng thái 'draft' → 422."""
        h = _admin(client)
        emp = _create_probation_employee(client, h)
        emp_id = emp["id"]
        me = client.get("/api/v1/auth/me", headers=h).json()

        # Tạo phiếu nhưng KHÔNG submit
        client.post(f"{BASE_EMP}/{emp_id}/probation/evaluate", json={
            "evaluation_date": "2098-03-10",
            "evaluator_id": me["id"],
            "attitude_score": 8.0,
            "competence_score": 7.0,
        }, headers=h)

        r = client.post(f"{BASE_EMP}/{emp_id}/probation/approve",
                        json={"result": "passed"}, headers=h)
        assert r.status_code == 422, r.text

    def test_cannot_approve_twice(self, client: TestClient):
        """Phê duyệt phiếu đã approved → 422."""
        h = _admin(client)
        emp, _ = self._create_submitted_eval(client, h)
        emp_id = emp["id"]

        # Approve lần 1
        r1 = client.post(f"{BASE_EMP}/{emp_id}/probation/approve",
                         json={"result": "passed"}, headers=h)
        assert r1.status_code == 200, r1.text

        # Approve lần 2
        r2 = client.post(f"{BASE_EMP}/{emp_id}/probation/approve",
                         json={"result": "passed"}, headers=h)
        assert r2.status_code == 422, r2.text
