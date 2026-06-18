"""Endpoints báo cáo Onboarding & Thử việc (Plan 14.3)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_department_scope, require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.probation_report import (
    ActiveProbationReport,
    ChecklistCompletionReport,
    FailureReasonReport,
    ProbationHistoryReport,
    ProbationPassRateReport,
)
from app.services import probation_report_service

router = APIRouter()

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/active",
    response_model=ActiveProbationReport,
    summary="Danh sách nhân viên đang thử việc",
)
async def get_active(
    department_id: Optional[int] = Query(None, description="Lọc theo phòng ban"),
    keyword: Optional[str] = Query(None, description="Tìm theo tên hoặc mã nhân viên"),
    current_user: User = require_permission("employees:view"),
    allowed_department_ids: set[int] | None = require_department_scope("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> ActiveProbationReport:
    return await probation_report_service.get_active_probation(
        session,
        department_id=department_id,
        keyword=keyword,
        allowed_department_ids=allowed_department_ids,
    )


@router.get(
    "/history",
    response_model=ProbationHistoryReport,
    summary="Nhân viên từng thử việc trong kỳ (bao gồm đã hoàn thành)",
)
async def get_history(
    start_date: Optional[date] = Query(None, description="Từ ngày bắt đầu thử việc"),
    end_date: Optional[date] = Query(None, description="Đến ngày bắt đầu thử việc"),
    department_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None, description="Tìm theo tên hoặc mã nhân viên"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = require_permission("employees:view"),
    allowed_department_ids: set[int] | None = require_department_scope("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> ProbationHistoryReport:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date phải ≤ end_date",
        )
    return await probation_report_service.get_probation_history(
        session,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
        keyword=keyword,
        allowed_department_ids=allowed_department_ids,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/checklist-completion",
    response_model=ChecklistCompletionReport,
    summary="Tỷ lệ hoàn thành Checklist onboarding theo phòng ban",
)
async def get_checklist_completion(
    start_date: date = Query(..., description="Từ ngày (start_date của nhân viên)"),
    end_date: date = Query(..., description="Đến ngày"),
    department_id: Optional[int] = Query(None),
    current_user: User = require_permission("employees:view"),
    allowed_department_ids: set[int] | None = require_department_scope("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> ChecklistCompletionReport:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date phải ≤ end_date",
        )
    return await probation_report_service.get_checklist_completion(
        session,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
        allowed_department_ids=allowed_department_ids,
    )


@router.get(
    "/pass-rate",
    response_model=ProbationPassRateReport,
    summary="Tỷ lệ vượt thử việc theo kỳ",
)
async def get_pass_rate(
    start_date: date = Query(...),
    end_date: date = Query(...),
    department_id: Optional[int] = Query(None),
    current_user: User = require_permission("employees:view"),
    allowed_department_ids: set[int] | None = require_department_scope("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> ProbationPassRateReport:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date phải ≤ end_date",
        )
    return await probation_report_service.get_pass_rate(
        session,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
        allowed_department_ids=allowed_department_ids,
    )


@router.get(
    "/failure-reasons",
    response_model=FailureReasonReport,
    summary="Phân tích lý do không đạt thử việc",
)
async def get_failure_reasons(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = require_permission("employees:view"),
    allowed_department_ids: set[int] | None = require_department_scope("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> FailureReasonReport:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date phải ≤ end_date",
        )
    return await probation_report_service.get_failure_reasons(
        session,
        start_date=start_date,
        end_date=end_date,
        allowed_department_ids=allowed_department_ids,
    )


@router.get(
    "/export",
    summary="Xuất báo cáo thử việc ra Excel",
    response_class=StreamingResponse,
)
async def export(
    start_date: date = Query(...),
    end_date: date = Query(...),
    department_id: Optional[int] = Query(None),
    current_user: User = require_permission("employees:view"),
    allowed_department_ids: set[int] | None = require_department_scope("employees:view"),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date phải ≤ end_date",
        )
    try:
        buf = await probation_report_service.export_excel(
            session,
            start_date=start_date,
            end_date=end_date,
            department_id=department_id,
            allowed_department_ids=allowed_department_ids,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    filename = f"bc_thu_viec_{start_date}_{end_date}.xlsx"
    return StreamingResponse(
        buf,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
