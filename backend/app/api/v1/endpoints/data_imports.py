"""Endpoints Import dữ liệu hàng loạt (12.1)."""
import unicodedata

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.employee_import import ImportResult
from app.services import contract_import_service, leave_record_import_service, insurance_import_service

router = APIRouter()

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB


def _content_disposition(filename: str) -> str:
    encoded = unicodedata.normalize("NFC", filename)
    try:
        encoded.encode("latin-1")
        return f'attachment; filename="{encoded}"'
    except (UnicodeEncodeError, ValueError):
        from urllib.parse import quote
        return f"attachment; filename*=UTF-8''{quote(encoded)}"


def _validate_xlsx(file: UploadFile) -> None:
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Chỉ chấp nhận file .xlsx")


# ── Hợp đồng ─────────────────────────────────────────────────────────────────

@router.get(
    "/contracts/template",
    summary="Tải file mẫu import hợp đồng (.xlsx)",
)
async def download_contract_template(
    _: User = require_permission("contracts:edit"),
) -> Response:
    content = contract_import_service.generate_template()
    return Response(
        content=content,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": _content_disposition("mau_import_hop_dong.xlsx")},
    )


@router.post(
    "/contracts",
    response_model=ImportResult,
    summary="Import hợp đồng hàng loạt từ file Excel",
)
async def import_contracts(
    file: UploadFile = File(...),
    _: User = require_permission("contracts:edit"),
    session: AsyncSession = Depends(get_session),
) -> ImportResult:
    _validate_xlsx(file)
    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File quá lớn (tối đa 5MB)")
    try:
        return await contract_import_service.process_import(session, content)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Nghỉ phép ─────────────────────────────────────────────────────────────────

@router.get(
    "/leave-records/template",
    summary="Tải file mẫu import nghỉ phép (.xlsx)",
)
async def download_leave_record_template(
    _: User = require_permission("leaves:edit"),
) -> Response:
    content = leave_record_import_service.generate_template()
    return Response(
        content=content,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": _content_disposition("mau_import_nghi_phep.xlsx")},
    )


@router.post(
    "/leave-records",
    response_model=ImportResult,
    summary="Import nghỉ phép hàng loạt từ file Excel",
)
async def import_leave_records(
    file: UploadFile = File(...),
    _: User = require_permission("leaves:edit"),
    session: AsyncSession = Depends(get_session),
) -> ImportResult:
    _validate_xlsx(file)
    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File quá lớn (tối đa 5MB)")
    try:
        return await leave_record_import_service.process_import(session, content)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Bảo hiểm ─────────────────────────────────────────────────────────────────

@router.get(
    "/insurance/template",
    summary="Tải file mẫu import bảo hiểm (.xlsx)",
)
async def download_insurance_template(
    _: User = require_permission("insurance:edit"),
) -> Response:
    content = insurance_import_service.generate_template()
    return Response(
        content=content,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": _content_disposition("mau_import_bao_hiem.xlsx")},
    )


@router.post(
    "/insurance",
    response_model=ImportResult,
    summary="Import hồ sơ bảo hiểm hàng loạt từ file Excel",
)
async def import_insurance(
    file: UploadFile = File(...),
    _: User = require_permission("insurance:edit"),
    session: AsyncSession = Depends(get_session),
) -> ImportResult:
    _validate_xlsx(file)
    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File quá lớn (tối đa 5MB)")
    try:
        return await insurance_import_service.process_import(session, content)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
