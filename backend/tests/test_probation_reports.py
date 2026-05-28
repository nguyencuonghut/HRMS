"""Tests cho Plan 14.3 — Báo cáo Onboarding & Thử việc."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

BASE = "/api/v1/reports/probation"

_ADMIN_EMAIL    = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"

# Date range that captures existing seed data
_START = "2026-01-01"
_END   = "2026-12-31"


def _login(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Test 1: GET /active returns 200 and has 'items' list ──────────────────────

def test_active_returns_200_with_items(client: TestClient):
    headers = _login(client)
    r = client.get(f"{BASE}/active", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert isinstance(body["items"], list)
    assert body["total"] == len(body["items"])


# ── Test 2: GET /active with department_id filter returns subset ───────────────

def test_active_filter_by_department(client: TestClient):
    headers = _login(client)

    # Get all active
    r_all = client.get(f"{BASE}/active", headers=headers)
    assert r_all.status_code == 200, r_all.text
    all_items = r_all.json()["items"]

    if not all_items:
        pytest.skip("Không có nhân viên thử việc để test filter")

    # Use the department_id of the first employee
    dept_id = all_items[0].get("department_id")
    if dept_id is None:
        pytest.skip("Nhân viên đầu tiên không có phòng ban")

    r_filtered = client.get(f"{BASE}/active", params={"department_id": dept_id}, headers=headers)
    assert r_filtered.status_code == 200, r_filtered.text
    filtered_items = r_filtered.json()["items"]

    # All filtered items must belong to that department
    assert all(item["department_id"] == dept_id for item in filtered_items)
    # Filtered count must be <= total count
    assert len(filtered_items) <= len(all_items)


# ── Test 3: GET /checklist-completion with valid date range ────────────────────

def test_checklist_completion_structure(client: TestClient):
    headers = _login(client)
    r = client.get(
        f"{BASE}/checklist-completion",
        params={"start_date": _START, "end_date": _END},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "period_start" in body
    assert "period_end" in body
    assert "items" in body
    assert isinstance(body["items"], list)
    # Each item must have required fields
    for item in body["items"]:
        assert "department_id" in item
        assert "department_name" in item
        assert "total_checklists" in item
        assert "completed_count" in item
        assert "completion_rate" in item
        assert "avg_completion_pct" in item
        assert 0 <= item["completion_rate"] <= 100
        assert item["completed_count"] <= item["total_checklists"]


# ── Test 4: GET /pass-rate returns structure ───────────────────────────────────

def test_pass_rate_structure(client: TestClient):
    headers = _login(client)
    r = client.get(
        f"{BASE}/pass-rate",
        params={"start_date": _START, "end_date": _END},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "period_start" in body
    assert "period_end" in body
    assert "overall" in body
    assert "by_department" in body
    assert "by_position" in body
    assert "monthly_trend" in body

    overall = body["overall"]
    assert "passed" in overall
    assert "failed" in overall
    assert "extended" in overall
    assert "total_decided" in overall
    assert overall["total_decided"] == overall["passed"] + overall["failed"] + overall["extended"]

    assert isinstance(body["by_department"], list)
    assert isinstance(body["monthly_trend"], list)


# ── Test 5: GET /failure-reasons returns structure ────────────────────────────

def test_failure_reasons_structure(client: TestClient):
    headers = _login(client)
    r = client.get(
        f"{BASE}/failure-reasons",
        params={"start_date": _START, "end_date": _END},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "total_failed" in body
    assert "reasons" in body
    assert "raw_comments" in body
    assert isinstance(body["reasons"], list)
    assert isinstance(body["raw_comments"], list)
    # Each reason must have keyword, count, pct
    for reason in body["reasons"]:
        assert "keyword" in reason
        assert "count" in reason
        assert "pct" in reason


# ── Test 6: GET /export returns 200 with xlsx content-type ────────────────────

def test_export_returns_xlsx(client: TestClient):
    headers = _login(client)
    r = client.get(
        f"{BASE}/export",
        params={"start_date": _START, "end_date": _END},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert "spreadsheetml" in r.headers.get("content-type", "")
    assert len(r.content) > 0


# ── Test 7: GET /export with range > 1 year returns 400 ──────────────────────

def test_export_range_over_1_year_returns_400(client: TestClient):
    headers = _login(client)
    r = client.get(
        f"{BASE}/export",
        params={"start_date": "2024-01-01", "end_date": "2026-01-02"},
        headers=headers,
    )
    assert r.status_code == 400, r.text


# ── RBAC: unauthenticated is rejected ─────────────────────────────────────────

def test_unauthenticated_rejected(client: TestClient):
    r = client.get(f"{BASE}/active")
    assert r.status_code == 401, r.text
