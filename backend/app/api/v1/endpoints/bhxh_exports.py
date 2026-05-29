"""Endpoints xuất biểu mẫu BHXH — D02-LT và D03-TS."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.services import bhxh_export_service

router = APIRouter()
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/d02-lt")
async def export_d02_lt(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    department_id: int | None = Query(None),
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    content = await bhxh_export_service.build_d02_lt(
        session, year=year, month=month, department_id=department_id
    )
    filename = f"D02-LT_T{month:02d}_{year}.xlsx"
    return Response(
        content=content,
        media_type=_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/d03-ts")
async def export_d03_ts(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    content = await bhxh_export_service.build_d03_ts(session, year=year, month=month)
    filename = f"D03-TS_T{month:02d}_{year}.xlsx"
    return Response(
        content=content,
        media_type=_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
