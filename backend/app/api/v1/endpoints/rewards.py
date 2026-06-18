"""Endpoints khen thưởng nhân viên (8.1)."""
from __future__ import annotations

import io
import json
from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.core.storage import get_object_stream
from app.models.auth import User
from app.schemas.reward import (
    RewardCreate,
    RewardListPage,
    RewardRead,
    RewardTypeCreate,
    RewardTypeRead,
    RewardTypeUpdate,
    RewardUpdate,
)
from app.schemas.reward_report import RewardDisciplineReportPage
from app.services import auth_service, reward_export_service, reward_report_service, reward_service

router = APIRouter()

_TAG = "Khen thưởng"
_TAG_CAT = "Danh mục khen thưởng"


# ── RewardType catalog ────────────────────────────────────────────────────────


@router.get("/types", response_model=list[RewardTypeRead], tags=[_TAG_CAT],
            summary="Danh sách loại khen thưởng")
async def list_reward_types(
    include_inactive: bool = Query(False),
    _: User = require_permission("rewards:view"),
    session: AsyncSession = Depends(get_session),
):
    return await reward_service.list_reward_types(session, include_inactive=include_inactive)


@router.post("/types", response_model=RewardTypeRead, status_code=status.HTTP_201_CREATED,
             tags=[_TAG_CAT], summary="Tạo loại khen thưởng")
async def create_reward_type(
    body: RewardTypeCreate,
    request: Request,
    current_user: User = require_permission("rewards:create"),
    session: AsyncSession = Depends(get_session),
):
    result = await reward_service.create_reward_type(session, body)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="reward_type", entity_id=result.id, entity_name=result.name,
    )
    await session.commit()
    return result


@router.put("/types/{type_id}", response_model=RewardTypeRead, tags=[_TAG_CAT],
            summary="Cập nhật loại khen thưởng")
async def update_reward_type(
    type_id: int,
    body: RewardTypeUpdate,
    request: Request,
    current_user: User = require_permission("rewards:edit"),
    session: AsyncSession = Depends(get_session),
):
    result = await reward_service.update_reward_type(session, type_id, body)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="reward_type", entity_id=type_id, entity_name=result.name,
    )
    await session.commit()
    return result


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT, tags=[_TAG_CAT],
               summary="Xóa loại khen thưởng")
async def delete_reward_type(
    type_id: int,
    request: Request,
    current_user: User = require_permission("rewards:delete"),
    session: AsyncSession = Depends(get_session),
):
    await reward_service.delete_reward_type(session, type_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="reward_type", entity_id=type_id,
    )
    await session.commit()


# ── EmployeeReward CRUD ───────────────────────────────────────────────────────


@router.get("", response_model=RewardListPage, tags=[_TAG],
            summary="Danh sách quyết định khen thưởng")
async def list_rewards(
    employee_id:    Optional[int]  = Query(None),
    reward_type_id: Optional[int]  = Query(None),
    department_id:  Optional[int]  = Query(None),
    from_date:      Optional[_date] = Query(None),
    to_date:        Optional[_date] = Query(None),
    search:         Optional[str]  = Query(None),
    page:           int            = Query(1, ge=1),
    page_size:      int            = Query(20, ge=1, le=200),
    _: User = require_permission("rewards:view"),
    session: AsyncSession = Depends(get_session),
):
    return await reward_service.list_rewards(
        session,
        employee_id=employee_id,
        reward_type_id=reward_type_id,
        department_id=department_id,
        from_date=from_date,
        to_date=to_date,
        search=search,
        page=page,
        page_size=page_size,
    )


# ── Report routes (must be before /{reward_id} to avoid path conflicts) ──────


@router.get("/report/summary", response_model=RewardDisciplineReportPage, tags=[_TAG],
            summary="Báo cáo tổng hợp khen thưởng – kỷ luật")
async def get_report_summary(
    from_date: _date = Query(...),
    to_date: _date = Query(...),
    department_id: Optional[int] = Query(None),
    reward_page: int = Query(1, ge=1),
    reward_page_size: int = Query(20, ge=1, le=200),
    discipline_page: int = Query(1, ge=1),
    discipline_page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("rewards:view"),
    session: AsyncSession = Depends(get_session),
):
    return await reward_report_service.get_reward_discipline_report(
        session,
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
        reward_page=reward_page,
        reward_page_size=reward_page_size,
        discipline_page=discipline_page,
        discipline_page_size=discipline_page_size,
    )


@router.get("/report/export", tags=[_TAG], summary="Xuất Excel khen thưởng – kỷ luật")
async def export_report_excel(
    from_date: _date = Query(...),
    to_date: _date = Query(...),
    department_id: Optional[int] = Query(None),
    _: User = require_permission("rewards:view"),
    session: AsyncSession = Depends(get_session),
):
    content = await reward_export_service.export_reward_discipline_excel(
        session,
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
    )
    filename = f"khen_thuong_ky_luat_{from_date}_{to_date}.xlsx"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{reward_id}", response_model=RewardRead, tags=[_TAG],
            summary="Chi tiết quyết định khen thưởng")
async def get_reward(
    reward_id: int,
    _: User = require_permission("rewards:view"),
    session: AsyncSession = Depends(get_session),
):
    return await reward_service.get_reward(session, reward_id)


@router.post("", response_model=RewardRead, status_code=status.HTTP_201_CREATED, tags=[_TAG],
             summary="Tạo quyết định khen thưởng")
async def create_reward(
    request: Request,
    # JSON body gửi dưới dạng Form field "body" (multipart)
    body: str = Form(..., description='JSON string của RewardCreate'),
    file: Optional[UploadFile] = File(None),
    current_user: User = require_permission("rewards:create"),
    session: AsyncSession = Depends(get_session),
):
    try:
        data = RewardCreate.model_validate(json.loads(body))
    except Exception as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))

    result = await reward_service.create_reward(session, data, file or None, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="employee_reward", entity_id=result.id,
        entity_name=f"{result.employee_name} {result.reward_date}",
    )
    await session.commit()
    return result


@router.put("/{reward_id}", response_model=RewardRead, tags=[_TAG],
            summary="Cập nhật quyết định khen thưởng")
async def update_reward(
    reward_id: int,
    request: Request,
    body: str = Form(..., description='JSON string của RewardUpdate'),
    file: Optional[UploadFile] = File(None),
    current_user: User = require_permission("rewards:create"),
    session: AsyncSession = Depends(get_session),
):
    try:
        data = RewardUpdate.model_validate(json.loads(body))
    except Exception as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))

    result = await reward_service.update_reward(session, reward_id, data, file or None)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="employee_reward", entity_id=reward_id,
        entity_name=f"{result.employee_name} {result.reward_date}",
    )
    await session.commit()
    return result


@router.delete("/{reward_id}", status_code=status.HTTP_204_NO_CONTENT, tags=[_TAG],
               summary="Xóa quyết định khen thưởng")
async def delete_reward(
    reward_id: int,
    request: Request,
    current_user: User = require_permission("rewards:delete"),
    session: AsyncSession = Depends(get_session),
):
    await reward_service.delete_reward(session, reward_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="employee_reward", entity_id=reward_id,
    )
    await session.commit()


@router.get("/{reward_id}/download", tags=[_TAG], summary="Tải file đính kèm")
async def download_reward_file(
    reward_id: int,
    _: User = require_permission("rewards:view"),
    session: AsyncSession = Depends(get_session),
):
    from app.services.reward_service import _get_reward_or_404
    record = await _get_reward_or_404(session, reward_id)
    if not record.file_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Quyết định chưa có file đính kèm")
    filename = record.file_name or "quyet_dinh.pdf"
    return StreamingResponse(
        get_object_stream(record.file_path),
        media_type=record.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Employee reward history (dùng trong hồ sơ NV) ────────────────────────────

employee_history_router = APIRouter()


@employee_history_router.get(
    "/{employee_id}/rewards",
    response_model=list[RewardRead],
    tags=[_TAG],
    summary="Lịch sử khen thưởng của nhân viên",
)
async def get_employee_rewards(
    employee_id: int,
    _: User = require_permission("rewards:view"),
    session: AsyncSession = Depends(get_session),
):
    return await reward_service.get_employee_reward_history(session, employee_id)
