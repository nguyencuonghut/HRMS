from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.salary import (
    BhxhSalaryHistoryItem,
    SalaryBhxhBasisDetail,
    SalaryEmployeeListPage,
)
from app.services import salary_service

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
