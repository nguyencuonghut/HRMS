"""Integration tests cho Plan 6.4 — Báo cáo BHXH.

Covers:
  - TestReportCreation : tạo báo cáo + auto-populate line items
  - TestLineItemAdjustment : điều chỉnh tháng kê khai
  - TestApprovalWorkflow : submit / approve / reject + business rules
  - TestExport : export D02-TS VNPT từ báo cáo đã duyệt
"""
from __future__ import annotations

import io

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/insurance"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"

_TEST_YEAR = 2098
_TEST_MONTH = 11


# ── Session + auth ─────────────────────────────────────────────────────────────

def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _delete_reports_for_period(year: int, month: int) -> None:
    """Xóa reports (cascade → line items) cho period."""
    async with _make_session()() as s:
        await s.execute(
            text("DELETE FROM insurance_period_reports WHERE period_year=:y AND period_month=:m"),
            {"y": year, "m": month},
        )
        await s.commit()


async def _delete_events_for_period(year: int, month: int) -> None:
    """Xóa events cho period (phải gọi SAU khi reports đã xóa vì RESTRICT FK)."""
    async with _make_session()() as s:
        await s.execute(
            text("""
                DELETE FROM insurance_change_events
                WHERE suggested_declaration_year=:y AND suggested_declaration_month=:m
            """),
            {"y": year, "m": month},
        )
        await s.commit()


async def _cleanup(year: int = _TEST_YEAR, month: int = _TEST_MONTH) -> None:
    await _delete_reports_for_period(year, month)
    await _delete_events_for_period(year, month)


async def _force_approve(report_id: int) -> None:
    """Set status=approved trực tiếp trong DB (bypass self-approval check)."""
    async with _make_session()() as s:
        await s.execute(
            text("""
                UPDATE insurance_period_reports
                SET status='approved', prepared_by_id=NULL, reviewed_at=now()
                WHERE id=:id
            """),
            {"id": report_id},
        )
        await s.commit()


async def _get_employee_with_basis() -> dict:
    async with _make_session()() as s:
        r = await s.execute(text("""
            SELECT e.id, e.full_name
            FROM employees e
            JOIN employee_insurance_profiles eip ON eip.employee_id = e.id
            JOIN employee_contracts ec ON ec.employee_id = e.id AND ec.status = 'active'
            WHERE eip.participation_status = 'active'
              AND ec.insurance_salary IS NOT NULL AND ec.insurance_salary > 0
            ORDER BY e.id LIMIT 1
        """))
        row = r.fetchone()
        assert row is not None, "Không tìm thấy employee đủ điều kiện cho test"
        return {"id": row[0], "name": row[1]}


# ── API helpers ───────────────────────────────────────────────────────────────

def _create_event(client: TestClient, headers: dict, eid: int,
                  change_type: str = "increase",
                  year: int = _TEST_YEAR, month: int = _TEST_MONTH) -> dict:
    resp = client.post(f"{BASE}/change-events", headers=headers, json={
        "employee_id": eid,
        "change_type": change_type,
        "change_reason": "new_hire" if change_type == "increase" else "resignation",
        "effective_date": f"{year}-{month:02d}-01",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_report(client: TestClient, headers: dict,
                   year: int = _TEST_YEAR, month: int = _TEST_MONTH,
                   submission_type: str = "initial") -> dict:
    resp = client.post(f"{BASE}/reports", headers=headers, json={
        "period_year": year,
        "period_month": month,
        "submission_type": submission_type,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _get_report_detail(client: TestClient, headers: dict, report_id: int) -> dict:
    resp = client.get(f"{BASE}/reports/{report_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _submit(client: TestClient, headers: dict, report_id: int) -> dict:
    resp = client.post(f"{BASE}/reports/{report_id}/submit", headers=headers)
    return resp


# ══════════════════════════════════════════════════════════════════════════════
# TestReportCreation
# ══════════════════════════════════════════════════════════════════════════════

class TestReportCreation:

    @pytest.fixture(autouse=True)
    def _clean(self):
        import asyncio
        asyncio.get_event_loop().run_until_complete(_cleanup())
        yield
        asyncio.get_event_loop().run_until_complete(_cleanup())

    @pytest.mark.asyncio
    async def test_create_report_auto_populates_line_items_from_suggested_period(
        self, client: TestClient
    ):
        emp = await _get_employee_with_basis()
        headers = _admin(client)

        # Tạo event với suggested_declaration = TEST period
        event = _create_event(client, headers, emp["id"])
        assert event["suggested_declaration_year"] == _TEST_YEAR
        assert event["suggested_declaration_month"] == _TEST_MONTH

        # Tạo báo cáo cho cùng kỳ
        report = _create_report(client, headers)

        # Chi tiết báo cáo phải có line item cho event đó
        detail = _get_report_detail(client, headers, report["id"])
        event_ids = [li["event_id"] for li in detail["line_items"]]
        assert event["id"] in event_ids
        assert detail["line_item_count"] >= 1

    @pytest.mark.asyncio
    async def test_create_report_does_not_include_events_already_in_approved_report(
        self, client: TestClient
    ):
        emp = await _get_employee_with_basis()
        headers = _admin(client)

        # Tạo event và report initial, force-approve nó
        _create_event(client, headers, emp["id"])
        report1 = _create_report(client, headers, submission_type="initial")
        assert report1["line_item_count"] >= 1
        await _force_approve(report1["id"])

        # Tạo report supplement cho cùng kỳ
        report2 = _create_report(client, headers, submission_type="supplement")

        # Event đã có trong approved report → không được auto-populate vào report2
        detail2 = _get_report_detail(client, headers, report2["id"])
        assert detail2["line_item_count"] == 0

    @pytest.mark.asyncio
    async def test_create_supplement_requires_initial_to_exist(self, client: TestClient):
        # Pre-clean 2098/10 để đảm bảo không có initial nào
        await _cleanup(_TEST_YEAR, 10)

        headers = _admin(client)

        # Không có initial nào cho period 2098/10 → supplement phải 422
        resp = client.post(f"{BASE}/reports", headers=headers, json={
            "period_year": _TEST_YEAR,
            "period_month": 10,
            "submission_type": "supplement",
        })
        assert resp.status_code == 422, resp.text


# ══════════════════════════════════════════════════════════════════════════════
# TestLineItemAdjustment
# ══════════════════════════════════════════════════════════════════════════════

class TestLineItemAdjustment:

    @pytest.fixture(autouse=True)
    def _clean(self):
        import asyncio
        asyncio.get_event_loop().run_until_complete(_cleanup())
        yield
        asyncio.get_event_loop().run_until_complete(_cleanup())

    @pytest.fixture
    def _report_with_item(self, client: TestClient):
        """Trả về (headers, report_id, line_item_id)."""
        import asyncio
        emp = asyncio.get_event_loop().run_until_complete(_get_employee_with_basis())
        headers = _admin(client)
        _create_event(client, headers, emp["id"])
        report = _create_report(client, headers)
        detail = _get_report_detail(client, headers, report["id"])
        assert detail["line_items"], "Fixture cần ít nhất 1 line item"
        return headers, report["id"], detail["line_items"][0]["id"]

    def test_adjust_declared_month_sets_is_adjusted_flag(
        self, client: TestClient, _report_with_item
    ):
        headers, report_id, item_id = _report_with_item

        resp = client.patch(
            f"{BASE}/reports/{report_id}/line-items/{item_id}",
            headers=headers,
            json={
                "declared_year": _TEST_YEAR,
                "declared_month": _TEST_MONTH - 1,  # khác với suggested
                "adjustment_note": "Ghi nhận muộn",
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_adjusted"] is True
        assert resp.json()["declared_month"] == _TEST_MONTH - 1

    def test_adjust_declared_month_records_adjusted_by(
        self, client: TestClient, _report_with_item
    ):
        headers, report_id, item_id = _report_with_item

        resp = client.patch(
            f"{BASE}/reports/{report_id}/line-items/{item_id}",
            headers=headers,
            json={
                "declared_year": _TEST_YEAR,
                "declared_month": _TEST_MONTH - 1,
                "adjustment_note": "Nhập chậm",
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_adjusted"] is True

        # adjusted_by_id phải được ghi lại — verify qua DB
        import asyncio
        async def _check() -> bool:
            async with _make_session()() as s:
                r = await s.execute(
                    text("SELECT adjusted_by_id FROM insurance_report_line_items WHERE id=:id"),
                    {"id": item_id},
                )
                row = r.fetchone()
                return row is not None and row[0] is not None
        assert asyncio.get_event_loop().run_until_complete(_check()), \
            "adjusted_by_id phải được set sau khi điều chỉnh"

    def test_cannot_adjust_when_report_is_pending_review(
        self, client: TestClient, _report_with_item
    ):
        headers, report_id, item_id = _report_with_item

        # Submit → pending_review
        r = _submit(client, headers, report_id)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "pending_review"

        # Thử adjust → phải 409
        resp = client.patch(
            f"{BASE}/reports/{report_id}/line-items/{item_id}",
            headers=headers,
            json={
                "declared_year": _TEST_YEAR,
                "declared_month": _TEST_MONTH - 1,
                "adjustment_note": "Không được sửa",
            },
        )
        assert resp.status_code == 409, resp.text

    def test_declared_month_defaults_to_suggested_when_not_adjusted(
        self, client: TestClient, _report_with_item
    ):
        headers, report_id, item_id = _report_with_item

        detail = _get_report_detail(client, headers, report_id)
        item = next(li for li in detail["line_items"] if li["id"] == item_id)

        assert item["is_adjusted"] is False
        assert item["declared_year"] == item["suggested_year"]
        assert item["declared_month"] == item["suggested_month"]


# ══════════════════════════════════════════════════════════════════════════════
# TestApprovalWorkflow
# ══════════════════════════════════════════════════════════════════════════════

class TestApprovalWorkflow:

    @pytest.fixture(autouse=True)
    def _clean(self):
        import asyncio
        asyncio.get_event_loop().run_until_complete(_cleanup())
        yield
        asyncio.get_event_loop().run_until_complete(_cleanup())

    @pytest.fixture
    def _report_with_item(self, client: TestClient):
        import asyncio
        emp = asyncio.get_event_loop().run_until_complete(_get_employee_with_basis())
        headers = _admin(client)
        _create_event(client, headers, emp["id"])
        report = _create_report(client, headers)
        detail = _get_report_detail(client, headers, report["id"])
        assert detail["line_items"]
        return headers, report["id"]

    def test_submit_changes_status_to_pending_review(
        self, client: TestClient, _report_with_item
    ):
        headers, report_id = _report_with_item

        resp = _submit(client, headers, report_id)
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "pending_review"

    @pytest.mark.asyncio
    async def test_cannot_submit_empty_report(self, client: TestClient):
        headers = _admin(client)

        # Báo cáo không có event nào → line_item_count == 0
        report = _create_report(client, headers)
        assert report["line_item_count"] == 0

        resp = _submit(client, headers, report["id"])
        assert resp.status_code == 422, resp.text

    def test_approve_changes_status_to_approved(
        self, client: TestClient, _report_with_item
    ):
        import asyncio
        headers, report_id = _report_with_item

        # Submit → pending_review
        r = _submit(client, headers, report_id)
        assert r.json()["status"] == "pending_review"

        # Force clear prepared_by_id để bypass self-approval check
        async def _clear_preparer():
            async with _make_session()() as s:
                await s.execute(
                    text("UPDATE insurance_period_reports SET prepared_by_id=NULL WHERE id=:id"),
                    {"id": report_id},
                )
                await s.commit()
        asyncio.get_event_loop().run_until_complete(_clear_preparer())

        resp = client.post(f"{BASE}/reports/{report_id}/approve", headers=headers, json={})
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "approved"

    def test_reject_returns_report_to_rejected_with_note(
        self, client: TestClient, _report_with_item
    ):
        headers, report_id = _report_with_item

        _submit(client, headers, report_id)

        resp = client.post(
            f"{BASE}/reports/{report_id}/reject",
            headers=headers,
            json={"review_note": "Sai số liệu tháng 10"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["review_note"] == "Sai số liệu tháng 10"

    def test_same_user_can_approve_own_submission(
        self, client: TestClient, _report_with_item
    ):
        headers, report_id = _report_with_item

        r = _submit(client, headers, report_id)
        assert r.json()["status"] == "pending_review"

        # Cùng user vẫn được xác nhận (không còn restrict self-approval)
        resp = client.post(f"{BASE}/reports/{report_id}/approve", headers=headers, json={})
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "approved"


# ══════════════════════════════════════════════════════════════════════════════
# TestExport
# ══════════════════════════════════════════════════════════════════════════════

class TestExport:

    @pytest.fixture(autouse=True)
    def _clean(self):
        import asyncio
        asyncio.get_event_loop().run_until_complete(_cleanup())
        yield
        asyncio.get_event_loop().run_until_complete(_cleanup())

    @pytest.fixture
    def _approved_report(self, client: TestClient):
        import asyncio
        emp = asyncio.get_event_loop().run_until_complete(_get_employee_with_basis())
        headers = _admin(client)
        _create_event(client, headers, emp["id"])
        report = _create_report(client, headers)
        asyncio.get_event_loop().run_until_complete(_force_approve(report["id"]))
        return headers, report["id"]

    def _do_export(self, client: TestClient, headers: dict, report_id: int):
        return client.get(f"{BASE}/reports/{report_id}/export/d02-ts", headers=headers)

    def test_export_draft_report_returns_422(self, client: TestClient):
        headers = _admin(client)
        report = _create_report(client, headers)  # status = draft

        resp = self._do_export(client, headers, report["id"])
        assert resp.status_code == 422, resp.text

    def test_export_pending_report_returns_422(self, client: TestClient):
        import asyncio
        emp = asyncio.get_event_loop().run_until_complete(_get_employee_with_basis())
        headers = _admin(client)
        _create_event(client, headers, emp["id"])
        report = _create_report(client, headers)
        _submit(client, headers, report["id"])  # → pending_review

        resp = self._do_export(client, headers, report["id"])
        assert resp.status_code == 422, resp.text

    def test_export_returns_xlsx_content_type_for_approved_report(
        self, client: TestClient, _approved_report
    ):
        headers, report_id = _approved_report

        resp = self._do_export(client, headers, report_id)
        assert resp.status_code == 200, resp.text
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_adjusted_rows_use_declared_month_not_suggested_in_excel(
        self, client: TestClient
    ):
        """Col 16 ("Từ tháng") phải dùng declared_month, không phải suggested_month."""
        import asyncio
        emp = asyncio.get_event_loop().run_until_complete(_get_employee_with_basis())
        headers = _admin(client)

        # Tạo event có suggested = TEST_MONTH
        _create_event(client, headers, emp["id"])

        # Tạo report, lấy line item đầu tiên
        report = _create_report(client, headers)
        detail = _get_report_detail(client, headers, report["id"])
        assert detail["line_items"], "Cần có line item để test"
        item = detail["line_items"][0]

        assert item["suggested_month"] == _TEST_MONTH  # sanity check

        # Điều chỉnh declared sang tháng khác (TEST_MONTH - 1 = 10)
        declared_month = _TEST_MONTH - 1
        resp = client.patch(
            f"{BASE}/reports/{report['id']}/line-items/{item['id']}",
            headers=headers,
            json={
                "declared_year": _TEST_YEAR,
                "declared_month": declared_month,
                "adjustment_note": "Ghi nhận muộn, kê khai tháng trước",
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["declared_month"] == declared_month

        # Force approve → có thể export
        asyncio.get_event_loop().run_until_complete(_force_approve(report["id"]))

        # Export và kiểm tra col 16 của "Dữ Liệu" sheet
        resp = self._do_export(client, headers, report["id"])
        assert resp.status_code == 200, resp.text

        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        ws = wb["Dữ Liệu"]

        # Row 4 = dòng dữ liệu đầu tiên (rows 1-3 là header)
        col16_val = ws.cell(row=4, column=16).value
        expected = f"{declared_month:02d}/{_TEST_YEAR}"
        assert col16_val == expected, (
            f"Col 16 phải là '{expected}' (declared), nhận '{col16_val}'"
        )
