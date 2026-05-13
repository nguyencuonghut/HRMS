"""Audit Log API — xem lịch sử thao tác toàn hệ thống."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import outerjoin, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import AuditLog, User

router = APIRouter()


class AuditLogRead(BaseModel):
    id:          int
    user_id:     Optional[int]
    user_email:  Optional[str]
    user_name:   Optional[str]
    action:      str
    entity_type: Optional[str]
    entity_id:   Optional[int]
    entity_name: Optional[str]
    old_data:    Optional[dict]
    new_data:    Optional[dict]
    ip_address:  Optional[str]
    user_agent:  Optional[str]
    created_at:  str

    model_config = {"from_attributes": True}

    @classmethod
    def from_row(cls, log: AuditLog, user: Optional[User] = None) -> "AuditLogRead":
        return cls(
            id=log.id,
            user_id=log.user_id,
            user_email=user.email if user else None,
            user_name=user.full_name if user else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            entity_name=log.entity_name,
            old_data=log.old_data,
            new_data=log.new_data,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at.isoformat(),
        )


@router.get("", response_model=list[AuditLogRead], summary="Lịch sử thao tác hệ thống")
async def list_audit_logs(
    user_id:     Optional[int]  = Query(None, description="Lọc theo user_id"),
    action:      Optional[str]  = Query(None, description="Lọc theo action: LOGIN, CREATE, UPDATE, DELETE, ..."),
    entity_type: Optional[str]  = Query(None, description="Lọc theo loại đối tượng"),
    entity_id:   Optional[int]  = Query(None, description="Lọc theo ID đối tượng"),
    date_from:   Optional[date] = Query(None, description="Từ ngày (YYYY-MM-DD)"),
    date_to:     Optional[date] = Query(None, description="Đến ngày (YYYY-MM-DD)"),
    limit:       int            = Query(100, ge=1, le=500, description="Số bản ghi tối đa"),
    _:           User           = require_permission("audit_logs:view"),
    session:     AsyncSession   = Depends(get_session),
):
    j = outerjoin(AuditLog, User, AuditLog.user_id == User.id)
    q = (
        select(AuditLog, User)
        .select_from(j)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )

    if user_id is not None:
        q = q.where(AuditLog.user_id == user_id)
    if action:
        q = q.where(AuditLog.action == action.upper())
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        q = q.where(AuditLog.entity_id == entity_id)
    if date_from:
        q = q.where(AuditLog.created_at >= date_from)
    if date_to:
        q = q.where(AuditLog.created_at < date_to + timedelta(days=1))

    rows = (await session.execute(q)).all()
    return [AuditLogRead.from_row(log, user) for log, user in rows]
