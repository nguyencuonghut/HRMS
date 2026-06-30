"""Audit Log API — xem lịch sử thao tác toàn hệ thống."""

from datetime import date, timedelta
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, outerjoin, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.audit_catalog import (
    AUDIT_ACTION_DEFS,
    AUDIT_ACTION_LABELS,
    AUDIT_ACTION_ORDER,
    AUDIT_ACTION_SEVERITIES,
    AUDIT_ENTITY_DEFS,
    AUDIT_ENTITY_LABELS,
    AUDIT_ENTITY_ORDER,
    AUDIT_ENTITY_SEVERITIES,
)
from app.core.database import get_session
from app.models.auth import AuditLog, User

router = APIRouter()


class AuditLogRead(BaseModel):
    id:          int
    user_id:     Optional[int]
    user_email:  Optional[str]
    user_name:   Optional[str]
    action:      str
    action_label: str
    action_order: int
    action_severity: str
    entity_type: Optional[str]
    entity_type_label: Optional[str]
    entity_type_order: Optional[int]
    entity_type_severity: Optional[str]
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
            action_label=AUDIT_ACTION_LABELS.get(log.action, log.action),
            action_order=AUDIT_ACTION_ORDER.get(log.action, 999),
            action_severity=AUDIT_ACTION_SEVERITIES.get(log.action, "secondary"),
            entity_type=log.entity_type,
            entity_type_label=AUDIT_ENTITY_LABELS.get(log.entity_type, log.entity_type) if log.entity_type else None,
            entity_type_order=AUDIT_ENTITY_ORDER.get(log.entity_type) if log.entity_type else None,
            entity_type_severity=AUDIT_ENTITY_SEVERITIES.get(log.entity_type, "secondary") if log.entity_type else None,
            entity_id=log.entity_id,
            entity_name=log.entity_name,
            old_data=log.old_data,
            new_data=log.new_data,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at.isoformat(),
        )


class AuditLogPageResponse(BaseModel):
    items:       list[AuditLogRead]
    total:       int
    page:        int
    page_size:   int
    total_pages: int


class AuditActionOption(BaseModel):
    code: str
    label: str
    severity: str
    order: int


class AuditEntityTypeOption(BaseModel):
    code: str
    label: str
    severity: str
    order: int


class AuditLogMetaResponse(BaseModel):
    actions: list[AuditActionOption]
    entity_types: list[AuditEntityTypeOption]


@router.get("/meta", response_model=AuditLogMetaResponse, summary="Metadata audit log")
async def get_audit_log_meta(
    _: User = require_permission("audit_logs:view"),
) -> AuditLogMetaResponse:
    return AuditLogMetaResponse(
        actions=[
            AuditActionOption(code=code, label=label, severity=severity, order=AUDIT_ACTION_ORDER[code])
            for code, label, severity in AUDIT_ACTION_DEFS
        ],
        entity_types=[
            AuditEntityTypeOption(code=code, label=label, severity=severity, order=AUDIT_ENTITY_ORDER[code])
            for code, label, severity in AUDIT_ENTITY_DEFS
        ],
    )


@router.get("", response_model=AuditLogPageResponse, summary="Lịch sử thao tác hệ thống")
async def list_audit_logs(
    user_id:     Optional[int]  = Query(None),
    action:      Optional[str]  = Query(None),
    entity_type: Optional[str]  = Query(None),
    entity_id:   Optional[int]  = Query(None),
    date_from:   Optional[date] = Query(None),
    date_to:     Optional[date] = Query(None),
    keyword:     Optional[str]  = Query(None, description="Tìm theo tên đối tượng / email / IP"),
    page:        int            = Query(1, ge=1),
    page_size:   int            = Query(20, ge=1, le=100),
    _:           User           = require_permission("audit_logs:view"),
    session:     AsyncSession   = Depends(get_session),
):
    j = outerjoin(AuditLog, User, AuditLog.user_id == User.id)
    base = select(AuditLog, User).select_from(j)

    if user_id is not None:
        base = base.where(AuditLog.user_id == user_id)
    if action:
        base = base.where(AuditLog.action == action.upper())
    if entity_type:
        base = base.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        base = base.where(AuditLog.entity_id == entity_id)
    if date_from:
        base = base.where(AuditLog.created_at >= date_from)
    if date_to:
        base = base.where(AuditLog.created_at < date_to + timedelta(days=1))
    if keyword:
        kw = f"%{keyword.strip()}%"
        base = base.where(
            or_(
                AuditLog.entity_name.ilike(kw),
                AuditLog.ip_address.ilike(kw),
                User.email.ilike(kw),
                User.full_name.ilike(kw),
            )
        )

    # Count
    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await session.execute(count_q)).scalar_one()

    # Page
    rows = (await session.execute(
        base.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
    )).all()

    return AuditLogPageResponse(
        items=[AuditLogRead.from_row(log, user) for log, user in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )
