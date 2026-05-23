"""Integration tests cho Plan 8.2 — Kỷ luật nhân viên.

Covers:
  - TestCreateDiscipline: tạo kỷ luật, validate hình thức, ngày, file
  - TestListDisciplines: list + filter + search
  - TestUpdateDeleteDiscipline: sửa + xoá, recalc end_date
  - TestEmployeeHistory: lịch sử kỷ luật của nhân viên
"""
from __future__ import annotations

import io
import json
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

BASE = "/api/v1/disciplines"
_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_RUN_ID = uuid.uuid4().hex[:8]

# Ngày test — tương lai xa để tránh collision
_VIOLATION_DATE = "2098-05-01"
_EFFECTIVE_DATE = "2098-05-10"


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _get_active_employee() -> dict:
    async with _make_session()() as s:
        r = await s.execute(text(
            "SELECT id, full_name FROM employees WHERE status != 'resigned' ORDER BY id LIMIT 1"
        ))
        row = r.fetchone()
        assert row is not None, "Không tìm thấy nhân viên active"
        return {"id": row[0], "name": row[1]}


async def _get_resigned_employee() -> dict | None:
    async with _make_session()() as s:
        r = await s.execute(text(
            "SELECT id, full_name FROM employees WHERE status = 'resigned' LIMIT 1"
        ))
        row = r.fetchone()
        return {"id": row[0], "name": row[1]} if row else None


def _create_discipline(client, h, emp_id, form="khien_trach", title="Test kỷ luật",
                       extended_months=None):
    payload = json.dumps({
        "employee_id": emp_id,
        "discipline_form": form,
        "violation_date": _VIOLATION_DATE,
        "effective_date": _EFFECTIVE_DATE,
        **({"extended_months": extended_months} if extended_months else {}),
        "title": title,
    })
    return client.post(BASE, data={"body": payload}, headers=h)


# ── TestCreateDiscipline ───────────────────────────────────────────────────────

class TestCreateDiscipline:
    @pytest.mark.asyncio
    async def test_create_khien_trach_without_file(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        r = _create_discipline(client, h, emp["id"], "khien_trach", f"KT {_RUN_ID}")
        assert r.status_code == 201
        data = r.json()
        assert data["discipline_form"] == "khien_trach"
        assert data["discipline_form_label"] == "Khiển trách"
        assert data["has_file"] is False
        assert data["end_date"] is None
        assert data["extended_months"] is None

    @pytest.mark.asyncio
    async def test_create_keo_dai_requires_extended_months(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        r = _create_discipline(client, h, emp["id"], "keo_dai_nang_luong",
                               f"KD thiếu months {_RUN_ID}")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_create_keo_dai_auto_calculates_end_date(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        r = _create_discipline(client, h, emp["id"], "keo_dai_nang_luong",
                               f"KD có months {_RUN_ID}", extended_months=3)
        assert r.status_code == 201
        data = r.json()
        assert data["extended_months"] == 3
        # end_date = effective_date + 3 months = 2098-08-10
        assert data["end_date"] == "2098-08-10"

    @pytest.mark.asyncio
    async def test_create_sa_thai_with_file(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        payload = json.dumps({
            "employee_id": emp["id"],
            "discipline_form": "sa_thai",
            "violation_date": _VIOLATION_DATE,
            "effective_date": _EFFECTIVE_DATE,
            "title": f"Sa thải có file {_RUN_ID}",
        })
        fake_pdf = io.BytesIO(b"%PDF-1.4 sa thai test")
        r = client.post(
            BASE,
            data={"body": payload},
            files={"file": ("quyet_dinh_sa_thai.pdf", fake_pdf, "application/pdf")},
            headers=h,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["has_file"] is True
        assert data["file_name"] == "quyet_dinh_sa_thai.pdf"

    @pytest.mark.asyncio
    async def test_invalid_discipline_form_rejected(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        payload = json.dumps({
            "employee_id": emp["id"],
            "discipline_form": "khong_hop_le",
            "violation_date": _VIOLATION_DATE,
            "effective_date": _EFFECTIVE_DATE,
            "title": "Form không hợp lệ",
        })
        r = client.post(BASE, data={"body": payload}, headers=h)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_violation_date_after_effective_date_rejected(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        payload = json.dumps({
            "employee_id": emp["id"],
            "discipline_form": "khien_trach",
            "violation_date": "2098-06-01",   # sau effective_date
            "effective_date": "2098-05-01",
            "title": "Ngày vi phạm sau ngày hiệu lực",
        })
        r = client.post(BASE, data={"body": payload}, headers=h)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_resigned_employee_rejected(self, client: TestClient):
        emp = await _get_resigned_employee()
        if emp is None:
            pytest.skip("Không có nhân viên resigned trong DB test")
        h = _admin(client)
        r = _create_discipline(client, h, emp["id"], "khien_trach", f"NV đã nghỉ {_RUN_ID}")
        assert r.status_code == 422


# ── TestListDisciplines ────────────────────────────────────────────────────────

class TestListDisciplines:
    @pytest.mark.asyncio
    async def test_filter_by_employee_id(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        _create_discipline(client, h, emp["id"], title=f"Filter emp {_RUN_ID}")
        r = client.get(BASE, params={"employee_id": emp["id"], "page_size": 100}, headers=h)
        assert r.status_code == 200
        assert all(item["employee_id"] == emp["id"] for item in r.json()["items"])

    @pytest.mark.asyncio
    async def test_filter_by_discipline_form(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        _create_discipline(client, h, emp["id"], form="cach_chuc", title=f"Filter form {_RUN_ID}")
        r = client.get(BASE, params={"discipline_form": "cach_chuc", "page_size": 100}, headers=h)
        assert r.status_code == 200
        assert all(item["discipline_form"] == "cach_chuc" for item in r.json()["items"])

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        _create_discipline(client, h, emp["id"], title=f"Filter date {_RUN_ID}")
        r = client.get(BASE, params={"from_date": "2098-01-01", "to_date": "2098-12-31", "page_size": 100}, headers=h)
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(item["effective_date"].startswith("2098") for item in items)

    @pytest.mark.asyncio
    async def test_search_by_employee_name(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        _create_discipline(client, h, emp["id"], title=f"Search name {_RUN_ID}")
        r = client.get(BASE, params={"search": emp["name"][:4], "page_size": 50}, headers=h)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_search_by_employee_code(self, client: TestClient):
        """Search theo mã nhân viên — trả về 200 và có kết quả."""
        emp = await _get_active_employee()
        h = _admin(client)
        _create_discipline(client, h, emp["id"], title=f"Search code {_RUN_ID}")
        # Lấy mã NV từ API
        detail_r = client.get(BASE, params={"employee_id": emp["id"], "page_size": 1}, headers=h)
        assert detail_r.status_code == 200
        items = detail_r.json()["items"]
        if not items or not items[0]["employee_code"]:
            pytest.skip("Không tìm thấy mã NV để kiểm tra search")
        emp_code = items[0]["employee_code"]
        r = client.get(BASE, params={"search": emp_code, "page_size": 50}, headers=h)
        assert r.status_code == 200
        # Phải tìm thấy ít nhất 1 record khớp mã nhân viên
        assert r.json()["total"] >= 1
        assert all(item["employee_code"] == emp_code for item in r.json()["items"])

    @pytest.mark.asyncio
    async def test_search_by_decision_number(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        qd = f"QD-{_RUN_ID}"
        payload = json.dumps({
            "employee_id": emp["id"],
            "discipline_form": "khien_trach",
            "violation_date": _VIOLATION_DATE,
            "effective_date": _EFFECTIVE_DATE,
            "title": f"Có số QĐ {_RUN_ID}",
            "decision_number": qd,
        })
        client.post(BASE, data={"body": payload}, headers=h)
        r = client.get(BASE, params={"search": qd, "page_size": 50}, headers=h)
        assert r.status_code == 200
        assert any(item["decision_number"] == qd for item in r.json()["items"])


# ── TestUpdateDeleteDiscipline ─────────────────────────────────────────────────

class TestUpdateDeleteDiscipline:
    @pytest.mark.asyncio
    async def test_update_changes_title_and_form(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        created = _create_discipline(client, h, emp["id"], title=f"Trước khi sửa {_RUN_ID}").json()
        rid = created["id"]
        payload = json.dumps({"title": "Sau khi sửa", "discipline_form": "cach_chuc"})
        r = client.put(f"{BASE}/{rid}", data={"body": payload}, headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "Sau khi sửa"
        assert data["discipline_form"] == "cach_chuc"

    @pytest.mark.asyncio
    async def test_update_keo_dai_recalculates_end_date(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        # Tạo với keo_dai_nang_luong 3 tháng
        created = _create_discipline(client, h, emp["id"], "keo_dai_nang_luong",
                                     f"Recalc {_RUN_ID}", extended_months=3).json()
        rid = created["id"]
        assert created["end_date"] == "2098-08-10"

        # Đổi sang 6 tháng → end_date phải tự tính lại
        payload = json.dumps({"extended_months": 6})
        r = client.put(f"{BASE}/{rid}", data={"body": payload}, headers=h)
        assert r.status_code == 200
        assert r.json()["end_date"] == "2098-11-10"

    @pytest.mark.asyncio
    async def test_delete_removes_record(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        created = _create_discipline(client, h, emp["id"], title=f"Sẽ xoá {_RUN_ID}").json()
        rid = created["id"]
        r = client.delete(f"{BASE}/{rid}", headers=h)
        assert r.status_code == 204
        r2 = client.get(f"{BASE}/{rid}", headers=h)
        assert r2.status_code == 404


# ── TestEmployeeHistory ────────────────────────────────────────────────────────

class TestEmployeeHistory:
    @pytest.mark.asyncio
    async def test_employee_discipline_history_returns_correct_records(self, client: TestClient):
        emp = await _get_active_employee()
        h = _admin(client)
        _create_discipline(client, h, emp["id"], title=f"Lịch sử {_RUN_ID}")

        r = client.get(f"/api/v1/employees/{emp['id']}/disciplines", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(item["employee_id"] == emp["id"] for item in data)

    def test_unauthenticated_returns_401(self, client: TestClient):
        r = client.get(f"{BASE}")
        assert r.status_code == 401
