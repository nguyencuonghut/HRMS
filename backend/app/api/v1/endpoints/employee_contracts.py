"""Endpoints hợp đồng lao động per-employee (4.1)."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.core.storage import delete_attachment, get_object_stream, save_contract_file
from app.models.auth import User
from app.schemas.employee_contract import (
    ALLOWED_FILE_EXTS,
    MAX_FILE_SIZE,
    ContractCreate,
    ContractRead,
    ContractUpdate,
)
from app.services import auth_service, employee_contract_service

router = APIRouter()

_TAG = "Hợp đồng nhân viên"


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
    cat = await session.get(ContractCategory, c.contract_category_id)
    from app.schemas.employee_contract import _days_until, _status_display
    from app.services.employee_contract_service import _to_read
    return _to_read(c, cat.name if cat else "")
