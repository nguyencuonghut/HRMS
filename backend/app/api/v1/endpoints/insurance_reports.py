"""Endpoints Báo cáo Bảo hiểm Analytics (11.4)."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.insurance_analytics import (
    InsuranceDashboardKPI,
    InsuranceMonthlyChangesResponse,
    InsurancePayrollFundResponse,
    InsuranceNonParticipantsResponse,
    InsuranceDepartmentBreakdownResponse,
    InsuranceEmployeeHistoryResponse,
)
from app.services import insurance_analytics_service

router = APIRouter()


@router.get("/dashboard", response_model=InsuranceDashboardKPI)
async def get_dashboard(
    year: int = Query(..., ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    department_id: Optional[int] = Query(None),
    _current_user: User = require_permission("insurance:read"),
    session: AsyncSession = Depends(get_session),
) -> InsuranceDashboardKPI:
    return await insurance_analytics_service.get_dashboard(
        session,
        year=year,
        month=month,
        department_id=department_id,
    )


@router.get("/monthly-changes", response_model=InsuranceMonthlyChangesResponse)
async def get_monthly_changes(
    year: int = Query(..., ge=2000, le=2100),
    department_id: Optional[int] = Query(None),
    _current_user: User = require_permission("insurance:read"),
    session: AsyncSession = Depends(get_session),
) -> InsuranceMonthlyChangesResponse:
    return await insurance_analytics_service.get_monthly_changes(
        session,
        year=year,
        department_id=department_id,
    )


@router.get("/payroll-fund", response_model=InsurancePayrollFundResponse)
async def get_payroll_fund(
    year: int = Query(..., ge=2000, le=2100),
    department_id: Optional[int] = Query(None),
    _current_user: User = require_permission("insurance:read"),
    session: AsyncSession = Depends(get_session),
) -> InsurancePayrollFundResponse:
    return await insurance_analytics_service.get_payroll_fund(
        session,
        year=year,
        department_id=department_id,
    )


@router.get("/non-participants", response_model=InsuranceNonParticipantsResponse)
async def get_non_participants(
    department_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    _current_user: User = require_permission("insurance:read"),
    session: AsyncSession = Depends(get_session),
) -> InsuranceNonParticipantsResponse:
    return await insurance_analytics_service.get_non_participants(
        session,
        department_id=department_id,
        page=page,
        page_size=page_size,
    )


@router.get("/by-department", response_model=InsuranceDepartmentBreakdownResponse)
async def get_department_breakdown(
    year: int = Query(..., ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    _current_user: User = require_permission("insurance:read"),
    session: AsyncSession = Depends(get_session),
) -> InsuranceDepartmentBreakdownResponse:
    return await insurance_analytics_service.get_department_breakdown(
        session,
        year=year,
        month=month,
    )


@router.get("/employee-history", response_model=InsuranceEmployeeHistoryResponse)
async def get_employee_history(
    employee_id: int = Query(...),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    _current_user: User = require_permission("insurance:read"),
    session: AsyncSession = Depends(get_session),
) -> InsuranceEmployeeHistoryResponse:
    return await insurance_analytics_service.get_employee_history(
        session,
        employee_id=employee_id,
        year=year,
    )


@router.get("/export")
async def export_analytics(
    year: int = Query(..., ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    department_id: Optional[int] = Query(None),
    _current_user: User = require_permission("insurance:read"),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    buf = await insurance_analytics_service.export_analytics_xlsx(
        session,
        year=year,
        month=month,
        department_id=department_id,
    )
    filename = (
        f"bao_cao_bhxh_{year}_ca_nam.xlsx"
        if month is None
        else f"bao_cao_bhxh_{year}_{month}.xlsx"
    )
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
