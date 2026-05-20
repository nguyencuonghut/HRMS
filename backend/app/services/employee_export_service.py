"""Export nhân viên ra file Excel (3.7)."""

from __future__ import annotations

from io import BytesIO
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Bank
from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department, JobTitle
from app.schemas.employee_import import EXPORT_MAX_ROWS
from app.services import (
    employee_code_service,
    employee_education_service,
    employee_insurance_service,
    employee_job_service,
    employee_relative_service,
    employee_service,
)


# ── Style helpers ─────────────────────────────────────────────────────────────

_HDR_FILL = PatternFill("solid", fgColor="1F4E79")
_HDR_FONT = Font(color="FFFFFF", bold=True)
_ALT_FILL = PatternFill("solid", fgColor="EBF3FB")


def _write_header(ws, headers: list[str], widths: list[int] | None = None) -> None:
    for col, h in enumerate(headers, start=1):
        c = ws.cell(row=1, column=col, value=h)
        c.font      = _HDR_FONT
        c.fill      = _HDR_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")
    if widths:
        for col, w in enumerate(widths, start=1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = w
    ws.row_dimensions[1].height = 22


def _fmt_date(d) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def _gender_label(g: str) -> str:
    return {"male": "Nam", "female": "Nữ", "other": "Khác"}.get(g, g)


def _status_label(s: str) -> str:
    return {
        "probation":  "Thử việc",
        "official":   "Chính thức",
        "long_leave": "Nghỉ dài hạn",
        "resigned":   "Đã nghỉ",
    }.get(s, s)


# ── Export list ───────────────────────────────────────────────────────────────

async def export_employee_list(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> bytes:
    result = await employee_service.list_employees_page(
        session,
        keyword=keyword,
        status=status,
        is_active=is_active,
        page=1,
        page_size=EXPORT_MAX_ROWS + 1,
    )
    employees: list[Employee] = result["items"]
    total: int = result["total"]

    if total > EXPORT_MAX_ROWS:
        raise ValueError(
            f"Danh sách có {total} nhân viên, vượt giới hạn {EXPORT_MAX_ROWS}. "
            "Hãy dùng bộ lọc để thu hẹp kết quả."
        )

    # Batch fetch current job (dept + job_title) để tránh N+1
    emp_ids = [e.id for e in employees]
    job_map: dict[int, EmployeeJobRecord] = {}
    dept_map: dict[int, Department] = {}
    jt_map: dict[int, JobTitle] = {}

    if emp_ids:
        rows = await session.execute(
            select(EmployeeJobRecord)
            .where(EmployeeJobRecord.employee_id.in_(emp_ids), EmployeeJobRecord.is_current.is_(True))
        )
        for rec in rows.scalars().all():
            job_map[rec.employee_id] = rec

        dept_ids = {r.department_id for r in job_map.values()}
        jt_ids   = {r.job_title_id  for r in job_map.values() if r.job_title_id}

        if dept_ids:
            drows = await session.execute(select(Department).where(Department.id.in_(dept_ids)))
            for d in drows.scalars().all():
                dept_map[d.id] = d
        if jt_ids:
            jrows = await session.execute(select(JobTitle).where(JobTitle.id.in_(jt_ids)))
            for j in jrows.scalars().all():
                jt_map[j.id] = j

    display_codes = await employee_code_service.batch_build_employee_display_codes(session, employees)

    wb = Workbook()
    ws = wb.active
    ws.title = "Danh sách nhân viên"

    headers = [
        "Mã NV", "Họ và tên", "Ngày sinh", "Giới tính",
        "Số CCCD/CMND", "Điện thoại", "Email",
        "Trạng thái", "Ngày vào làm",
        "Phòng ban", "Chức danh", "Ngày nghỉ việc",
    ]
    widths = [12, 24, 14, 10, 16, 14, 26, 14, 14, 22, 26, 14]
    _write_header(ws, headers, widths)

    for row_idx, emp in enumerate(employees, start=2):
        code     = display_codes[emp.id]
        job_rec  = job_map.get(emp.id)
        dept_name = dept_map.get(job_rec.department_id).name if job_rec and job_rec.department_id in dept_map else ""
        jt_name   = jt_map.get(job_rec.job_title_id).name  if job_rec and job_rec.job_title_id  in jt_map  else ""

        row_data = [
            code,
            emp.full_name,
            _fmt_date(emp.date_of_birth),
            _gender_label(emp.gender),
            emp.id_number,
            emp.phone_number or "",
            emp.personal_email or "",
            _status_label(emp.status),
            _fmt_date(emp.start_date),
            dept_name,
            jt_name,
            _fmt_date(emp.resigned_date),
        ]
        for col, val in enumerate(row_data, start=1):
            c = ws.cell(row=row_idx, column=col, value=val)
            if row_idx % 2 == 0:
                c.fill = _ALT_FILL

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── Export full profile ───────────────────────────────────────────────────────

async def export_employee_profile(session: AsyncSession, employee_id: int) -> bytes:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise ValueError("Không tìm thấy nhân viên")
    insurance_profile = await employee_insurance_service.get_employee_insurance_profile(session, employee_id)
    bhxh_code = (
        insurance_profile.bhxh_code
        if insurance_profile and insurance_profile.bhxh_code is not None
        else emp.bhxh_code
    )

    wb = Workbook()

    # ── Sheet 1: Thông tin cá nhân ────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Thông tin cá nhân"

    def kv(ws, key: str, val: str, row: int) -> None:
        k = ws.cell(row=row, column=1, value=key)
        k.font = Font(bold=True)
        k.fill = PatternFill("solid", fgColor="D6E4F0")
        ws.cell(row=row, column=2, value=val)

    personal_rows = [
        ("Họ và tên",       emp.full_name),
        ("Ngày sinh",       _fmt_date(emp.date_of_birth)),
        ("Giới tính",       _gender_label(emp.gender)),
        ("Số CCCD/CMND",    emp.id_number),
        ("Ngày cấp",        _fmt_date(emp.id_issued_on)),
        ("Nơi cấp",         emp.id_issued_by or ""),
        ("Hộ chiếu",        emp.passport_number or ""),
        ("Giấy phép LĐ",   emp.work_permit_number or ""),
        ("Điện thoại",      emp.phone_number or ""),
        ("Email cá nhân",   emp.personal_email or ""),
        ("Mã số thuế",      emp.personal_tax_code or ""),
        ("Số BHXH",         bhxh_code or ""),
        ("Trạng thái",      _status_label(emp.status)),
        ("Ngày vào làm",    _fmt_date(emp.start_date)),
        ("Ngày nghỉ việc",  _fmt_date(emp.resigned_date) if emp.resigned_date else ""),
    ]
    for i, (k, v) in enumerate(personal_rows, start=1):
        kv(ws1, k, v, i)
    ws1.column_dimensions["A"].width = 20
    ws1.column_dimensions["B"].width = 30

    # ── Sheet 2: Lịch sử công việc ────────────────────────────────────
    ws2 = wb.create_sheet("Công việc")
    job_headers = ["Phòng ban", "Chức danh", "Ngày hiệu lực", "Ngày kết thúc", "Thử việc từ", "Thử việc đến", "Ngày chính thức", "Hiện tại"]
    _write_header(ws2, job_headers, [22, 22, 14, 14, 14, 14, 14, 10])
    job_records = await employee_job_service.get_job_records(session, employee_id)
    for ri, rec in enumerate(job_records, start=2):
        dept = await session.get(Department, rec.department_id)
        jt   = await session.get(JobTitle, rec.job_title_id) if rec.job_title_id else None
        row  = [
            dept.name if dept else "",
            jt.name   if jt   else "",
            _fmt_date(rec.effective_from),
            _fmt_date(rec.effective_to),
            _fmt_date(rec.probation_start_date),
            _fmt_date(rec.probation_end_date),
            _fmt_date(rec.official_date),
            "✅" if rec.is_current else "",
        ]
        for ci, v in enumerate(row, start=1):
            ws2.cell(row=ri, column=ci, value=v)

    # ── Sheet 3: Học vấn ──────────────────────────────────────────────
    ws3 = wb.create_sheet("Học vấn")
    edu_headers = ["Trường", "Ngành", "Trình độ", "Năm tốt nghiệp", "Loại bằng", "Học vấn chính"]
    _write_header(ws3, edu_headers, [28, 24, 16, 18, 18, 14])
    edu_list = await employee_education_service.get_education_histories(session, employee_id)
    for ri, edu in enumerate(edu_list, start=2):
        row = [
            edu.institution_name or "",
            edu.major_name or "",
            edu.education_level_name or "",
            str(edu.graduation_year or ""),
            edu.diploma_type or "",
            "✅" if edu.is_main_education else "",
        ]
        for ci, v in enumerate(row, start=1):
            ws3.cell(row=ri, column=ci, value=v)

    # ── Sheet 4: Người thân ───────────────────────────────────────────
    ws4 = wb.create_sheet("Người thân")
    rel_headers = ["Họ tên", "Quan hệ", "Ngày sinh", "Điện thoại", "Liên hệ khẩn cấp"]
    _write_header(ws4, rel_headers, [24, 16, 14, 14, 16])
    relatives = await employee_relative_service.get_relatives(session, employee_id)
    for ri, rel in enumerate(relatives, start=2):
        row = [
            rel.full_name,
            rel.relationship_type or "",
            _fmt_date(rel.date_of_birth) if rel.date_of_birth else "",
            rel.phone_number or "",
            "✅" if rel.is_emergency_contact else "",
        ]
        for ci, v in enumerate(row, start=1):
            ws4.cell(row=ri, column=ci, value=v)

    # ── Sheet 5: Tài khoản ngân hàng ─────────────────────────────────
    ws5 = wb.create_sheet("Tài khoản ngân hàng")
    bank_headers = ["Số tài khoản", "Tên tài khoản", "Ngân hàng", "Chi nhánh", "Tài khoản chính"]
    _write_header(ws5, bank_headers, [20, 24, 24, 24, 14])
    raw_accounts = await employee_service.get_employee_bank_accounts(session, employee_id)
    bank_id_map: dict[int, Bank] = {}
    for acc in raw_accounts:
        if acc.bank_id not in bank_id_map:
            b = await session.get(Bank, acc.bank_id)
            if b:
                bank_id_map[acc.bank_id] = b
    for ri, acc in enumerate(raw_accounts, start=2):
        bank = bank_id_map.get(acc.bank_id)
        row = [
            acc.account_number,
            acc.account_name or "",
            bank.name if bank else "",
            acc.branch_name or "",
            "✅" if acc.is_primary else "",
        ]
        for ci, v in enumerate(row, start=1):
            ws5.cell(row=ri, column=ci, value=v)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
