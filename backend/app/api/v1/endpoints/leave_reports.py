from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_department_scope, require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.leave_report import (
    DepartmentSummaryReport,
    EmployeeSummaryReport,
    YearEndReport,
)
from app.services import access_scope_service, leave_report_service

router = APIRouter()

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/employee-summary",
    response_model=EmployeeSummaryReport,
    summary="Báo cáo chi tiết nghỉ phép theo nhân viên",
)
async def employee_summary(
    year:          int           = Query(..., ge=2020, le=2100),
    employee_id:   Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    leave_type_id: Optional[int] = Query(None),
    keyword:       Optional[str] = Query(None),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(50, ge=1, le=200),
    current_user: User = require_permission("leaves:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.LEAVE_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
):
    if employee_id is not None:
        await access_scope_service.ensure_employee_access(
            session,
            current_user,
            permission_codes=access_scope_service.LEAVE_SCOPE_PERMISSIONS,
            employee_id=employee_id,
        )
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            current_user,
            permission_codes=access_scope_service.LEAVE_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    return await leave_report_service.get_employee_summary(
        session,
        year=year,
        employee_id=employee_id,
        department_id=department_id,
        leave_type_id=leave_type_id,
        keyword=keyword,
        allowed_department_ids=allowed_department_ids,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/department-summary",
    response_model=DepartmentSummaryReport,
    summary="Báo cáo tổng hợp nghỉ phép theo phòng ban",
)
async def department_summary(
    year:          int           = Query(..., ge=2020, le=2100),
    month_from:    Optional[int] = Query(None, ge=1, le=12),
    month_to:      Optional[int] = Query(None, ge=1, le=12),
    department_id: Optional[int] = Query(None),
    leave_type_id: Optional[int] = Query(None),
    current_user: User = require_permission("leaves:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.LEAVE_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
):
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            current_user,
            permission_codes=access_scope_service.LEAVE_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    return await leave_report_service.get_department_summary(
        session,
        year=year,
        month_from=month_from,
        month_to=month_to,
        department_id=department_id,
        leave_type_id=leave_type_id,
        allowed_department_ids=allowed_department_ids,
    )


@router.get(
    "/year-end",
    response_model=YearEndReport,
    summary="Báo cáo tồn phép cuối năm",
)
async def year_end(
    year:          int           = Query(..., ge=2020, le=2100),
    department_id: Optional[int] = Query(None),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(50, ge=1, le=200),
    current_user: User = require_permission("leaves:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.LEAVE_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
):
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            current_user,
            permission_codes=access_scope_service.LEAVE_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    return await leave_report_service.get_year_end(
        session,
        year=year,
        department_id=department_id,
        allowed_department_ids=allowed_department_ids,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/export",
    summary="Xuất báo cáo nghỉ phép ra Excel",
    response_class=StreamingResponse,
)
async def export(
    report_type:   Literal["A", "B", "C"] = Query(..., description="A=chi tiết NV, B=phòng ban, C=tồn phép"),
    year:          int                    = Query(..., ge=2020, le=2100),
    employee_id:   Optional[int]          = Query(None),
    department_id: Optional[int]          = Query(None),
    leave_type_id: Optional[int]          = Query(None),
    keyword:       Optional[str]          = Query(None),
    month_from:    Optional[int]          = Query(None, ge=1, le=12),
    month_to:      Optional[int]          = Query(None, ge=1, le=12),
    current_user: User = require_permission("leaves:view"),
    allowed_department_ids: set[int] | None = require_department_scope(*access_scope_service.LEAVE_SCOPE_PERMISSIONS),
    session: AsyncSession = Depends(get_session),
):
    if employee_id is not None:
        await access_scope_service.ensure_employee_access(
            session,
            current_user,
            permission_codes=access_scope_service.LEAVE_SCOPE_PERMISSIONS,
            employee_id=employee_id,
        )
    if department_id is not None:
        await access_scope_service.ensure_department_access(
            session,
            current_user,
            permission_codes=access_scope_service.LEAVE_SCOPE_PERMISSIONS,
            department_id=department_id,
        )
    if report_type == "A":
        report = await leave_report_service.get_employee_summary(
            session, year=year, employee_id=employee_id,
            department_id=department_id, leave_type_id=leave_type_id,
            keyword=keyword, allowed_department_ids=allowed_department_ids, page=1, page_size=10000,
        )
        buf = leave_report_service.export_employee_summary_xlsx(report)
        filename = f"bc_nghi_phep_nv_{year}.xlsx"

    elif report_type == "B":
        report = await leave_report_service.get_department_summary(
            session, year=year, month_from=month_from, month_to=month_to,
            department_id=department_id, leave_type_id=leave_type_id, allowed_department_ids=allowed_department_ids,
        )
        buf = leave_report_service.export_department_summary_xlsx(report)
        filename = f"bc_nghi_phep_phongban_{year}.xlsx"

    else:  # C
        report = await leave_report_service.get_year_end(
            session, year=year, department_id=department_id, allowed_department_ids=allowed_department_ids, page=1, page_size=10000,
        )
        buf = leave_report_service.export_year_end_xlsx(report)
        filename = f"bc_ton_phep_{year}.xlsx"

    return StreamingResponse(
        buf,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
