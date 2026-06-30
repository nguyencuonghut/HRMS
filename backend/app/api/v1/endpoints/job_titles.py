from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_department_scope, require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.job_title import JobTitleCreate, JobTitleRead, JobTitleUpdate
from app.services import job_title_service

router = APIRouter()


@router.get("", response_model=list[JobTitleRead], summary="Danh sách chức danh")
async def list_job_titles(
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái; bỏ trống = lấy tất cả"),
    _: User = require_permission("org:view"),
    allowed_department_ids: set[int] | None = require_department_scope("org:view"),
    session: AsyncSession = Depends(get_session),
):
    if allowed_department_ids is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập danh mục chức danh dùng chung",
        )
    return await job_title_service.get_list(session, is_active=is_active)


@router.post("", response_model=JobTitleRead, status_code=status.HTTP_201_CREATED, summary="Tạo chức danh mới")
async def create_job_title(
    body: JobTitleCreate,
    _: User = require_permission("org:edit"),
    session: AsyncSession = Depends(get_session),
):
    return await job_title_service.create(session, body)


@router.put("/{jt_id}", response_model=JobTitleRead, summary="Cập nhật chức danh")
async def update_job_title(
    jt_id: int,
    body: JobTitleUpdate,
    _: User = require_permission("org:edit"),
    session: AsyncSession = Depends(get_session),
):
    return await job_title_service.update(session, jt_id, body)


@router.delete("/{jt_id}", summary="Xóa chức danh")
async def delete_job_title(
    jt_id: int,
    _: User = require_permission("org:edit"),
    session: AsyncSession = Depends(get_session),
):
    return await job_title_service.delete(session, jt_id)
