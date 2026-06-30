"""Endpoints quản lý Thông báo & Nhắc việc tự động (Plan 12.3)."""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.notification_catalog import (
    NOTIFICATION_EVENT_DEFS,
    NOTIFICATION_EVENT_LABELS,
    NOTIFICATION_EVENT_ORDER,
    NOTIFICATION_STATUS_DEFS,
    NOTIFICATION_STATUS_ORDER,
)
from app.core.database import get_session
from app.models.auth import User
from app.models.notification import EmailLog, NotificationTemplate, NotifConfig
from app.schemas.notification import (
    ConfigResponse,
    NotificationEventOption,
    NotificationMetaResponse,
    NotificationStatusOption,
    ConfigUpdate,
    LogItem,
    LogListResponse,
    PreviewRequest,
    PreviewResponse,
    TemplateResponse,
    TemplateUpdate,
    TestSendRequest,
)
from app.services import notification_service

router = APIRouter()


def _to_template_response(row: NotificationTemplate) -> TemplateResponse:
    return TemplateResponse(
        id=row.id,
        code=row.code,
        event_type=row.event_type,
        event_type_label=NOTIFICATION_EVENT_LABELS.get(row.event_type, row.event_type),
        event_type_order=NOTIFICATION_EVENT_ORDER.get(row.event_type, 999),
        name=row.name,
        subject=row.subject,
        body_html=row.body_html,
        body_text=row.body_text,
        merge_fields=row.merge_fields,
        is_active=row.is_active,
        is_system=row.is_system,
        days_before=row.days_before,
        recipient_type=row.recipient_type,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_config_response(row: NotifConfig) -> ConfigResponse:
    return ConfigResponse(
        id=row.id,
        event_type=row.event_type,
        event_type_label=NOTIFICATION_EVENT_LABELS.get(row.event_type, row.event_type),
        event_type_order=NOTIFICATION_EVENT_ORDER.get(row.event_type, 999),
        is_enabled=row.is_enabled,
        days_before=row.days_before,
        extra_recipients=row.extra_recipients,
        updated_at=row.updated_at,
    )


def _to_log_item(row: EmailLog) -> LogItem:
    return LogItem(
        id=row.id,
        template_code=row.template_code,
        event_type=row.event_type,
        event_type_label=NOTIFICATION_EVENT_LABELS.get(row.event_type, row.event_type),
        event_type_order=NOTIFICATION_EVENT_ORDER.get(row.event_type, 999),
        employee_id=row.employee_id,
        recipient_email=row.recipient_email,
        recipient_name=row.recipient_name,
        subject=row.subject,
        status=row.status,
        error_message=row.error_message,
        sent_at=row.sent_at,
        celery_task_id=row.celery_task_id,
    )


@router.get("/meta", response_model=NotificationMetaResponse)
async def get_notification_meta(
    _: User = require_permission("settings:view"),
) -> NotificationMetaResponse:
    return NotificationMetaResponse(
        event_types=[
            NotificationEventOption(code=code, label=label, order=index)
            for index, (code, label) in enumerate(NOTIFICATION_EVENT_DEFS, start=1)
        ],
        statuses=[
            NotificationStatusOption(code=code, label=label, severity=severity, order=NOTIFICATION_STATUS_ORDER[code])
            for code, label, severity in NOTIFICATION_STATUS_DEFS
        ],
    )


# ─── Templates ────────────────────────────────────────────────────────────────

@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    _: User = require_permission("settings:view"),
    session: AsyncSession = Depends(get_session),
) -> list[TemplateResponse]:
    rows = (await session.execute(select(NotificationTemplate).order_by(NotificationTemplate.id))).scalars().all()
    return [_to_template_response(r) for r in rows]


@router.get("/templates/{code}", response_model=TemplateResponse)
async def get_template(
    code: str,
    _: User = require_permission("settings:view"),
    session: AsyncSession = Depends(get_session),
) -> TemplateResponse:
    tpl = (
        await session.execute(select(NotificationTemplate).where(NotificationTemplate.code == code))
    ).scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail=f"Template '{code}' không tồn tại")
    return _to_template_response(tpl)


@router.put("/templates/{code}", response_model=TemplateResponse)
async def update_template(
    code: str,
    payload: TemplateUpdate,
    _: User = require_permission("settings:edit"),
    session: AsyncSession = Depends(get_session),
) -> TemplateResponse:
    tpl = (
        await session.execute(select(NotificationTemplate).where(NotificationTemplate.code == code))
    ).scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail=f"Template '{code}' không tồn tại")

    if payload.subject is not None:
        tpl.subject = payload.subject
    if payload.body_html is not None:
        tpl.body_html = payload.body_html
    if payload.is_active is not None:
        tpl.is_active = payload.is_active

    from datetime import timezone
    tpl.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.commit()
    await session.refresh(tpl)
    return _to_template_response(tpl)


@router.post("/templates/{code}/preview", response_model=PreviewResponse)
async def preview_template(
    code: str,
    payload: PreviewRequest,
    _: User = require_permission("settings:view"),
    session: AsyncSession = Depends(get_session),
) -> PreviewResponse:
    tpl = (
        await session.execute(select(NotificationTemplate).where(NotificationTemplate.code == code))
    ).scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail=f"Template '{code}' không tồn tại")
    html = notification_service._render_template(tpl.body_html, payload.sample_data)
    return PreviewResponse(html=html)


# ─── Config ───────────────────────────────────────────────────────────────────

@router.get("/config", response_model=list[ConfigResponse])
async def list_config(
    _: User = require_permission("settings:view"),
    session: AsyncSession = Depends(get_session),
) -> list[ConfigResponse]:
    rows = (await session.execute(select(NotifConfig).order_by(NotifConfig.id))).scalars().all()
    return [_to_config_response(r) for r in rows]


@router.put("/config/{event_type}", response_model=ConfigResponse)
async def update_config(
    event_type: str,
    payload: ConfigUpdate,
    _: User = require_permission("settings:edit"),
    session: AsyncSession = Depends(get_session),
) -> ConfigResponse:
    cfg = (
        await session.execute(select(NotifConfig).where(NotifConfig.event_type == event_type))
    ).scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Config event_type '{event_type}' không tồn tại")

    if payload.is_enabled is not None:
        cfg.is_enabled = payload.is_enabled
    if payload.extra_recipients is not None:
        cfg.extra_recipients = payload.extra_recipients

    from datetime import timezone
    cfg.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.commit()
    await session.refresh(cfg)
    return _to_config_response(cfg)


# ─── Logs ─────────────────────────────────────────────────────────────────────

@router.get("/logs", response_model=LogListResponse)
async def list_logs(
    event_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = require_permission("settings:view"),
    session: AsyncSession = Depends(get_session),
) -> LogListResponse:
    q = select(EmailLog)
    count_q = select(func.count()).select_from(EmailLog)

    if event_type:
        q = q.where(EmailLog.event_type == event_type)
        count_q = count_q.where(EmailLog.event_type == event_type)
    if status:
        q = q.where(EmailLog.status == status)
        count_q = count_q.where(EmailLog.status == status)
    if from_date:
        q = q.where(func.date(EmailLog.sent_at) >= from_date)
        count_q = count_q.where(func.date(EmailLog.sent_at) >= from_date)
    if to_date:
        q = q.where(func.date(EmailLog.sent_at) <= to_date)
        count_q = count_q.where(func.date(EmailLog.sent_at) <= to_date)

    total = (await session.execute(count_q)).scalar_one()
    offset = (page - 1) * page_size
    rows = (
        await session.execute(q.order_by(EmailLog.sent_at.desc()).offset(offset).limit(page_size))
    ).scalars().all()

    return LogListResponse(
        items=[_to_log_item(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


# ─── Test send ────────────────────────────────────────────────────────────────

@router.post("/test-send")
async def test_send(
    payload: TestSendRequest,
    _: User = require_permission("settings:edit"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    ok = await notification_service.send_notification_email(
        payload.template_code,
        payload.recipient_email,
        "Test Recipient",
        {"company_name": "Test Company"},
        session,
    )
    if ok:
        return {"message": f"Email đã gửi (hoặc skipped) tới {payload.recipient_email}"}
    raise HTTPException(status_code=500, detail="Gửi email thất bại, kiểm tra logs")
