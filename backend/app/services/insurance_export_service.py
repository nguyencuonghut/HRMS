from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Optional

import openpyxl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Nationality
from app.models.insurance import InsuranceChangeEvent
from app.models.salary import CompanyBhxhRegion

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "FileMau_D02_TK1_VNPT.xlsx"

_CHANGE_REASON_PA_MAP: dict[tuple[str, str], tuple[int, str, str]] = {
    ("new_hire",                 "increase"): (1, "TM", "Tăng mới"),
    ("return_from_leave",        "increase"): (1, "ON", "Đi làm lại"),
    ("transfer_in",              "increase"): (1, "TD", "Tăng do chuyển đơn vị"),
    ("contract_renewal",         "increase"): (1, "TM", "Tăng mới"),
    ("manual_correction",        "increase"): (1, "TM", "Tăng mới"),
    ("resignation",              "decrease"): (3, "GH", "Giảm hẳn"),
    ("contract_end",             "decrease"): (3, "GH", "Giảm hẳn"),
    ("dismissal",                "decrease"): (3, "GH", "Giảm hẳn"),
    ("unpaid_leave",             "decrease"): (3, "KL", "Nghỉ không lương"),
    ("maternity_no_contribution","decrease"): (3, "TS", "Thai sản"),
    ("long_term_sick",           "decrease"): (3, "OF", "Nghỉ do ốm đau"),
    ("transfer_out",             "decrease"): (3, "GD", "Giảm do chuyển đơn vị"),
    ("manual_correction",        "decrease"): (3, "GH", "Giảm hẳn"),
}


def _fmt_date(d: object) -> Optional[str]:
    if d is None:
        return None
    return d.strftime("%d/%m/%Y")  # type: ignore[attr-defined]


def _fmt_month_year(d: object) -> Optional[str]:
    if d is None:
        return None
    return d.strftime("%m/%Y")  # type: ignore[attr-defined]


def _fmt_rate(employee: Decimal, employer: Decimal) -> str:
    total = float(employee) + float(employer)
    return f"{total:g}".replace(".", ",")


async def export_d02_ts_vnpt(
    session: AsyncSession,
    period_year: int,
    period_month: int,
) -> BytesIO:
    # 1. Query events — increase first, then decrease; stable id order within each type
    events = (
        await session.execute(
            select(InsuranceChangeEvent)
            .where(
                InsuranceChangeEvent.period_year == period_year,
                InsuranceChangeEvent.period_month == period_month,
            )
            .order_by(InsuranceChangeEvent.change_type.desc(), InsuranceChangeEvent.id.asc())
        )
    ).scalars().all()

    # 2. Current company region → MavungLTT
    region_row = (
        await session.execute(
            select(CompanyBhxhRegion)
            .where(CompanyBhxhRegion.effective_to.is_(None))
            .order_by(CompanyBhxhRegion.effective_from.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    mavung_ltt = f"0{region_row.region}" if region_row else "01"

    # 3. Nationality name lookup (iso2_code → name)
    nat_codes = {e.nationality_code_snapshot for e in events if e.nationality_code_snapshot}
    nat_map: dict[str, str] = {}
    if nat_codes:
        nat_rows = (
            await session.execute(
                select(Nationality).where(Nationality.iso2_code.in_(nat_codes))
            )
        ).scalars().all()
        nat_map = {n.iso2_code: n.name for n in nat_rows if n.iso2_code}

    # 4. Load template
    wb = openpyxl.load_workbook(TEMPLATE_PATH, keep_vba=False)
    ws_data = wb["Dữ Liệu"]
    ws_bangke = wb["Bảng kê"]

    # 5. Clear existing example rows (keep header rows 1–3)
    for ws in (ws_data, ws_bangke):
        if ws.max_row >= 4:
            ws.delete_rows(4, ws.max_row - 3)

    # 6. Fill rows
    for idx, event in enumerate(events, start=1):
        row = idx + 3  # data starts at row 4

        loai, pa, ten_pa = _CHANGE_REASON_PA_MAP.get(
            (event.change_reason, event.change_type),
            (1 if event.change_type == "increase" else 3, "TM", "Tăng mới"),
        )
        ten_loai = "Tăng lao động" if event.change_type == "increase" else "Giảm lao động"

        if pa == "TM":
            contract_part = event.contract_number_snapshot or ""
            clinic_part = event.bhyt_clinic_code_snapshot or ""
            ghichu: Optional[str] = f"{contract_part} - KCB: {clinic_part}".strip(" -") or None
        else:
            ghichu = event.note or None

        den_thang: Optional[str] = (
            _fmt_month_year(event.contract_to_snapshot) if pa == "GH" else None
        )

        nat_name = nat_map.get(event.nationality_code_snapshot or "", "Việt Nam")
        gender_val = 1 if event.gender_snapshot == "male" else 0

        # Sheet "Dữ Liệu"
        ws_data.cell(row=row, column=1).value  = idx
        ws_data.cell(row=row, column=2).value  = event.employee_name_snapshot
        ws_data.cell(row=row, column=3).value  = event.bhxh_code_snapshot
        ws_data.cell(row=row, column=4).value  = ten_loai
        ws_data.cell(row=row, column=5).value  = loai
        ws_data.cell(row=row, column=6).value  = ten_pa
        ws_data.cell(row=row, column=7).value  = pa
        ws_data.cell(row=row, column=10).value = int(event.basis_amount)
        ws_data.cell(row=row, column=11).value = int(event.allowances_amount)
        ws_data.cell(row=row, column=16).value = _fmt_month_year(event.effective_date)
        ws_data.cell(row=row, column=17).value = den_thang
        ws_data.cell(row=row, column=19).value = ghichu
        ws_data.cell(row=row, column=20).value = _fmt_rate(
            event.employee_rate_total_snapshot,
            event.employer_rate_total_snapshot,
        )
        ws_data.cell(row=row, column=28).value = event.identity_number_snapshot
        ws_data.cell(row=row, column=30).value = _fmt_date(event.date_of_birth_snapshot)
        ws_data.cell(row=row, column=31).value = gender_val
        ws_data.cell(row=row, column=32).value = nat_name
        ws_data.cell(row=row, column=33).value = event.nationality_code_snapshot
        ws_data.cell(row=row, column=34).value = event.ethnicity_bhxh_code_snapshot
        ws_data.cell(row=row, column=38).value = event.bhyt_clinic_name_snapshot
        ws_data.cell(row=row, column=39).value = event.bhyt_clinic_code_snapshot
        ws_data.cell(row=row, column=50).value = mavung_ltt

        # Sheet "Bảng kê"
        ws_bangke.cell(row=row, column=1).value = idx
        ws_bangke.cell(row=row, column=2).value = event.employee_name_snapshot
        ws_bangke.cell(row=row, column=3).value = event.bhxh_code_snapshot
        ws_bangke.cell(row=row, column=4).value = "Hợp đồng lao động"
        ws_bangke.cell(row=row, column=5).value = event.contract_number_snapshot
        ws_bangke.cell(row=row, column=6).value = _fmt_date(event.contract_signed_date_snapshot)
        ws_bangke.cell(row=row, column=7).value = _fmt_date(event.contract_from_snapshot)

    # 7. Return as BytesIO
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
