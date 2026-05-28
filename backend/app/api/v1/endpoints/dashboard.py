"""Endpoints cho dashboard tổng quan nhân sự (11.1)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.dashboard import (
    DashboardSummary,
    HeadcountByDeptItem,
    MonthlyTrendReport,
    StructureReport,
)
from app.services import dashboard_service

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary, summary="Tóm tắt KPI dashboard nhân sự")
async def get_dashboard_summary(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    department_id: Optional[int] = Query(None),
    _: User = require_permission("employees:view", "employees:read"),
    session: AsyncSession = Depends(get_session),
):
    return await dashboard_service.get_summary(
        session,
        year=year,
        month=month,
        department_id=department_id,
    )


@router.get("/headcount-by-dept", response_model=list[HeadcountByDeptItem], summary="Headcount theo phòng ban")
async def get_dashboard_headcount_by_dept(
    department_id: Optional[int] = Query(None),
    _: User = require_permission("employees:view", "employees:read"),
    session: AsyncSession = Depends(get_session),
):
    return await dashboard_service.get_headcount_by_dept(session, department_id=department_id)


@router.get("/monthly-trend", response_model=MonthlyTrendReport, summary="Biến động nhân sự 12 tháng")
async def get_dashboard_monthly_trend(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    department_id: Optional[int] = Query(None),
    _: User = require_permission("employees:view", "employees:read"),
    session: AsyncSession = Depends(get_session),
):
    return await dashboard_service.get_monthly_trend(
        session,
        year=year,
        department_id=department_id,
    )


@router.get("/structure", response_model=StructureReport, summary="Cơ cấu nhân sự cho dashboard")
async def get_dashboard_structure(
    department_id: Optional[int] = Query(None),
    _: User = require_permission("employees:view", "employees:read"),
    session: AsyncSession = Depends(get_session),
):
    return await dashboard_service.get_structure(session, department_id=department_id)
