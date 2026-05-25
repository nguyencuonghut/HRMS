"""Integration tests — Plan 13.4: Recruitment Pipeline."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient

BASE_CAND = "/api/v1/recruitment/candidates"
BASE_JR = "/api/v1/recruitment/job-requisitions"
BASE_PIPELINE_TEMPLATES = "/api/v1/recruitment/pipeline-templates"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_dept_id(client: TestClient, h: dict) -> int:
    items = client.get("/api/v1/departments", headers=h, params={"page_size": 1}).json()
    rows = items if isinstance(items, list) else items.get("items", items)
    return rows[0]["id"]


def _get_pos_id(client: TestClient, h: dict) -> int:
    items = client.get("/api/v1/job-positions", headers=h, params={"page_size": 1}).json()
    rows = items if isinstance(items, list) else items.get("items", items)
    return rows[0]["id"]


def _create_approved_jr(client: TestClient, h: dict, suffix: str) -> dict:
    jr = client.post(
        BASE_JR,
        json={
            "job_position_id": _get_pos_id(client, h),
            "department_id": _get_dept_id(client, h),
            "quantity": 1,
            "reason_type": "new",
            "internal_note": suffix,
        },
        headers=h,
    ).json()
    client.post(f"{BASE_JR}/{jr['id']}/submit", headers=h)
    client.post(f"{BASE_JR}/{jr['id']}/approve", headers=h)
    return client.get(f"{BASE_JR}/{jr['id']}", headers=h).json()


def _create_candidate(client: TestClient, h: dict, suffix: str) -> dict:
    res = client.post(
        BASE_CAND,
        json={
            "full_name": f"Ứng viên Pipeline {suffix}",
            "personal_email": f"pipeline_{suffix}@example.com",
        },
        headers=h,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _setup_pipeline(client: TestClient, h: dict, jr_id: int, stages: list[dict]) -> list[dict]:
    res = client.post(
        f"{BASE_JR}/{jr_id}/pipeline",
        json={"stages": stages},
        headers=h,
    )
    assert res.status_code == 200, res.text
    return res.json()


class TestRecruitmentPipeline:
    def test_pipeline_template_and_setup_for_jr(self, client: TestClient) -> None:
        h = _admin(client)
        token = uuid.uuid4().hex[:8]
        template_res = client.post(
            BASE_PIPELINE_TEMPLATES,
            json={
                "name": f"Template Pipeline {token}",
                "job_position_id": _get_pos_id(client, h),
                "items": [
                    {"stage_order": 1, "stage_name": "Sàng lọc CV", "stage_type": "screening"},
                    {"stage_order": 2, "stage_name": "Phỏng vấn HR", "stage_type": "interview"},
                    {"stage_order": 3, "stage_name": "Vòng cuối", "stage_type": "final"},
                ],
            },
            headers=h,
        )
        assert template_res.status_code == 201, template_res.text
        template = template_res.json()

        list_res = client.get(BASE_PIPELINE_TEMPLATES, headers=h)
        assert list_res.status_code == 200
        assert any(item["id"] == template["id"] for item in list_res.json())

        jr = _create_approved_jr(client, h, token)
        setup_res = client.post(
            f"{BASE_JR}/{jr['id']}/pipeline",
            json={"template_id": template["id"]},
            headers=h,
        )
        assert setup_res.status_code == 200, setup_res.text
        stages = setup_res.json()
        assert [stage["stage_type"] for stage in stages] == ["screening", "interview", "final"]

        candidate = _create_candidate(client, h, token)
        app_res = client.post(
            f"{BASE_CAND}/{candidate['id']}/apply",
            json={"job_requisition_id": jr["id"], "applied_date": str(date.today())},
            headers=h,
        )
        assert app_res.status_code == 201, app_res.text
        assert app_res.json()["current_stage"] == "screening"

    def test_update_pipeline_template_replaces_stage_items(self, client: TestClient) -> None:
        h = _admin(client)
        token = uuid.uuid4().hex[:8]
        template_res = client.post(
            BASE_PIPELINE_TEMPLATES,
            json={
                "name": f"Template Update {token}",
                "items": [
                    {"stage_order": 1, "stage_name": "Sàng lọc", "stage_type": "screening"},
                    {"stage_order": 2, "stage_name": "Phỏng vấn", "stage_type": "interview"},
                ],
            },
            headers=h,
        )
        assert template_res.status_code == 201, template_res.text
        template = template_res.json()

        update_res = client.put(
            f"{BASE_PIPELINE_TEMPLATES}/{template['id']}",
            json={
                "name": f"Template Update 2 {token}",
                "items": [
                    {"stage_order": 1, "stage_name": "Bài test", "stage_type": "test"},
                    {"stage_order": 2, "stage_name": "Vòng cuối", "stage_type": "final"},
                ],
            },
            headers=h,
        )
        assert update_res.status_code == 200, update_res.text
        payload = update_res.json()
        assert payload["name"] == f"Template Update 2 {token}"
        assert [item["stage_type"] for item in payload["items"]] == ["test", "final"]

    def test_advance_hold_reject_and_kanban(self, client: TestClient) -> None:
        h = _admin(client)
        token = uuid.uuid4().hex[:8]
        jr = _create_approved_jr(client, h, token)
        stages = _setup_pipeline(
            client,
            h,
            jr["id"],
            [
                {"stage_order": 1, "stage_name": "Screening", "stage_type": "screening"},
                {"stage_order": 2, "stage_name": "Test", "stage_type": "test"},
                {"stage_order": 3, "stage_name": "Final", "stage_type": "final"},
            ],
        )
        screening_stage = stages[0]
        test_stage = stages[1]

        candidate = _create_candidate(client, h, token)
        app = client.post(
            f"{BASE_CAND}/{candidate['id']}/apply",
            json={"job_requisition_id": jr["id"], "applied_date": str(date.today())},
            headers=h,
        ).json()

        kanban_before = client.get(f"{BASE_JR}/{jr['id']}/kanban", headers=h).json()
        screening_column = next(stage for stage in kanban_before["stages"] if stage["stage"]["stage_type"] == "screening")
        assert any(card["application_id"] == app["id"] for card in screening_column["applications"])

        hold_res = client.post(
            f"/api/v1/recruitment/applications/{app['id']}/hold",
            json={"stage_id": screening_stage["id"], "notes": "Chờ bổ sung hồ sơ"},
            headers=h,
        )
        assert hold_res.status_code == 200, hold_res.text
        assert hold_res.json()["current_stage"] == "screening"

        advance_res = client.post(
            f"/api/v1/recruitment/applications/{app['id']}/advance",
            json={"stage_id": screening_stage["id"], "result": "pass", "notes": "CV phù hợp"},
            headers=h,
        )
        assert advance_res.status_code == 200, advance_res.text
        assert advance_res.json()["current_stage"] == "test"

        reject_res = client.post(
            f"/api/v1/recruitment/applications/{app['id']}/advance",
            json={
                "stage_id": test_stage["id"],
                "result": "fail",
                "rejection_reason": "Không đạt bài test",
            },
            headers=h,
        )
        assert reject_res.status_code == 200, reject_res.text
        assert reject_res.json()["current_stage"] == "rejected"
        assert reject_res.json()["rejection_reason"] == "Không đạt bài test"

        stage_results_res = client.get(
            f"/api/v1/recruitment/applications/{app['id']}/stages",
            headers=h,
        )
        assert stage_results_res.status_code == 200
        stage_results = stage_results_res.json()
        assert any(item["stage_id"] == screening_stage["id"] and item["result"] == "pass" for item in stage_results)
        assert any(item["stage_id"] == test_stage["id"] and item["result"] == "fail" for item in stage_results)

    def test_interview_flow_updates_stage_result(self, client: TestClient) -> None:
        h = _admin(client)
        token = uuid.uuid4().hex[:8]
        jr = _create_approved_jr(client, h, token)
        stages = _setup_pipeline(
            client,
            h,
            jr["id"],
            [
                {"stage_order": 1, "stage_name": "Screening", "stage_type": "screening"},
                {"stage_order": 2, "stage_name": "Phỏng vấn", "stage_type": "interview"},
                {"stage_order": 3, "stage_name": "Final", "stage_type": "final"},
            ],
        )
        screening_stage = stages[0]
        interview_stage = stages[1]

        candidate = _create_candidate(client, h, token)
        app = client.post(
            f"{BASE_CAND}/{candidate['id']}/apply",
            json={"job_requisition_id": jr["id"], "applied_date": str(date.today())},
            headers=h,
        ).json()

        client.post(
            f"/api/v1/recruitment/applications/{app['id']}/advance",
            json={"stage_id": screening_stage["id"], "result": "pass"},
            headers=h,
        )

        scheduled_at = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0).isoformat()
        interview_res = client.post(
            f"/api/v1/recruitment/applications/{app['id']}/interviews",
            json={
                "stage_id": interview_stage["id"],
                "scheduled_at": scheduled_at,
                "duration_minutes": 45,
                "format": "online",
                "location": "https://meet.example.com/test",
                "panelist_user_ids": [1],
            },
            headers=h,
        )
        assert interview_res.status_code == 201, interview_res.text
        interview = interview_res.json()
        assert interview["stage_id"] == interview_stage["id"]
        assert len(interview["panelists"]) == 1

        list_interviews_res = client.get(
            f"/api/v1/recruitment/applications/{app['id']}/interviews",
            headers=h,
        )
        assert list_interviews_res.status_code == 200
        assert any(item["id"] == interview["id"] for item in list_interviews_res.json())

        score_res = client.post(
            f"/api/v1/recruitment/interviews/{interview['id']}/panelists/1/score",
            json={
                "criteria_scores": [{"criterion": "Giao tiếp", "score": 4, "max_score": 5}],
                "result": "pass",
                "private_notes": "Ổn",
            },
            headers=h,
        )
        assert score_res.status_code == 200, score_res.text
        assert score_res.json()["result"] == "pass"

        complete_res = client.post(
            f"/api/v1/recruitment/interviews/{interview['id']}/complete",
            headers=h,
        )
        assert complete_res.status_code == 200, complete_res.text
        assert complete_res.json()["status"] == "completed"

        stage_results_res = client.get(
            f"/api/v1/recruitment/applications/{app['id']}/stages",
            headers=h,
        )
        assert stage_results_res.status_code == 200
        assert any(
            item["stage_id"] == interview_stage["id"] and item["result"] == "pass"
            for item in stage_results_res.json()
        )

    def test_interview_kit_endpoints(self, client: TestClient) -> None:
        h = _admin(client)
        token = uuid.uuid4().hex[:8]
        pos_id = _get_pos_id(client, h)

        question_res = client.post(
            "/api/v1/recruitment/questions",
            json={
                "question_text": f"Bạn xử lý xung đột thế nào? {token}",
                "category": "Hành vi",
                "difficulty": "medium",
                "job_position_id": pos_id,
                "stage_type": "interview",
            },
            headers=h,
        )
        assert question_res.status_code == 201, question_res.text
        question = question_res.json()

        update_question_res = client.put(
            f"/api/v1/recruitment/questions/{question['id']}",
            json={"category": "Tình huống"},
            headers=h,
        )
        assert update_question_res.status_code == 200
        assert update_question_res.json()["category"] == "Tình huống"

        list_questions_res = client.get(
            "/api/v1/recruitment/questions",
            params={"job_position_id": pos_id, "stage_type": "interview"},
            headers=h,
        )
        assert list_questions_res.status_code == 200
        assert any(item["id"] == question["id"] for item in list_questions_res.json())

        criterion_res = client.post(
            "/api/v1/recruitment/scorecard-criteria",
            json={
                "name": f"Kỹ năng giao tiếp {token}",
                "job_position_id": pos_id,
                "stage_type": "interview",
                "max_score": 5,
                "sort_order": 1,
            },
            headers=h,
        )
        assert criterion_res.status_code == 201, criterion_res.text
        criterion = criterion_res.json()

        list_criteria_res = client.get(
            "/api/v1/recruitment/scorecard-criteria",
            params={"job_position_id": pos_id, "stage_type": "interview"},
            headers=h,
        )
        assert list_criteria_res.status_code == 200
        assert any(item["id"] == criterion["id"] for item in list_criteria_res.json())

        delete_question_res = client.delete(
            f"/api/v1/recruitment/questions/{question['id']}",
            headers=h,
        )
        assert delete_question_res.status_code == 204
