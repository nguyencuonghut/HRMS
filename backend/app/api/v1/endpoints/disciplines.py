"""Endpoints kỷ luật nhân viên (8.2)."""
from __future__ import annotations

import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.core.storage import get_object_stream
from app.models.auth import User
from app.schemas.discipline import (
    DisciplineCreate,
    DisciplineListPage,
    DisciplineRead,
    DisciplineUpdate,
)
from app.services import auth_service, discipline_service

router = APIRouter()
employee_history_router = APIRouter()

_TAG = "Kỷ luật"


# ── List / Get ────────────────────────────────────────────────────────────────


@router.get("", response_model=DisciplineListPage, tags=[_TAG],
            summary="Danh sách kỷ luật (phân trang + filter)")
async def list_disciplines(
    employee_id:      Optional[int]  = Query(None),
    discipline_form:  Optional[str]  = Query(None),
    department_id:    Optional[int]  = Query(None),
    from_date:        Optional[date] = Query(None),
    to_date:          Optional[date] = Query(None),
    search:           Optional[str]  = Query(None),
    page:             int            = Query(1, ge=1),
    page_size:        int            = Query(20, ge=1, le=200),
    _: User = require_permission("disciplines:view"),
    session: AsyncSession = Depends(get_session),
):
    return await discipline_service.list_disciplines(
        session,
        employee_id=employee_id,
        discipline_form=discipline_form,
        department_id=department_id,
        from_date=from_date,
        to_date=to_date,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{discipline_id}", response_model=DisciplineRead, tags=[_TAG],
            summary="Chi tiết quyết định kỷ luật")
async def get_discipline(
    discipline_id: int,
    _: User = require_permission("disciplines:view"),
    session: AsyncSession = Depends(get_session),
):
    return await discipline_service.get_discipline(session, discipline_id)


# ── Create ────────────────────────────────────────────────────────────────────


@router.post("", response_model=DisciplineRead, status_code=status.HTTP_201_CREATED,
             tags=[_TAG], summary="Tạo quyết định kỷ luật")
async def create_discipline(
    request: Request,
    body: str = Form(...),
    file: Optional[UploadFile] = File(None),
    current_user: User = require_permission("disciplines:create"),
    session: AsyncSession = Depends(get_session),
):
    try:
        data = DisciplineCreate.model_validate(json.loads(body))
    except Exception as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))

    result = await discipline_service.create_discipline(session, data, file or None, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="employee_discipline", entity_id=result.id,
        entity_name=f"{result.employee_name} {result.effective_date}",
    )
    await session.commit()
    return result


# ── Update ────────────────────────────────────────────────────────────────────


@router.put("/{discipline_id}", response_model=DisciplineRead, tags=[_TAG],
            summary="Sửa quyết định kỷ luật")
async def update_discipline(
    discipline_id: int,
    request: Request,
    body: str = Form(...),
    file: Optional[UploadFile] = File(None),
    current_user: User = require_permission("disciplines:create"),
    session: AsyncSession = Depends(get_session),
):
    try:
        data = DisciplineUpdate.model_validate(json.loads(body))
    except Exception as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))

    result = await discipline_service.update_discipline(session, discipline_id, data, file or None)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="employee_discipline", entity_id=result.id,
        entity_name=f"{result.employee_name} {result.effective_date}",
    )
    await session.commit()
    return result


# ── Delete ────────────────────────────────────────────────────────────────────


@router.delete("/{discipline_id}", status_code=status.HTTP_204_NO_CONTENT, tags=[_TAG],
               summary="Xóa quyết định kỷ luật")
async def delete_discipline(
    discipline_id: int,
    current_user: User = require_permission("disciplines:delete"),
    session: AsyncSession = Depends(get_session),
):
    await discipline_service.delete_discipline(session, discipline_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="employee_discipline", entity_id=discipline_id,
        entity_name=str(discipline_id),
    )
    await session.commit()


# ── Download ──────────────────────────────────────────────────────────────────


@router.get("/{discipline_id}/download", tags=[_TAG], summary="Tải file đính kèm")
async def download_discipline_file(
    discipline_id: int,
    _: User = require_permission("disciplines:view"),
    session: AsyncSession = Depends(get_session),
):
    from app.models.discipline import EmployeeDiscipline
    record = await session.get(EmployeeDiscipline, discipline_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy quyết định kỷ luật")
    if not record.file_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không có file đính kèm")

    mime = record.mime_type or "application/octet-stream"
    filename = record.file_name or f"discipline_{discipline_id}"
    return StreamingResponse(
        get_object_stream(record.file_path),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Employee history ──────────────────────────────────────────────────────────


@employee_history_router.get("/{employee_id}/disciplines", response_model=list[DisciplineRead],
                              tags=[_TAG], summary="Lịch sử kỷ luật của nhân viên")
async def get_employee_discipline_history(
    employee_id: int,
    _: User = require_permission("disciplines:view"),
    session: AsyncSession = Depends(get_session),
):
    return await discipline_service.get_employee_discipline_history(session, employee_id)
