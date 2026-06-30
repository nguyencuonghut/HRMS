from datetime import date, timedelta
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_department_scope, require_permission
from app.core.database import get_session
from app.models.auth import User
from app.models.org import OrgChangeLog
from app.schemas.org_history import OrgHistoryRead

router = APIRouter()


class OrgHistoryPageResponse(BaseModel):
    items:       list[OrgHistoryRead]
    total:       int
    page:        int
    page_size:   int
    total_pages: int


@router.get("", response_model=OrgHistoryPageResponse, summary="Lịch sử thay đổi cơ cấu tổ chức")
async def list_org_history(
    entity_type: Optional[str] = Query(None),
    date_from:   Optional[date] = Query(None),
    date_to:     Optional[date] = Query(None),
    page:        int            = Query(1, ge=1),
    page_size:   int            = Query(20, ge=1, le=100),
    _: User = require_permission("org:view"),
    allowed_department_ids: set[int] | None = require_department_scope("org:view"),
    session: AsyncSession = Depends(get_session),
):
    if allowed_department_ids is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập lịch sử thay đổi cơ cấu tổ chức toàn công ty",
        )
    base = select(OrgChangeLog)

    if entity_type:
        base = base.where(OrgChangeLog.entity_type == entity_type)
    if date_from:
        base = base.where(OrgChangeLog.changed_at >= date_from)
    if date_to:
        base = base.where(OrgChangeLog.changed_at < date_to + timedelta(days=1))

    total: int = (await session.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar_one()

    rows = (await session.execute(
        base.order_by(OrgChangeLog.changed_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
    )).scalars().all()

    return OrgHistoryPageResponse(
        items=[OrgHistoryRead.from_orm_row(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )
