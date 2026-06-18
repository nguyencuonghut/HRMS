"""Endpoints Leave Analytics (11.3)."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_department_scope, require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.leave_analytics import (
    DeptComparisonReport,
    ExpiringBalanceReport,
    LeaveAnalyticsSummary,
    LeaveByTypeReport,
    MonthlyHeatmapReport,
    TopEmployeesReport,
)
from app.services import access_scope_service, leave_analytics_service

router = APIRouter()


@router.get("/analytics-summary", response_model=LeaveAnalyticsSummary)
async def get_analytics_summary(
    year: int = Query(..., ge=2000, le=2100),
    department_id: int | None = Query(None),
    leave_type_id: int | None = Query(None),
    _current_user: User = require_permission("leaves:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.LEAVE_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> LeaveAnalyticsSummary:
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            _current_user,
            permission_codes=access_scope_service.LEAVE_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    scope_for_service = None if department_id is not None else allowed_department_ids
    return await leave_analytics_service.get_analytics_summary(
        session,
        year=year,
        department_id=department_id,
        leave_type_id=leave_type_id,
        allowed_department_ids=scope_for_service,
    )


@router.get("/by-type", response_model=LeaveByTypeReport)
async def get_by_type(
    year: int = Query(..., ge=2000, le=2100),
    department_id: int | None = Query(None),
    _current_user: User = require_permission("leaves:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.LEAVE_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> LeaveByTypeReport:
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            _current_user,
            permission_codes=access_scope_service.LEAVE_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    scope_for_service = None if department_id is not None else allowed_department_ids
    return await leave_analytics_service.get_by_type(
        session,
        year=year,
        department_id=department_id,
        allowed_department_ids=scope_for_service,
    )


@router.get("/monthly-heatmap", response_model=MonthlyHeatmapReport)
async def get_monthly_heatmap(
    year: int = Query(..., ge=2000, le=2100),
    _current_user: User = require_permission("leaves:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.LEAVE_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> MonthlyHeatmapReport:
    return await leave_analytics_service.get_monthly_heatmap(
        session,
        year=year,
        allowed_department_ids=allowed_department_ids,
    )


@router.get("/top-employees", response_model=TopEmployeesReport)
async def get_top_employees(
    year: int = Query(..., ge=2000, le=2100),
    department_id: int | None = Query(None),
    leave_type_id: int | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    _current_user: User = require_permission("leaves:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.LEAVE_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> TopEmployeesReport:
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            _current_user,
            permission_codes=access_scope_service.LEAVE_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    scope_for_service = None if department_id is not None else allowed_department_ids
    return await leave_analytics_service.get_top_employees(
        session,
        year=year,
        department_id=department_id,
        leave_type_id=leave_type_id,
        allowed_department_ids=scope_for_service,
        limit=limit,
    )


@router.get("/expiring-balance", response_model=ExpiringBalanceReport)
async def get_expiring_balance(
    year: int = Query(..., ge=2000, le=2100),
    department_id: int | None = Query(None),
    expire_days: int = Query(30, ge=1, le=365),
    _current_user: User = require_permission("leaves:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.LEAVE_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> ExpiringBalanceReport:
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            _current_user,
            permission_codes=access_scope_service.LEAVE_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    scope_for_service = None if department_id is not None else allowed_department_ids
    return await leave_analytics_service.get_expiring_balance(
        session,
        year=year,
        department_id=department_id,
        allowed_department_ids=scope_for_service,
        expire_days=expire_days,
    )


@router.get("/department-comparison", response_model=DeptComparisonReport)
async def get_department_comparison(
    year: int = Query(..., ge=2000, le=2100),
    _current_user: User = require_permission("leaves:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.LEAVE_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> DeptComparisonReport:
    return await leave_analytics_service.get_department_comparison(
        session,
        year=year,
        allowed_department_ids=allowed_department_ids,
    )


@router.get("/export-analytics")
async def export_analytics(
    year: int = Query(..., ge=2000, le=2100),
    department_id: int | None = Query(None),
    _current_user: User = require_permission("leaves:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.LEAVE_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            _current_user,
            permission_codes=access_scope_service.LEAVE_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    scope_for_service = None if department_id is not None else allowed_department_ids
    summary = await leave_analytics_service.get_analytics_summary(
        session, year=year, department_id=department_id, allowed_department_ids=scope_for_service
    )
    by_type = await leave_analytics_service.get_by_type(
        session, year=year, department_id=department_id, allowed_department_ids=scope_for_service
    )
    heatmap = await leave_analytics_service.get_monthly_heatmap(
        session,
        year=year,
        allowed_department_ids=allowed_department_ids,
    )
    top = await leave_analytics_service.get_top_employees(
        session, year=year, department_id=department_id, allowed_department_ids=scope_for_service
    )

    buf = leave_analytics_service.build_analytics_xlsx(summary, by_type, heatmap, top)
    filename = f"phan_tich_nghi_phep_{year}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
