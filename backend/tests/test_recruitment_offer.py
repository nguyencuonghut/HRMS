"""Integration tests — Plan 13.5: Offer & Quyết định tuyển dụng."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

BASE_CAND = "/api/v1/recruitment/candidates"
BASE_JR = "/api/v1/recruitment/job-requisitions"
BASE_OFFERS = "/api/v1/recruitment/offers"
BASE_HD = "/api/v1/recruitment/hiring-decisions"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_NATIONALITY_ID = 1374


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_pos_dept(client: TestClient, h: dict) -> tuple[int, int]:
    """Returns (job_position_id, department_id) where position belongs to department."""
    items = client.get("/api/v1/job-positions", headers=h, params={"page_size": 50}).json()
    rows = items if isinstance(items, list) else items.get("items", items)
    row = rows[0]
    return row["id"], row["department_id"]


def _get_dept_id(client: TestClient, h: dict) -> int:
    return _get_pos_dept(client, h)[1]


def _get_pos_id(client: TestClient, h: dict) -> int:
    return _get_pos_dept(client, h)[0]


def _create_approved_jr(client: TestClient, h: dict, pos_id: int, dept_id: int, qty: int = 1) -> dict:
    jr = client.post(
        BASE_JR,
        json={
            "job_position_id": pos_id,
            "department_id": dept_id,
            "quantity": qty,
            "reason_type": "new",
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
            "full_name": f"Ứng Viên Offer {suffix}",
            "personal_email": f"offer_{suffix}@example.com",
        },
        headers=h,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_candidate_full(client: TestClient, h: dict, suffix: str) -> dict:
    """Candidate with all fields required for convert_to_employee."""
    res = client.post(
        BASE_CAND,
        json={
            "full_name": f"Ứng Viên Convert {suffix}",
            "last_name": "Ứng Viên",
            "first_name": suffix,
            "personal_email": f"convert_{suffix}@example.com",
            "date_of_birth": "1990-01-01",
            "gender": "male",
            "nationality_id": _NATIONALITY_ID,
            "id_number": f"0{suffix[:9]}",
            "id_issued_on": "2015-01-01",
            "id_issued_by": "Cục CSQLHC",
        },
        headers=h,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _apply(client: TestClient, h: dict, candidate_id: int, jr_id: int) -> dict:
    res = client.post(
        f"{BASE_CAND}/{candidate_id}/apply",
        json={"job_requisition_id": jr_id, "applied_date": str(date.today())},
        headers=h,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_offer(client: TestClient, h: dict, application_id: int, pos_id: int | None = None, dept_id: int | None = None, **overrides) -> dict:
    if pos_id is None:
        pos_id = _get_pos_id(client, h)
    if dept_id is None:
        dept_id = _get_dept_id(client, h)
    payload = {
        "job_position_id": pos_id,
        "department_id": dept_id,
        "proposed_start_date": str(date.today() + timedelta(days=14)),
        "probation_salary": 8000000,
        "official_salary": 10000000,
        "probation_days": 30,
        "expires_at": str(date.today() + timedelta(days=7)),
    }
    payload.update(overrides)
    res = client.post(
        f"/api/v1/recruitment/applications/{application_id}/offers",
        json=payload,
        headers=h,
    )
    assert res.status_code == 201, res.text
    return res.json()


# ── TestOfferCRUD ──────────────────────────────────────────────────────────────

class TestOfferCRUD:
    def test_create_offer_draft(self, client: TestClient) -> None:
        h = _admin(client)
        suffix = uuid.uuid4().hex[:8]
        pos_id = _get_pos_id(client, h)
        dept_id = _get_dept_id(client, h)
        jr = _create_approved_jr(client, h, pos_id, dept_id)
        cand = _create_candidate(client, h, suffix)
        app = _apply(client, h, cand["id"], jr["id"])

        offer = _create_offer(client, h, app["id"])
        assert offer["status"] == "draft"
        assert offer["candidate_id"] == cand["id"]
        assert offer["application_id"] == app["id"]

    def test_create_offer_duplicate_active_returns_409(self, client: TestClient) -> None:
        h = _admin(client)
        suffix = uuid.uuid4().hex[:8]
        pos_id, dept_id = _get_pos_dept(client, h)
        jr = _create_approved_jr(client, h, pos_id, dept_id)
        cand = _create_candidate(client, h, suffix)
        app = _apply(client, h, cand["id"], jr["id"])

        _create_offer(client, h, app["id"], pos_id=pos_id, dept_id=dept_id)
        res2 = client.post(
            f"/api/v1/recruitment/applications/{app['id']}/offers",
            json={
                "job_position_id": pos_id,
                "department_id": dept_id,
                "proposed_start_date": str(date.today() + timedelta(days=14)),
                "probation_salary": 8000000,
                "official_salary": 10000000,
                "probation_days": 30,
            },
            headers=h,
        )
        assert res2.status_code == 409

    def test_update_offer_draft(self, client: TestClient) -> None:
        h = _admin(client)
        suffix = uuid.uuid4().hex[:8]
        pos_id = _get_pos_id(client, h)
        dept_id = _get_dept_id(client, h)
        jr = _create_approved_jr(client, h, pos_id, dept_id)
        cand = _create_candidate(client, h, suffix)
        app = _apply(client, h, cand["id"], jr["id"])
        offer = _create_offer(client, h, app["id"])

        res = client.put(
            f"{BASE_OFFERS}/{offer['id']}",
            json={"official_salary": 12000000},
            headers=h,
        )
        assert res.status_code == 200
        assert float(res.json()["official_salary"]) == 12000000

    def test_list_offers_for_application(self, client: TestClient) -> None:
        h = _admin(client)
        suffix = uuid.uuid4().hex[:8]
        pos_id = _get_pos_id(client, h)
        dept_id = _get_dept_id(client, h)
        jr = _create_approved_jr(client, h, pos_id, dept_id)
        cand = _create_candidate(client, h, suffix)
        app = _apply(client, h, cand["id"], jr["id"])
        _create_offer(client, h, app["id"])

        res = client.get(f"/api/v1/recruitment/applications/{app['id']}/offers", headers=h)
        assert res.status_code == 200
        assert len(res.json()) >= 1


# ── TestOfferProbationValidation ──────────────────────────────────────────────

class TestOfferProbationValidation:
    def _setup(self, client: TestClient, h: dict):
        suffix = uuid.uuid4().hex[:8]
        pos_id = _get_pos_id(client, h)
        dept_id = _get_dept_id(client, h)
        jr = _create_approved_jr(client, h, pos_id, dept_id)
        cand = _create_candidate(client, h, suffix)
        app = _apply(client, h, cand["id"], jr["id"])
        return app

    def test_probation_salary_warning_below_85_percent(self, client: TestClient) -> None:
        h = _admin(client)
        app = self._setup(client, h)
        # 8_000_000 / 10_000_000 = 80% → warning
        offer = _create_offer(
            client, h, app["id"],
            probation_salary=8000000,
            official_salary=10000000,
        )
        assert offer["probation_salary_warning"] is True

    def test_probation_salary_ok_at_85_percent(self, client: TestClient) -> None:
        h = _admin(client)
        app = self._setup(client, h)
        # 8_500_000 / 10_000_000 = 85% → no warning
        offer = _create_offer(
            client, h, app["id"],
            probation_salary=8500000,
            official_salary=10000000,
        )
        assert offer["probation_salary_warning"] is False

    def test_probation_days_warning_over_limit(self, client: TestClient) -> None:
        h = _admin(client)
        app = self._setup(client, h)
        # 61 ngày > giới hạn 60 (manager) hoặc 30 (specialist/worker) → warning
        offer = _create_offer(
            client, h, app["id"],
            probation_days=61,
        )
        # Warning phụ thuộc vào job_title level; nếu pos không có title → worker=6 ngày
        # Nên 61 > 6 → True
        assert offer["probation_days_warning"] is True

    def test_probation_days_limit_computed(self, client: TestClient) -> None:
        h = _admin(client)
        app = self._setup(client, h)
        offer = _create_offer(client, h, app["id"])
        # probation_days_limit phải là số dương hợp lệ
        assert offer["probation_days_limit"] in (180, 60, 30, 6)


# ── TestOfferWorkflow ──────────────────────────────────────────────────────────

class TestOfferWorkflow:
    def _setup(self, client: TestClient, h: dict):
        suffix = uuid.uuid4().hex[:8]
        pos_id = _get_pos_id(client, h)
        dept_id = _get_dept_id(client, h)
        jr = _create_approved_jr(client, h, pos_id, dept_id)
        cand = _create_candidate(client, h, suffix)
        app = _apply(client, h, cand["id"], jr["id"])
        offer = _create_offer(client, h, app["id"])
        return offer, jr

    def test_send_offer(self, client: TestClient) -> None:
        h = _admin(client)
        offer, _ = self._setup(client, h)
        res = client.post(f"{BASE_OFFERS}/{offer['id']}/send", headers=h)
        assert res.status_code == 200
        assert res.json()["status"] == "sent"
        assert res.json()["sent_at"] is not None

    def test_accept_offer_updates_application_stage(self, client: TestClient) -> None:
        h = _admin(client)
        offer, _ = self._setup(client, h)
        client.post(f"{BASE_OFFERS}/{offer['id']}/send", headers=h)
        res = client.post(f"{BASE_OFFERS}/{offer['id']}/accept", headers=h)
        assert res.status_code == 200
        assert res.json()["status"] == "accepted"

    def test_reject_offer(self, client: TestClient) -> None:
        h = _admin(client)
        offer, _ = self._setup(client, h)
        client.post(f"{BASE_OFFERS}/{offer['id']}/send", headers=h)
        res = client.post(
            f"{BASE_OFFERS}/{offer['id']}/reject",
            json={"rejection_reason": "Lương không phù hợp"},
            headers=h,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "rejected"
        assert res.json()["rejection_reason"] == "Lương không phù hợp"

    def test_negotiate_offer(self, client: TestClient) -> None:
        h = _admin(client)
        offer, _ = self._setup(client, h)
        client.post(f"{BASE_OFFERS}/{offer['id']}/send", headers=h)
        res = client.post(
            f"{BASE_OFFERS}/{offer['id']}/negotiate",
            json={"negotiation_note": "Đề xuất tăng lương 5%"},
            headers=h,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "negotiating"

    def test_cannot_send_non_draft_offer(self, client: TestClient) -> None:
        h = _admin(client)
        offer, _ = self._setup(client, h)
        client.post(f"{BASE_OFFERS}/{offer['id']}/send", headers=h)
        res = client.post(f"{BASE_OFFERS}/{offer['id']}/send", headers=h)
        assert res.status_code == 409

    def test_cannot_update_sent_offer(self, client: TestClient) -> None:
        h = _admin(client)
        offer, _ = self._setup(client, h)
        client.post(f"{BASE_OFFERS}/{offer['id']}/send", headers=h)
        res = client.put(
            f"{BASE_OFFERS}/{offer['id']}",
            json={"official_salary": 15000000},
            headers=h,
        )
        assert res.status_code == 409


# ── TestHiringDecision ─────────────────────────────────────────────────────────

class TestHiringDecision:
    def _setup_accepted_offer(self, client: TestClient, h: dict):
        suffix = uuid.uuid4().hex[:8]
        pos_id = _get_pos_id(client, h)
        dept_id = _get_dept_id(client, h)
        jr = _create_approved_jr(client, h, pos_id, dept_id)
        cand = _create_candidate(client, h, suffix)
        app = _apply(client, h, cand["id"], jr["id"])
        offer = _create_offer(client, h, app["id"])
        client.post(f"{BASE_OFFERS}/{offer['id']}/send", headers=h)
        client.post(f"{BASE_OFFERS}/{offer['id']}/accept", headers=h)
        return offer, jr, pos_id, dept_id

    def test_create_hiring_decision(self, client: TestClient) -> None:
        h = _admin(client)
        offer, jr, pos_id, dept_id = self._setup_accepted_offer(client, h)
        res = client.post(
            f"{BASE_OFFERS}/{offer['id']}/hiring-decision",
            json={
                "signed_date": str(date.today()),
                "department_id": dept_id,
                "job_position_id": pos_id,
                "start_date": str(date.today() + timedelta(days=14)),
                "probation_salary": 8000000,
                "official_salary": 10000000,
                "probation_days": 30,
            },
            headers=h,
        )
        assert res.status_code == 201, res.text
        hd = res.json()
        assert hd["status"] == "pending"
        assert hd["offer_id"] == offer["id"]

    def test_cannot_create_decision_for_non_accepted_offer(self, client: TestClient) -> None:
        h = _admin(client)
        suffix = uuid.uuid4().hex[:8]
        pos_id = _get_pos_id(client, h)
        dept_id = _get_dept_id(client, h)
        jr = _create_approved_jr(client, h, pos_id, dept_id)
        cand = _create_candidate(client, h, suffix)
        app = _apply(client, h, cand["id"], jr["id"])
        offer = _create_offer(client, h, app["id"])
        # offer is still draft
        res = client.post(
            f"{BASE_OFFERS}/{offer['id']}/hiring-decision",
            json={
                "signed_date": str(date.today()),
                "department_id": dept_id,
                "job_position_id": pos_id,
                "start_date": str(date.today() + timedelta(days=14)),
                "probation_salary": 8000000,
                "official_salary": 10000000,
                "probation_days": 30,
            },
            headers=h,
        )
        assert res.status_code == 409

    def test_get_hiring_decision_for_offer(self, client: TestClient) -> None:
        h = _admin(client)
        offer, jr, pos_id, dept_id = self._setup_accepted_offer(client, h)
        client.post(
            f"{BASE_OFFERS}/{offer['id']}/hiring-decision",
            json={
                "signed_date": str(date.today()),
                "department_id": dept_id,
                "job_position_id": pos_id,
                "start_date": str(date.today() + timedelta(days=14)),
                "probation_salary": 8000000,
                "official_salary": 10000000,
                "probation_days": 30,
            },
            headers=h,
        )
        res = client.get(f"{BASE_OFFERS}/{offer['id']}/hiring-decision", headers=h)
        assert res.status_code == 200
        assert res.json()["offer_id"] == offer["id"]


# ── TestConvertToEmployee ──────────────────────────────────────────────────────

class TestConvertToEmployee:
    def _setup_decision(self, client: TestClient, h: dict):
        suffix = uuid.uuid4().hex[:8]
        pos_id, dept_id = _get_pos_dept(client, h)
        jr = _create_approved_jr(client, h, pos_id, dept_id)
        cand = _create_candidate_full(client, h, suffix[:6])
        app = _apply(client, h, cand["id"], jr["id"])
        offer = _create_offer(client, h, app["id"], pos_id=pos_id, dept_id=dept_id)
        client.post(f"{BASE_OFFERS}/{offer['id']}/send", headers=h)
        client.post(f"{BASE_OFFERS}/{offer['id']}/accept", headers=h)
        hd_res = client.post(
            f"{BASE_OFFERS}/{offer['id']}/hiring-decision",
            json={
                "signed_date": str(date.today()),
                "department_id": dept_id,
                "job_position_id": pos_id,
                "start_date": str(date.today() + timedelta(days=14)),
                "probation_salary": 8000000,
                "official_salary": 10000000,
                "probation_days": 30,
            },
            headers=h,
        )
        assert hd_res.status_code == 201, hd_res.text
        return hd_res.json(), cand

    def test_convert_creates_employee(self, client: TestClient) -> None:
        h = _admin(client)
        hd, cand = self._setup_decision(client, h)
        res = client.post(f"{BASE_HD}/{hd['id']}/convert", headers=h)
        assert res.status_code == 200, res.text
        result = res.json()
        assert "employee_id" in result
        assert "employee_code" in result
        assert result["employee_id"] > 0

    def test_convert_sets_decision_status_converted(self, client: TestClient) -> None:
        h = _admin(client)
        hd, _ = self._setup_decision(client, h)
        client.post(f"{BASE_HD}/{hd['id']}/convert", headers=h)
        res = client.get(f"{BASE_HD}/{hd['id']}", headers=h)
        assert res.status_code == 200
        assert res.json()["status"] == "converted"
        assert res.json()["employee_id"] is not None

    def test_convert_twice_returns_409(self, client: TestClient) -> None:
        h = _admin(client)
        hd, _ = self._setup_decision(client, h)
        client.post(f"{BASE_HD}/{hd['id']}/convert", headers=h)
        res = client.post(f"{BASE_HD}/{hd['id']}/convert", headers=h)
        assert res.status_code == 409

    def test_convert_missing_fields_returns_422(self, client: TestClient) -> None:
        h = _admin(client)
        suffix = uuid.uuid4().hex[:8]
        pos_id = _get_pos_id(client, h)
        dept_id = _get_dept_id(client, h)
        jr = _create_approved_jr(client, h, pos_id, dept_id)
        # Candidate thiếu date_of_birth, gender, id_number, ...
        cand = _create_candidate(client, h, suffix)
        app = _apply(client, h, cand["id"], jr["id"])
        offer = _create_offer(client, h, app["id"])
        client.post(f"{BASE_OFFERS}/{offer['id']}/send", headers=h)
        client.post(f"{BASE_OFFERS}/{offer['id']}/accept", headers=h)
        hd_res = client.post(
            f"{BASE_OFFERS}/{offer['id']}/hiring-decision",
            json={
                "signed_date": str(date.today()),
                "department_id": dept_id,
                "job_position_id": pos_id,
                "start_date": str(date.today() + timedelta(days=14)),
                "probation_salary": 8000000,
                "official_salary": 10000000,
                "probation_days": 30,
            },
            headers=h,
        )
        assert hd_res.status_code == 201
        res = client.post(f"{BASE_HD}/{hd_res.json()['id']}/convert", headers=h)
        assert res.status_code == 422
