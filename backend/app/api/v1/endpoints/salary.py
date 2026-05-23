import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_admin_or_hr, require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.salary import (
    BhxhSalaryAdjustmentCreate,
    BhxhSalaryAdjustmentListPage,
    BhxhSalaryAdjustmentRead,
    BhxhSalaryHistoryItem,
    SalaryBhxhBasisDetail,
    SalaryEmployeeListPage,
    SalarySummaryPage,
)
from app.services import salary_export_service, salary_service

router = APIRouter()


@router.get("/employees", response_model=SalaryEmployeeListPage, summary="Danh sách mức lương BHXH")
async def list_salary_employees(
    department_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    participation_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await salary_service.list_salary_employees(
        session,
        department_id=department_id,
        search=search,
        participation_status=participation_status,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/employees/{employee_id}/bhxh-basis",
    response_model=SalaryBhxhBasisDetail,
    summary="Chi tiết mức lương BHXH của nhân viên",
)
async def get_employee_bhxh_basis(
    employee_id: int,
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await salary_service.get_employee_bhxh_basis(session, employee_id)


@router.get(
    "/employees/{employee_id}/bhxh-history",
    response_model=list[BhxhSalaryHistoryItem],
    summary="Lịch sử mức lương BHXH của nhân viên",
)
async def get_employee_bhxh_history(
    employee_id: int,
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await salary_service.get_employee_bhxh_history(session, employee_id)


# ── Adjustment endpoints ──────────────────────────────────────────────────────

@router.post(
    "/adjustments",
    response_model=BhxhSalaryAdjustmentRead,
    status_code=201,
    summary="Tạo điều chỉnh mức lương BHXH",
)
async def create_bhxh_adjustment(
    body: BhxhSalaryAdjustmentCreate,
    current_user: User = require_admin_or_hr(),
    session: AsyncSession = Depends(get_session),
):
    result = await salary_service.create_bhxh_adjustment(session, body, current_user.id)
    await session.commit()
    return result


@router.get(
    "/adjustments",
    response_model=BhxhSalaryAdjustmentListPage,
    summary="Danh sách điều chỉnh lương BHXH",
)
async def list_adjustments(
    employee_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await salary_service.list_adjustments(
        session,
        employee_id=employee_id,
        department_id=department_id,
        search=search,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/employees/{employee_id}/adjustment-history",
    response_model=list[BhxhSalaryAdjustmentRead],
    summary="Lịch sử điều chỉnh lương BHXH của nhân viên",
)
async def get_employee_adjustment_history(
    employee_id: int,
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await salary_service.get_employee_adjustment_history(session, employee_id)


# ── Summary endpoints ─────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=SalarySummaryPage,
    summary="Bảng tổng hợp lương BHXH theo tháng",
)
async def get_salary_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    department_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await salary_service.get_salary_summary(
        session,
        year=year,
        month=month,
        department_id=department_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/summary/export",
    summary="Xuất Excel bảng tổng hợp lương BHXH",
)
async def export_salary_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    department_id: Optional[int] = Query(None),
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    excel_bytes = await salary_export_service.export_salary_summary_excel(
        session, year=year, month=month, department_id=department_id
    )
    filename = f"luong_bhxh_{year}_{month:02d}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
