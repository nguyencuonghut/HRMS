"""Endpoints Import/Export nhân viên (3.7)."""

import unicodedata
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.employee_import import ImportResult
from app.services import auth_service, employee_export_service, employee_import_service
from app.services.employee_import_service import generate_template

router = APIRouter()

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _content_disposition(filename: str) -> str:
    """RFC 5987 — hỗ trợ tên file UTF-8."""
    encoded = unicodedata.normalize("NFC", filename)
    try:
        encoded.encode("latin-1")
        return f'attachment; filename="{encoded}"'
    except (UnicodeEncodeError, ValueError):
        from urllib.parse import quote
        return f"attachment; filename*=UTF-8''{quote(encoded)}"


# ── Template ──────────────────────────────────────────────────────────────────

@router.get(
    "/import/template",
    summary="Tải file mẫu import nhân viên (.xlsx)",
)
async def download_import_template(
    _: User = require_permission("employees:edit"),
):
    content = generate_template()
    return Response(
        content=content,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": _content_disposition("mau_import_nhan_vien.xlsx")},
    )


# ── Import ────────────────────────────────────────────────────────────────────

@router.post(
    "/import",
    response_model=ImportResult,
    summary="Import nhân viên hàng loạt từ file Excel",
)
async def import_employees(
    file: UploadFile = File(...),
    current_user: User = require_permission("employees:edit"),
    session: AsyncSession = Depends(get_session),
):
    ext = (file.filename or "").lower()
    if not ext.endswith(".xlsx"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Chỉ chấp nhận file .xlsx")

    user_id = current_user.id   # cache trước khi session có thể expire
    content = await file.read()
    try:
        result = await employee_import_service.process_import(session, content)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await auth_service.log_audit(
        session, user_id, "IMPORT_EMPLOYEES",
        entity_type="employee", entity_id=None,
        new_data={"total": result.total, "success": result.success, "failed": result.failed},
    )
    await session.commit()
    return result


# ── Export list ───────────────────────────────────────────────────────────────

@router.get(
    "/export",
    summary="Export danh sách nhân viên ra Excel",
)
async def export_employees(
    keyword:   Optional[str]  = Query(None),
    status_q:  Optional[str]  = Query(None, alias="status"),
    is_active: Optional[bool] = Query(None),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    try:
        content = await employee_export_service.export_employee_list(
            session, keyword=keyword, status=status_q, is_active=is_active
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    today = date.today().strftime("%Y%m%d")
    filename = f"danh_sach_nhan_vien_{today}.xlsx"
    return Response(
        content=content,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": _content_disposition(filename)},
    )


# ── Export profile ────────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}/export",
    summary="Export hồ sơ đầy đủ một nhân viên ra Excel",
)
async def export_employee_profile(
    employee_id: int,
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    try:
        content = await employee_export_service.export_employee_profile(session, employee_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))

    filename = f"ho_so_{employee_id}.xlsx"
    return Response(
        content=content,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": _content_disposition(filename)},
    )
