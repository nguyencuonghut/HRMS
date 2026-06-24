"""Endpoints báo cáo nhân sự (11.2)."""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.hr_report import (
    EmployeeListResponse,
    MovementReportResponse,
    OlderWorkerReportResponse,
    OrgStructureResponse,
    TenureReportResponse,
)
from app.services import hr_report_service

router = APIRouter()

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class GroupBy(str, Enum):
    month = "month"
    quarter = "quarter"
    year = "year"


class ExportType(str, Enum):
    employee_list = "employee-list"
    movement = "movement"
    tenure = "tenure"
    org_structure = "org-structure"
    older_worker = "older-worker"


@router.get("/employee-list", response_model=EmployeeListResponse, summary="Danh sách nhân sự")
async def get_employee_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    department_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    gender: Optional[str] = Query(None),
    document_kind: Optional[str] = Query(None),
    start_date_from: Optional[date] = Query(None),
    start_date_to: Optional[date] = Query(None),
    tenure_min: Optional[int] = Query(None, ge=0),
    tenure_max: Optional[int] = Query(None, ge=0),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> EmployeeListResponse:
    return await hr_report_service.get_employee_list(
        session,
        page=page,
        page_size=page_size,
        department_id=department_id,
        status=status_filter,
        gender=gender,
        document_kind=document_kind,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        tenure_min=tenure_min,
        tenure_max=tenure_max,
    )


@router.get("/movement", response_model=MovementReportResponse, summary="Biến động nhân sự")
async def get_movement_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    group_by: GroupBy = Query(GroupBy.month),
    department_id: Optional[int] = Query(None),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> MovementReportResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date phải ≤ end_date",
        )
    return await hr_report_service.get_movement_report(
        session,
        start_date=start_date,
        end_date=end_date,
        group_by=group_by.value,
        department_id=department_id,
    )


@router.get("/tenure", response_model=TenureReportResponse, summary="Báo cáo thâm niên")
async def get_tenure_report(
    department_id: Optional[int] = Query(None),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> TenureReportResponse:
    return await hr_report_service.get_tenure_report(session, department_id=department_id)


@router.get("/org-structure", response_model=OrgStructureResponse, summary="Cơ cấu tổ chức")
async def get_org_structure(
    department_id: Optional[int] = Query(None),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> OrgStructureResponse:
    return await hr_report_service.get_org_structure(session, department_id=department_id)


@router.get(
    "/older-workers",
    response_model=OlderWorkerReportResponse,
    summary="Báo cáo người lao động cao tuổi theo tháng",
)
async def get_older_worker_report(
    year: int = Query(..., ge=1900, le=2500),
    month: int = Query(..., ge=1, le=12),
    department_id: Optional[int] = Query(None),
    gender: Optional[str] = Query(None),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> OlderWorkerReportResponse:
    return await hr_report_service.get_older_worker_report(
        session,
        year=year,
        month=month,
        department_id=department_id,
        gender=gender,
    )


@router.get("/export", summary="Xuất Excel báo cáo nhân sự", response_class=StreamingResponse)
async def export_hr_report(
    type: ExportType = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    department_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    gender: Optional[str] = Query(None),
    document_kind: Optional[str] = Query(None),
    start_date_from: Optional[date] = Query(None),
    start_date_to: Optional[date] = Query(None),
    tenure_min: Optional[int] = Query(None, ge=0),
    tenure_max: Optional[int] = Query(None, ge=0),
    movement_start_date: Optional[date] = Query(None, alias="start_date"),
    movement_end_date: Optional[date] = Query(None, alias="end_date"),
    older_worker_year: Optional[int] = Query(None, alias="year", ge=1900, le=2500),
    older_worker_month: Optional[int] = Query(None, alias="month", ge=1, le=12),
    group_by: GroupBy = Query(GroupBy.month),
    _: User = require_permission("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    if type == ExportType.employee_list:
        buf = await hr_report_service.export_employee_list_excel(
            session,
            page=page,
            page_size=max(page_size, 10000),
            department_id=department_id,
            status=status_filter,
            gender=gender,
            document_kind=document_kind,
            start_date_from=start_date_from,
            start_date_to=start_date_to,
            tenure_min=tenure_min,
            tenure_max=tenure_max,
        )
    elif type == ExportType.movement:
        if movement_start_date is None or movement_end_date is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="start_date và end_date là bắt buộc cho export movement",
            )
        if movement_start_date > movement_end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="start_date phải ≤ end_date",
            )
        buf = await hr_report_service.export_movement_excel(
            session,
            start_date=movement_start_date,
            end_date=movement_end_date,
            group_by=group_by.value,
            department_id=department_id,
        )
    elif type == ExportType.tenure:
        buf = await hr_report_service.export_tenure_excel(session, department_id=department_id)
    elif type == ExportType.older_worker:
        if older_worker_year is None or older_worker_month is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="year và month là bắt buộc cho export older-worker",
            )
        buf = await hr_report_service.export_older_worker_excel(
            session,
            year=older_worker_year,
            month=older_worker_month,
            department_id=department_id,
            gender=gender,
        )
    else:
        buf = await hr_report_service.export_org_structure_excel(session, department_id=department_id)

    filename = f"bao_cao_nhan_su_{type.value}_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        buf,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
