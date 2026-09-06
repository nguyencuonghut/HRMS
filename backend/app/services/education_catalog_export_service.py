"""Export Trường học / Chuyên ngành ra file Excel."""
from __future__ import annotations

from io import BytesIO
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.employee_import import EXPORT_MAX_ROWS
from app.services import education_catalog_service

_HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
_HEADER_FONT = Font(color="FFFFFF", bold=True)

INSTITUTION_TYPE_LABELS = {
    "university": "Đại học",
    "college": "Cao đẳng",
    "vocational": "Nghề / trung cấp",
    "high_school": "THPT",
    "other": "Khác",
}


def _style_header(ws, headers: list[str]) -> None:
    for col_idx, name in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=name)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 30


async def export_institutions(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    institution_type: Optional[str] = None,
    country_code: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> bytes:
    result = await education_catalog_service.list_institutions_page(
        session,
        keyword=keyword,
        institution_type=institution_type,
        country_code=country_code,
        is_active=is_active,
        page=1,
        page_size=EXPORT_MAX_ROWS + 1,
    )
    items = result["items"]
    if result["total"] > EXPORT_MAX_ROWS:
        raise ValueError(
            f"Danh sách có {result['total']} trường học, vượt giới hạn {EXPORT_MAX_ROWS}. "
            "Hãy dùng bộ lọc để thu hẹp kết quả."
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Trường học"

    headers = ["Mã trường", "Tên trường", "Tên viết tắt", "Loại hình", "Mã quốc gia", "Mã tỉnh/thành", "Trạng thái"]
    _style_header(ws, headers)

    for row_idx, inst in enumerate(items, start=2):
        ws.cell(row=row_idx, column=1, value=inst.code or "")
        ws.cell(row=row_idx, column=2, value=inst.name)
        ws.cell(row=row_idx, column=3, value=inst.short_name or "")
        ws.cell(row=row_idx, column=4, value=INSTITUTION_TYPE_LABELS.get(inst.institution_type or "", inst.institution_type or ""))
        ws.cell(row=row_idx, column=5, value=inst.country_code or "")
        ws.cell(row=row_idx, column=6, value=inst.province_code or "")
        ws.cell(row=row_idx, column=7, value="Hoạt động" if inst.is_active else "Đã khóa")

    widths = [14, 40, 16, 18, 12, 14, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def export_majors(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    major_group: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> bytes:
    result = await education_catalog_service.list_majors_page(
        session,
        keyword=keyword,
        major_group=major_group,
        is_active=is_active,
        page=1,
        page_size=EXPORT_MAX_ROWS + 1,
    )
    items = result["items"]
    if result["total"] > EXPORT_MAX_ROWS:
        raise ValueError(
            f"Danh sách có {result['total']} chuyên ngành, vượt giới hạn {EXPORT_MAX_ROWS}. "
            "Hãy dùng bộ lọc để thu hẹp kết quả."
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Chuyên ngành"

    headers = ["Mã chuyên ngành", "Tên chuyên ngành", "Nhóm ngành", "Trạng thái"]
    _style_header(ws, headers)

    for row_idx, major in enumerate(items, start=2):
        ws.cell(row=row_idx, column=1, value=major.code or "")
        ws.cell(row=row_idx, column=2, value=major.name)
        ws.cell(row=row_idx, column=3, value=major.major_group or "")
        ws.cell(row=row_idx, column=4, value="Hoạt động" if major.is_active else "Đã khóa")

    widths = [18, 40, 24, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
