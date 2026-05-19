"""Import nhân viên hàng loạt từ file Excel (3.7)."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from io import BytesIO
from typing import Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_code import EmployeeCodeSequence
from app.models.org import Department, JobPosition, JobTitle
from app.schemas.employee import EmployeeCreate
from app.services import employee_service
from app.schemas.employee_import import (
    GENDER_MAP,
    IMPORT_COLUMNS,
    IMPORT_MAX_ROWS,
    REQUIRED_COLUMNS,
    STATUS_MAP,
    ImportResult,
    ImportRowError,
)


# ── Template generation ───────────────────────────────────────────────────────

def generate_template() -> bytes:
    wb = Workbook()

    # Sheet 1: Data
    ws = wb.active
    ws.title = "Nhân viên"

    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(color="FFFFFF", bold=True)
    req_fill    = PatternFill("solid", fgColor="D6E4F0")

    for col_idx, col_name in enumerate(IMPORT_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font      = header_font
        cell.fill      = header_fill if col_name in REQUIRED_COLUMNS else req_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Sample row
    sample = [
        "Nguyễn Văn A", "Nguyễn", "Văn A",
        "01/01/1990", "nam", "123456789012",
        "01/01/2020", "Cục Cảnh sát ĐKQLCƯ",
        "probation", "01/01/2026",
        "0901234567", "vana@email.com",
        "1234567890", "BHXH123456",
        "HC", "Chuyên viên nhân sự", "", "",
        "01/01/2026", "31/03/2026",
    ]
    for col_idx, val in enumerate(sample, start=1):
        ws.cell(row=2, column=col_idx, value=val)

    # Column widths
    widths = [20, 12, 12, 14, 10, 16, 14, 24, 12, 14, 14, 22, 14, 14, 14, 22, 22, 18, 20, 20]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

    ws.row_dimensions[1].height = 36

    # Sheet 2: Hướng dẫn
    guide = wb.create_sheet("Hướng dẫn")
    guide_rows = [
        ["Cột", "Bắt buộc", "Mô tả", "Giá trị hợp lệ / Ví dụ"],
        ["Họ và tên", "✅", "Họ tên đầy đủ", "Nguyễn Văn A"],
        ["Họ", "✅", "Họ (last name)", "Nguyễn"],
        ["Tên", "✅", "Tên đệm + tên (first name)", "Văn A"],
        ["Ngày sinh", "✅", "Định dạng dd/mm/yyyy", "01/01/1990"],
        ["Giới tính", "✅", "Chữ thường", "nam / nữ / khác"],
        ["Số CCCD/CMND", "✅", "Số giấy tờ tùy thân", "123456789012"],
        ["Ngày cấp CCCD", "✅", "Định dạng dd/mm/yyyy", "01/01/2020"],
        ["Nơi cấp CCCD", "✅", "Cơ quan cấp", "Cục Cảnh sát ĐKQLCƯ"],
        ["Trạng thái", "✅", "Trạng thái nhân viên", "probation / official / long_leave"],
        ["Ngày vào làm", "✅", "Định dạng dd/mm/yyyy", "01/01/2026"],
        ["Số điện thoại", "", "Tùy chọn", "0901234567"],
        ["Email cá nhân", "", "Tùy chọn", "email@example.com"],
        ["Mã số thuế", "", "Mã số thuế thu nhập cá nhân", "1234567890"],
        ["Số BHXH", "", "Mã BHXH", "BHXH123456"],
        ["Phòng ban", "", "Mã hoặc tên phòng ban (tìm kiếm tương đối)", "HC"],
        ["Chức danh", "", "Tên chức danh (tìm kiếm tương đối)", "Chuyên viên nhân sự"],
        ["Vị trí công việc", "", "Tên vị trí công việc, nên đi cùng phòng ban", "Nhân viên nhân sự tổng hợp"],
        ["Hệ mã nhân viên", "", "Override hệ mã trong case ngoại lệ", "SYS2 / SYS3"],
        ["Ngày bắt đầu thử việc", "", "Định dạng dd/mm/yyyy", "01/01/2026"],
        ["Ngày kết thúc thử việc", "", "Định dạng dd/mm/yyyy", "31/03/2026"],
        [],
        ["LƯU Ý:", "", "Cột header màu xanh đậm = bắt buộc. Dòng trống sẽ bị bỏ qua.", ""],
        ["", "", f"Tối đa {IMPORT_MAX_ROWS} dòng dữ liệu mỗi lần import.", ""],
    ]
    for row in guide_rows:
        guide.append(row)

    guide.column_dimensions["A"].width = 24
    guide.column_dimensions["C"].width = 40
    guide.column_dimensions["D"].width = 30
    for cell in guide["1"]:
        cell.font = Font(bold=True)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── Parse helpers ─────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    """Chuẩn hoá Unicode NFC, bỏ dấu, lowercase — dùng để tra cứu fuzzy."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _parse_date(val: str, col: str, row: int, errors: list[ImportRowError]) -> Optional[date]:
    val = (val or "").strip()
    if not val:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return date.fromisoformat(val) if fmt == "%Y-%m-%d" else date(
                *[int(x) for x in re.split(r"[/\-]", val)][::-1]
                if fmt == "%d/%m/%Y" else [int(x) for x in re.split(r"[/\-]", val)]
            )
        except (ValueError, TypeError):
            pass
    # Try strptime fallback
    from datetime import datetime
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            pass
    errors.append(ImportRowError(row=row, column=col, message=f"Định dạng ngày không hợp lệ: '{val}' (cần dd/mm/yyyy)"))
    return None


def _cell_str(ws, row: int, col: int) -> str:
    v = ws.cell(row=row, column=col).value
    return str(v).strip() if v is not None else ""


# ── Department/JobTitle lookup ────────────────────────────────────────────────

async def _find_department(session: AsyncSession, name_or_code: str) -> Optional[int]:
    """Tra cứu department theo code (exact) rồi theo name (normalized)."""
    if not name_or_code:
        return None
    val = name_or_code.strip()
    # exact code
    row = await session.execute(select(Department).where(Department.code == val))
    dept = row.scalar_one_or_none()
    if dept:
        return dept.id
    # normalized name
    norm_val = _norm(val)
    rows = await session.execute(select(Department))
    for d in rows.scalars().all():
        if _norm(d.name) == norm_val or _norm(d.short_name or "") == norm_val:
            return d.id
    return None


async def _find_job_title(session: AsyncSession, name: str) -> Optional[int]:
    if not name:
        return None
    norm_val = _norm(name.strip())
    rows = await session.execute(select(JobTitle))
    for jt in rows.scalars().all():
        if _norm(jt.name) == norm_val:
            return jt.id
    return None


async def _find_job_position(
    session: AsyncSession,
    name_or_code: str,
    *,
    department_id: int | None = None,
) -> Optional[JobPosition]:
    if not name_or_code:
        return None

    raw = name_or_code.strip()
    query = select(JobPosition)
    if department_id is not None:
        query = query.where(JobPosition.department_id == department_id)

    exact = (await session.execute(query.where(JobPosition.code == raw))).scalar_one_or_none()
    if exact:
        return exact

    norm_val = _norm(raw)
    rows = await session.execute(query)
    for position in rows.scalars().all():
        if _norm(position.name) == norm_val:
            return position
    return None


async def _find_employee_code_sequence(
    session: AsyncSession,
    code_or_name: str,
) -> Optional[int]:
    if not code_or_name:
        return None
    raw = code_or_name.strip()
    row = (
        await session.execute(
            select(EmployeeCodeSequence).where(
                EmployeeCodeSequence.is_active.is_(True),
                EmployeeCodeSequence.code == raw,
            )
        )
    ).scalar_one_or_none()
    if row:
        return row.id

    norm_val = _norm(raw)
    rows = await session.execute(
        select(EmployeeCodeSequence).where(EmployeeCodeSequence.is_active.is_(True))
    )
    for sequence in rows.scalars().all():
        if _norm(sequence.name) == norm_val:
            return sequence.id
    return None


# ── Main import ───────────────────────────────────────────────────────────────

async def process_import(session: AsyncSession, file_bytes: bytes) -> ImportResult:
    try:
        wb = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception:
        raise ValueError("Không đọc được file Excel. Hãy dùng file .xlsx hợp lệ.")

    ws = wb.worksheets[0]
    rows_iter = list(ws.iter_rows(values_only=True))
    if not rows_iter:
        return ImportResult(total=0, success=0, failed=0, errors=[], created_ids=[])

    # Map header → col index (0-based)
    header_row = [str(c).strip() if c else "" for c in rows_iter[0]]
    col_idx: dict[str, int] = {h: i for i, h in enumerate(header_row)}

    def get(row_vals: tuple, col_name: str) -> str:
        idx = col_idx.get(col_name)
        if idx is None:
            return ""
        v = row_vals[idx] if idx < len(row_vals) else None
        return str(v).strip() if v is not None else ""

    data_rows = rows_iter[1:]
    if len(data_rows) > IMPORT_MAX_ROWS:
        raise ValueError(f"File có quá nhiều dòng. Tối đa {IMPORT_MAX_ROWS} dòng mỗi lần import.")

    total = 0
    success = 0
    failed = 0
    errors: list[ImportRowError] = []
    created_ids: list[int] = []

    for rel_idx, row_vals in enumerate(data_rows):
        excel_row = rel_idx + 2  # row 1 = header
        # Skip blank rows
        if all((v is None or str(v).strip() == "") for v in row_vals):
            continue
        total += 1
        row_errors: list[ImportRowError] = []

        # ── Required fields ───────────────────────────────────────────
        full_name  = get(row_vals, "Họ và tên")
        last_name  = get(row_vals, "Họ")
        first_name = get(row_vals, "Tên")
        id_number  = get(row_vals, "Số CCCD/CMND")
        id_issued_by = get(row_vals, "Nơi cấp CCCD")

        for field, val in [
            ("Họ và tên", full_name), ("Họ", last_name), ("Tên", first_name),
            ("Số CCCD/CMND", id_number), ("Nơi cấp CCCD", id_issued_by),
        ]:
            if not val:
                row_errors.append(ImportRowError(row=excel_row, column=field, message="Trường bắt buộc không được để trống"))

        gender_raw = get(row_vals, "Giới tính").lower()
        gender = GENDER_MAP.get(gender_raw)
        if not gender:
            row_errors.append(ImportRowError(row=excel_row, column="Giới tính", message=f"Giá trị phải là nam/nữ/khác, nhận được: '{gender_raw}'"))

        status_raw = get(row_vals, "Trạng thái").lower()
        status = STATUS_MAP.get(status_raw)
        if not status:
            row_errors.append(ImportRowError(row=excel_row, column="Trạng thái", message=f"Giá trị phải là probation/official/long_leave, nhận được: '{status_raw}'"))

        date_of_birth  = _parse_date(get(row_vals, "Ngày sinh"),       "Ngày sinh",       excel_row, row_errors)
        id_issued_on   = _parse_date(get(row_vals, "Ngày cấp CCCD"),   "Ngày cấp CCCD",   excel_row, row_errors)
        start_date     = _parse_date(get(row_vals, "Ngày vào làm"),    "Ngày vào làm",    excel_row, row_errors)
        prob_start     = _parse_date(get(row_vals, "Ngày bắt đầu thử việc"), "Ngày bắt đầu thử việc", excel_row, row_errors)
        prob_end       = _parse_date(get(row_vals, "Ngày kết thúc thử việc"), "Ngày kết thúc thử việc", excel_row, row_errors)

        if not date_of_birth and "Ngày sinh" not in {e.column for e in row_errors}:
            row_errors.append(ImportRowError(row=excel_row, column="Ngày sinh", message="Trường bắt buộc không được để trống"))
        if not id_issued_on and "Ngày cấp CCCD" not in {e.column for e in row_errors}:
            row_errors.append(ImportRowError(row=excel_row, column="Ngày cấp CCCD", message="Trường bắt buộc không được để trống"))
        if not start_date and "Ngày vào làm" not in {e.column for e in row_errors}:
            row_errors.append(ImportRowError(row=excel_row, column="Ngày vào làm", message="Trường bắt buộc không được để trống"))

        # Optional fields
        phone        = get(row_vals, "Số điện thoại") or None
        email        = get(row_vals, "Email cá nhân") or None
        tax_code     = get(row_vals, "Mã số thuế") or None
        bhxh_code    = get(row_vals, "Số BHXH") or None
        dept_raw     = get(row_vals, "Phòng ban")
        jt_raw       = get(row_vals, "Chức danh")
        position_raw = get(row_vals, "Vị trí công việc")
        sequence_raw = get(row_vals, "Hệ mã nhân viên")

        if row_errors:
            errors.extend(row_errors)
            failed += 1
            continue

        # ── DB checks ─────────────────────────────────────────────────
        existing = await session.execute(select(Employee).where(Employee.id_number == id_number))
        if existing.scalar_one_or_none():
            errors.append(ImportRowError(row=excel_row, column="Số CCCD/CMND", message=f"Số CCCD/CMND '{id_number}' đã tồn tại trong hệ thống"))
            failed += 1
            continue

        dept_id      = await _find_department(session, dept_raw)
        job_title_id = await _find_job_title(session, jt_raw)
        job_position = await _find_job_position(session, position_raw, department_id=dept_id) if position_raw else None
        sequence_id  = await _find_employee_code_sequence(session, sequence_raw) if sequence_raw else None

        if dept_raw and not dept_id:
            errors.append(ImportRowError(row=excel_row, column="Phòng ban", message=f"Không tìm thấy phòng ban '{dept_raw}' — nhân viên được tạo nhưng chưa gán phòng ban"))
        if position_raw and not dept_id:
            errors.append(ImportRowError(row=excel_row, column="Vị trí công việc", message="Muốn gán vị trí công việc thì phải xác định được phòng ban"))
            failed += 1
            continue
        if position_raw and not job_position:
            errors.append(ImportRowError(row=excel_row, column="Vị trí công việc", message=f"Không tìm thấy vị trí công việc '{position_raw}' trong phòng ban đã chọn"))
            failed += 1
            continue
        if sequence_raw and not sequence_id:
            errors.append(ImportRowError(row=excel_row, column="Hệ mã nhân viên", message=f"Không tìm thấy hệ mã nhân viên '{sequence_raw}'"))
            failed += 1
            continue

        # ── Create employee ───────────────────────────────────────────
        try:
            payload = EmployeeCreate(
                full_name=full_name,
                last_name=last_name,
                first_name=first_name,
                date_of_birth=date_of_birth,
                gender=gender,
                nationality_id=1,  # mặc định Việt Nam
                id_number=id_number,
                id_issued_on=id_issued_on,
                id_issued_by=id_issued_by,
                phone_number=phone,
                personal_email=email,
                personal_tax_code=tax_code,
                bhxh_code=bhxh_code,
                status=status,
                start_date=start_date,
                employee_code_sequence_id=sequence_id,
                initial_department_id=dept_id,
                initial_job_title_id=job_title_id,
                initial_job_position_id=job_position.id if job_position else None,
                initial_job_effective_from=start_date if dept_id else None,
                initial_probation_start_date=prob_start,
                initial_probation_end_date=prob_end,
            )
            emp = await employee_service.create_employee(session, payload)

            await session.commit()
            created_ids.append(emp.id)
            success += 1

        except IntegrityError:
            await session.rollback()
            errors.append(ImportRowError(row=excel_row, column="Số CCCD/CMND", message=f"Số CCCD/CMND '{id_number}' bị trùng (race condition)"))
            failed += 1
        except Exception as exc:
            await session.rollback()
            errors.append(ImportRowError(row=excel_row, column="—", message=f"Lỗi hệ thống: {exc}"))
            failed += 1

    return ImportResult(total=total, success=success, failed=failed, errors=errors, created_ids=created_ids)
