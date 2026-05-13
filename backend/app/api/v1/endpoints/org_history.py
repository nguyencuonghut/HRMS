from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.org import OrgChangeLog
from app.schemas.org_history import OrgHistoryRead

router = APIRouter()


@router.get("", response_model=list[OrgHistoryRead], summary="Lịch sử thay đổi cơ cấu tổ chức")
async def list_org_history(
    entity_type: Optional[str] = Query(None, description="Lọc theo loại: department | job_title | job_position"),
    date_from:   Optional[date] = Query(None, description="Từ ngày (YYYY-MM-DD)"),
    date_to:     Optional[date] = Query(None, description="Đến ngày (YYYY-MM-DD)"),
    limit:       int            = Query(200, ge=1, le=1000, description="Số bản ghi tối đa"),
    session: AsyncSession = Depends(get_session),
):
    q = select(OrgChangeLog).order_by(OrgChangeLog.changed_at.desc()).limit(limit)

    if entity_type:
        q = q.where(OrgChangeLog.entity_type == entity_type)
    if date_from:
        q = q.where(OrgChangeLog.changed_at >= date_from)
    if date_to:
        q = q.where(OrgChangeLog.changed_at < date_to + timedelta(days=1))

    rows = (await session.execute(q)).scalars().all()
    return [OrgHistoryRead.from_orm_row(r) for r in rows]
