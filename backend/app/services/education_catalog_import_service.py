"""Import Trường học / Chuyên ngành hàng loạt từ file Excel."""
from __future__ import annotations

from io import BytesIO
from typing import Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import EducationMajor, EducationalInstitution
from app.schemas.catalog import (
    EducationalInstitutionCreate,
    EducationalInstitutionUpdate,
    EducationMajorCreate,
    EducationMajorUpdate,
)
from app.schemas.employee_import import ImportResult, ImportRowError
from app.seeds.education_catalog import _normalize
from app.services import education_catalog_service
from app.services.import_excel_helper import extract_header_and_non_blank_rows

IMPORT_MAX_ROWS = 1000

VALID_INSTITUTION_TYPES = {"university", "college", "vocational", "high_school", "other"}


def _cell(row_vals: tuple, col_name: str, col_map: dict[str, int]) -> str:
    idx = col_map.get(col_name)
    if idx is None:
        return ""
    value = row_vals[idx] if idx < len(row_vals) else None
    return str(value).strip() if value is not None else ""


def _parse_bool(raw: str, row: int, col: str, errors: list[ImportRowError]) -> Optional[bool]:
    if not raw:
        return None
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "y", "co", "có"}:
        return True
    if value in {"0", "false", "no", "n", "khong", "không"}:
        return False
    errors.append(ImportRowError(row=row, column=col, message=f"Giá trị không hợp lệ: '{raw}'"))
    return None


def _guide_footer(guide_rows: list, max_rows: int) -> None:
    guide_rows.append([])
    guide_rows.append(["LƯU Ý", "", "Có thể import theo kiểu upsert: trùng mã (nếu có) hoặc trùng tên sẽ cập nhật record hiện có.", ""])
    guide_rows.append(["", "", f"Tối đa {max_rows} dòng mỗi lần import.", ""])


def _style_template(ws, columns: list[str], required: set[str], sample: list[str], widths: list[int]) -> None:
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(color="FFFFFF", bold=True)
    opt_fill = PatternFill("solid", fgColor="D6E4F0")
    opt_font = Font(color="1F2937", bold=True)

    for col_idx, col_name in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font if col_name in required else opt_font
        cell.fill = header_fill if col_name in required else opt_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for col_idx, val in enumerate(sample, start=1):
        ws.cell(row=2, column=col_idx, value=val)

    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width
    ws.row_dimensions[1].height = 36


def _style_guide(guide, guide_rows: list) -> None:
    for row in guide_rows:
        guide.append(row)
    guide.column_dimensions["A"].width = 20
    guide.column_dimensions["C"].width = 42
    guide.column_dimensions["D"].width = 32
    for cell in guide["1"]:
        cell.font = Font(bold=True)


# ── Trường học (EducationalInstitution) ────────────────────────────────────────

INSTITUTION_COLUMNS = [
    "Mã trường",
    "Tên trường",
    "Tên viết tắt",
    "Loại hình",
    "Mã quốc gia",
    "Mã tỉnh/thành",
    "Kích hoạt",
]
INSTITUTION_REQUIRED_COLUMNS = {"Tên trường"}


def generate_institution_template() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Trường học"
    _style_template(
        ws,
        INSTITUTION_COLUMNS,
        INSTITUTION_REQUIRED_COLUMNS,
        sample=["", "Đại học Bách khoa Hà Nội", "HUST", "university", "VN", "", "1"],
        widths=[16, 36, 16, 16, 14, 16, 12],
    )

    guide = wb.create_sheet("Hướng dẫn")
    guide_rows = [
        ["Cột", "Bắt buộc", "Mô tả", "Ví dụ"],
        ["Mã trường", "", "Mã nội bộ (để trống nếu không có, hệ thống đối chiếu theo tên)", "HUST"],
        ["Tên trường", "✅", "Tên đầy đủ, phải duy nhất trong danh mục", "Đại học Bách khoa Hà Nội"],
        ["Tên viết tắt", "", "Tên rút gọn", "HUST"],
        ["Loại hình", "", "university | college | vocational | high_school | other", "university"],
        ["Mã quốc gia", "", "Mã ISO quốc gia", "VN"],
        ["Mã tỉnh/thành", "", "Mã tỉnh/thành nếu cần", ""],
        ["Kích hoạt", "", "1/true/yes = hoạt động; 0/false/no = khóa", "1"],
    ]
    _guide_footer(guide_rows, IMPORT_MAX_ROWS)
    _style_guide(guide, guide_rows)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def _get_institution_by_code(session: AsyncSession, code: str) -> Optional[EducationalInstitution]:
    result = await session.execute(select(EducationalInstitution).where(EducationalInstitution.code == code))
    return result.scalar_one_or_none()


async def _get_institution_by_name(session: AsyncSession, name: str) -> Optional[EducationalInstitution]:
    result = await session.execute(
        select(EducationalInstitution).where(EducationalInstitution.normalized_name == _normalize(name))
    )
    return result.scalar_one_or_none()


async def process_institution_import(session: AsyncSession, file_bytes: bytes) -> ImportResult:
    try:
        wb = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError("Không đọc được file Excel. Hãy dùng file .xlsx hợp lệ.") from exc

    ws = wb.worksheets[0]
    header_row, data_rows = extract_header_and_non_blank_rows(ws)
    if not header_row:
        return ImportResult(total=0, success=0, failed=0, errors=[], created_ids=[])

    col_map = {header: idx for idx, header in enumerate(header_row)}
    if len(data_rows) > IMPORT_MAX_ROWS:
        raise ValueError(f"File có quá nhiều dòng. Tối đa {IMPORT_MAX_ROWS} dòng mỗi lần import.")

    total = 0
    failed = 0
    success = 0
    errors: list[ImportRowError] = []
    created_ids: list[int] = []

    for excel_row, row_vals in data_rows:
        total += 1
        row_errors: list[ImportRowError] = []

        code = _cell(row_vals, "Mã trường", col_map) or None
        name = _cell(row_vals, "Tên trường", col_map)
        short_name = _cell(row_vals, "Tên viết tắt", col_map) or None
        institution_type = _cell(row_vals, "Loại hình", col_map).lower() or None
        country_code = _cell(row_vals, "Mã quốc gia", col_map) or None
        province_code = _cell(row_vals, "Mã tỉnh/thành", col_map) or None
        is_active = _parse_bool(_cell(row_vals, "Kích hoạt", col_map), excel_row, "Kích hoạt", row_errors)

        if not name:
            row_errors.append(ImportRowError(row=excel_row, column="Tên trường", message="Trường bắt buộc không được để trống"))
        if institution_type and institution_type not in VALID_INSTITUTION_TYPES:
            row_errors.append(ImportRowError(
                row=excel_row,
                column="Loại hình",
                message=f"Giá trị phải là một trong: {', '.join(sorted(VALID_INSTITUTION_TYPES))}",
            ))

        if row_errors:
            errors.extend(row_errors)
            failed += 1
            continue

        existing = await _get_institution_by_code(session, code) if code else None
        if existing is None:
            existing = await _get_institution_by_name(session, name)

        try:
            if existing:
                updated = await education_catalog_service.update_institution(
                    session,
                    existing.id,
                    EducationalInstitutionUpdate(
                        name=name,
                        short_name=short_name,
                        institution_type=institution_type,
                        country_code=country_code,
                        province_code=province_code,
                        is_active=is_active if is_active is not None else existing.is_active,
                    ),
                )
                created_ids.append(updated.id)
            else:
                created = await education_catalog_service.create_institution(
                    session,
                    EducationalInstitutionCreate(
                        code=code,
                        name=name,
                        short_name=short_name,
                        institution_type=institution_type,
                        country_code=country_code,
                        province_code=province_code,
                        is_active=is_active if is_active is not None else True,
                    ),
                )
                created_ids.append(created.id)
            await session.commit()
            success += 1
        except Exception as exc:
            await session.rollback()
            detail = getattr(exc, "detail", str(exc))
            errors.append(ImportRowError(row=excel_row, column="Tên trường", message=str(detail)))
            failed += 1

    return ImportResult(total=total, success=success, failed=failed, errors=errors, created_ids=created_ids)


# ── Chuyên ngành (EducationMajor) ───────────────────────────────────────────────

MAJOR_COLUMNS = ["Mã chuyên ngành", "Tên chuyên ngành", "Nhóm ngành", "Kích hoạt"]
MAJOR_REQUIRED_COLUMNS = {"Tên chuyên ngành"}


def generate_major_template() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Chuyên ngành"
    _style_template(
        ws,
        MAJOR_COLUMNS,
        MAJOR_REQUIRED_COLUMNS,
        sample=["", "Công nghệ thông tin", "Kỹ thuật", "1"],
        widths=[18, 36, 24, 12],
    )

    guide = wb.create_sheet("Hướng dẫn")
    guide_rows = [
        ["Cột", "Bắt buộc", "Mô tả", "Ví dụ"],
        ["Mã chuyên ngành", "", "Mã nội bộ (để trống nếu không có, hệ thống đối chiếu theo tên)", "CNTT"],
        ["Tên chuyên ngành", "✅", "Tên đầy đủ, phải duy nhất trong danh mục", "Công nghệ thông tin"],
        ["Nhóm ngành", "", "Tên nhóm ngành để phân loại/lọc", "Kỹ thuật"],
        ["Kích hoạt", "", "1/true/yes = hoạt động; 0/false/no = khóa", "1"],
    ]
    _guide_footer(guide_rows, IMPORT_MAX_ROWS)
    _style_guide(guide, guide_rows)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def _get_major_by_code(session: AsyncSession, code: str) -> Optional[EducationMajor]:
    result = await session.execute(select(EducationMajor).where(EducationMajor.code == code))
    return result.scalar_one_or_none()


async def _get_major_by_name(session: AsyncSession, name: str) -> Optional[EducationMajor]:
    result = await session.execute(
        select(EducationMajor).where(EducationMajor.normalized_name == _normalize(name))
    )
    return result.scalar_one_or_none()


async def process_major_import(session: AsyncSession, file_bytes: bytes) -> ImportResult:
    try:
        wb = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError("Không đọc được file Excel. Hãy dùng file .xlsx hợp lệ.") from exc

    ws = wb.worksheets[0]
    header_row, data_rows = extract_header_and_non_blank_rows(ws)
    if not header_row:
        return ImportResult(total=0, success=0, failed=0, errors=[], created_ids=[])

    col_map = {header: idx for idx, header in enumerate(header_row)}
    if len(data_rows) > IMPORT_MAX_ROWS:
        raise ValueError(f"File có quá nhiều dòng. Tối đa {IMPORT_MAX_ROWS} dòng mỗi lần import.")

    total = 0
    failed = 0
    success = 0
    errors: list[ImportRowError] = []
    created_ids: list[int] = []

    for excel_row, row_vals in data_rows:
        total += 1
        row_errors: list[ImportRowError] = []

        code = _cell(row_vals, "Mã chuyên ngành", col_map) or None
        name = _cell(row_vals, "Tên chuyên ngành", col_map)
        major_group = _cell(row_vals, "Nhóm ngành", col_map) or None
        is_active = _parse_bool(_cell(row_vals, "Kích hoạt", col_map), excel_row, "Kích hoạt", row_errors)

        if not name:
            row_errors.append(ImportRowError(row=excel_row, column="Tên chuyên ngành", message="Trường bắt buộc không được để trống"))

        if row_errors:
            errors.extend(row_errors)
            failed += 1
            continue

        existing = await _get_major_by_code(session, code) if code else None
        if existing is None:
            existing = await _get_major_by_name(session, name)

        try:
            if existing:
                updated = await education_catalog_service.update_major(
                    session,
                    existing.id,
                    EducationMajorUpdate(
                        name=name,
                        major_group=major_group,
                        is_active=is_active if is_active is not None else existing.is_active,
                    ),
                )
                created_ids.append(updated.id)
            else:
                created = await education_catalog_service.create_major(
                    session,
                    EducationMajorCreate(
                        code=code,
                        name=name,
                        major_group=major_group,
                        is_active=is_active if is_active is not None else True,
                    ),
                )
                created_ids.append(created.id)
            await session.commit()
            success += 1
        except Exception as exc:
            await session.rollback()
            detail = getattr(exc, "detail", str(exc))
            errors.append(ImportRowError(row=excel_row, column="Tên chuyên ngành", message=str(detail)))
            failed += 1

    return ImportResult(total=total, success=success, failed=failed, errors=errors, created_ids=created_ids)
