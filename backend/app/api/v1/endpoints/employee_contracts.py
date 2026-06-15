"""Endpoints hợp đồng lao động per-employee (4.1)."""

import io
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote as _urlquote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.core.security import create_signed_token, decode_token
from app.core.storage import delete_attachment, get_object_stream, save_contract_file
from app.models.auth import User
from app.schemas.employee_contract import (
    ALLOWED_FILE_EXTS,
    MAX_FILE_SIZE,
    ContractCreate,
    ContractInsuranceSalaryPreviewInput,
    ContractInsuranceSalaryPreviewRead,
    ContractRead,
    ContractUpdate,
)
from app.services import auth_service, employee_contract_service

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class GenerateContractBody(BaseModel):
    template_id: int


class PreviewLinkRead(BaseModel):
    url: str
    expires_in_seconds: int


router = APIRouter()

_TAG = "Hợp đồng nhân viên"
_PREVIEW_TOKEN_TTL_SECONDS = 300


def _build_preview_token(*, employee_id: int, contract_id: int) -> str:
    return create_signed_token(
        "employee-contract-preview",
        token_type="preview",
        expires=timedelta(seconds=_PREVIEW_TOKEN_TTL_SECONDS),
        extra_claims={
            "scope": "employee-contract-preview",
            "employee_id": employee_id,
            "contract_id": contract_id,
        },
    )


def _validate_preview_token(token: str, *, employee_id: int, contract_id: int) -> None:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Link preview không hợp lệ hoặc đã hết hạn",
    )
    try:
        payload = decode_token(token)
    except JWTError as e:
        raise exc from e
    if payload.get("type") != "preview" or payload.get("scope") != "employee-contract-preview":
        raise exc
    if payload.get("employee_id") != employee_id:
        raise exc
    if payload.get("contract_id") != contract_id:
        raise exc


@router.get("/{employee_id}/contracts", response_model=list[ContractRead], tags=[_TAG])
async def list_contracts(
    employee_id: int,
    _: User = require_permission("contracts:view"),
    session: AsyncSession = Depends(get_session),
):
    return await employee_contract_service.get_contracts(session, employee_id)


@router.post("/{employee_id}/contracts", response_model=ContractRead, status_code=status.HTTP_201_CREATED, tags=[_TAG])
async def create_contract(
    employee_id: int,
    payload: ContractCreate,
    current_user: User = require_permission("contracts:create"),
    session: AsyncSession = Depends(get_session),
):
    result = await employee_contract_service.create_contract(session, employee_id, payload, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "CREATE_CONTRACT",
        entity_type="employee_contract", entity_id=result.id,
        new_data={"contract_number": result.contract_number, "employee_id": employee_id},
    )
    await session.commit()
    return result


@router.post(
    "/{employee_id}/contracts/preview-insurance-salary",
    response_model=ContractInsuranceSalaryPreviewRead,
    tags=[_TAG],
)
async def preview_contract_insurance_salary(
    employee_id: int,
    payload: ContractInsuranceSalaryPreviewInput,
    _: User = require_permission("contracts:view"),
    session: AsyncSession = Depends(get_session),
):
    from app.models.employee import Employee

    employee = await session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    return await employee_contract_service.preview_contract_insurance_salary(session, employee_id, payload)


@router.get("/{employee_id}/contracts/{contract_id}", response_model=ContractRead, tags=[_TAG])
async def get_contract(
    employee_id: int,
    contract_id: int,
    _: User = require_permission("contracts:view"),
    session: AsyncSession = Depends(get_session),
):
    return await employee_contract_service.get_contract_detail(session, employee_id, contract_id)


@router.put("/{employee_id}/contracts/{contract_id}", response_model=ContractRead, tags=[_TAG])
async def update_contract(
    employee_id: int,
    contract_id: int,
    payload: ContractUpdate,
    current_user: User = require_permission("contracts:edit"),
    session: AsyncSession = Depends(get_session),
):
    result = await employee_contract_service.update_contract(session, employee_id, contract_id, payload)
    import json as _json
    audit_data = _json.loads(payload.model_dump_json(exclude_none=True))
    await auth_service.log_audit(
        session, current_user.id, "UPDATE_CONTRACT",
        entity_type="employee_contract", entity_id=contract_id,
        new_data=audit_data,
    )
    await session.commit()
    return result


@router.delete("/{employee_id}/contracts/{contract_id}", response_model=ContractRead, tags=[_TAG])
async def terminate_contract(
    employee_id: int,
    contract_id: int,
    current_user: User = require_permission("contracts:edit"),
    session: AsyncSession = Depends(get_session),
):
    result = await employee_contract_service.terminate_contract(session, employee_id, contract_id)
    await auth_service.log_audit(
        session, current_user.id, "TERMINATE_CONTRACT",
        entity_type="employee_contract", entity_id=contract_id,
    )
    await session.commit()
    return result


@router.post("/{employee_id}/contracts/{contract_id}/upload", response_model=ContractRead, tags=[_TAG])
async def upload_contract_file(
    employee_id: int,
    contract_id: int,
    file: UploadFile = File(...),
    current_user: User = require_permission("contracts:edit"),
    session: AsyncSession = Depends(get_session),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_FILE_EXTS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ chấp nhận: {', '.join(sorted(ALLOWED_FILE_EXTS))}",
        )

    # Đọc trước để kiểm tra kích thước — UploadFile không có size sẵn
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File vượt quá giới hạn 20 MB")

    # Ghi lại để save_contract_file có thể đọc
    import io
    file.file = io.BytesIO(content)  # type: ignore[assignment]
    file.size = len(content)

    object_name, file_size = await save_contract_file(contract_id, file)
    result = await employee_contract_service.set_contract_file(
        session, employee_id, contract_id,
        object_name=object_name,
        file_name=file.filename or "file",
        file_size=file_size,
        mime_type=file.content_type,
    )
    await auth_service.log_audit(
        session, current_user.id, "UPLOAD_CONTRACT_FILE",
        entity_type="employee_contract", entity_id=contract_id,
        new_data={"file_name": file.filename},
    )
    await session.commit()
    return result


@router.get("/{employee_id}/contracts/{contract_id}/download", tags=[_TAG])
async def download_contract_file(
    employee_id: int,
    contract_id: int,
    _: User = require_permission("contracts:view"),
    session: AsyncSession = Depends(get_session),
):
    from app.models.employee_contract import EmployeeContract
    from app.services.employee_contract_service import _get_contract_or_404

    c = await _get_contract_or_404(session, employee_id, contract_id)
    if not c.file_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Hợp đồng chưa có file đính kèm")

    filename = c.file_name or "hop_dong.pdf"
    return StreamingResponse(
        get_object_stream(c.file_path),
        media_type=c.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{employee_id}/contracts/{contract_id}/preview-url",
    response_model=PreviewLinkRead,
    tags=[_TAG],
)
async def get_contract_preview_url(
    employee_id: int,
    contract_id: int,
    _: User = require_permission("contracts:view"),
    session: AsyncSession = Depends(get_session),
):
    from app.services.employee_contract_service import _get_contract_or_404

    c = await _get_contract_or_404(session, employee_id, contract_id)
    if not c.file_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Hợp đồng chưa có file đính kèm")

    token = _build_preview_token(employee_id=employee_id, contract_id=contract_id)
    return PreviewLinkRead(
        url=f"/api/v1/employees/{employee_id}/contracts/{contract_id}/preview?token={token}",
        expires_in_seconds=_PREVIEW_TOKEN_TTL_SECONDS,
    )


@router.get(
    "/{employee_id}/contracts/{contract_id}/preview",
    tags=[_TAG],
)
async def preview_contract_file(
    employee_id: int,
    contract_id: int,
    token: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_session),
):
    from app.services.employee_contract_service import _get_contract_or_404

    _validate_preview_token(token, employee_id=employee_id, contract_id=contract_id)
    c = await _get_contract_or_404(session, employee_id, contract_id)
    if not c.file_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Hợp đồng chưa có file đính kèm")

    filename = (c.file_name or "hop_dong.pdf").encode("utf-8").decode("latin-1", errors="replace")
    return StreamingResponse(
        get_object_stream(c.file_path),
        media_type=c.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/{employee_id}/contracts/{contract_id}/generate", tags=[_TAG])
async def generate_contract(
    employee_id: int,
    contract_id: int,
    payload: GenerateContractBody,
    current_user: User = require_permission("contracts:edit"),
    session: AsyncSession = Depends(get_session),
):
    from app.services.contract_generate_service import generate_contract_document

    docx_bytes, filename = await generate_contract_document(
        session, employee_id, contract_id, payload.template_id
    )
    await auth_service.log_audit(
        session, current_user.id, "GENERATE_CONTRACT_DOCUMENT",
        entity_type="employee_contract", entity_id=contract_id,
        new_data={"template_id": payload.template_id, "filename": filename},
    )
    await session.commit()
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type=_DOCX_MIME,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_urlquote(filename)}"},
    )


@router.delete("/{employee_id}/contracts/{contract_id}/file", response_model=ContractRead, tags=[_TAG])
async def delete_contract_file(
    employee_id: int,
    contract_id: int,
    current_user: User = require_permission("contracts:edit"),
    session: AsyncSession = Depends(get_session),
):
    c, old_path = await employee_contract_service.remove_contract_file(session, employee_id, contract_id)
    delete_attachment(old_path)
    await auth_service.log_audit(
        session, current_user.id, "DELETE_CONTRACT_FILE",
        entity_type="employee_contract", entity_id=contract_id,
    )
    await session.commit()
    from app.models.catalog import ContractCategory
    from app.models.salary import BhxhPositionGroup
    cat = await session.get(ContractCategory, c.contract_category_id)
    from app.services.employee_contract_service import _resolve_contract_read_grade_no, _to_read
    group = await session.get(BhxhPositionGroup, c.bhxh_position_group_id) if c.bhxh_position_group_id else None
    resolved_grade_no = await _resolve_contract_read_grade_no(session, c)
    return _to_read(c, cat.name if cat else "", position_group=group, resolved_grade_no=resolved_grade_no)
