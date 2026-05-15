"""Endpoints nhắc nhở sự kiện nhân sự (3.6)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.reminder import VALID_EVENT_TYPES, RemindersResponse
from app.services import reminder_service

router = APIRouter()


@router.get(
    "",
    response_model=RemindersResponse,
    summary="Danh sách sự kiện & nhắc nhở sắp đến",
)
async def get_reminders(
    days: int = Query(default=30, ge=1, le=90, description="Số ngày nhìn về phía trước"),
    types: Optional[str] = Query(
        default=None,
        description="Lọc loại sự kiện, phân cách bằng dấu phẩy: birthday,anniversary,probation_end",
    ),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
):
    parsed_types: Optional[set[str]] = None
    if types:
        parsed_types = {t.strip() for t in types.split(",") if t.strip() in VALID_EVENT_TYPES}
        if not parsed_types:
            parsed_types = None  # fallback: trả tất cả

    return await reminder_service.get_reminders(session, days=days, types=parsed_types)
