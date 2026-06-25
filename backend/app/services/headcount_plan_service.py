"""Service kế hoạch nhân sự (Headcount Plan) — 13.1."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.org import Department, JobPosition
from app.models.recruitment import HeadcountPlan, JobRequisition
from app.schemas.recruitment import (
    HeadcountPlanCreate,
    HeadcountPlanListPage,
    HeadcountPlanRead,
    HeadcountPlanUpdate,
)
from app.services import department_job_position_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _get_plan_or_404(session: AsyncSession, plan_id: int) -> HeadcountPlan:
    plan = await session.get(HeadcountPlan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kế hoạch nhân sự")
    return plan


async def _build_read(session: AsyncSession, plan: HeadcountPlan) -> HeadcountPlanRead:
    dept = await session.get(Department, plan.department_id) if plan.department_id else None
    pos = await session.get(JobPosition, plan.job_position_id) if plan.job_position_id else None
    creator = await session.get(User, plan.created_by_id) if plan.created_by_id else None
    return HeadcountPlanRead(
        id=plan.id,
        year=plan.year,
        department_id=plan.department_id,
        department_name=dept.name if dept else None,
        job_position_id=plan.job_position_id,
        job_position_name=pos.name if pos else None,
        current_count=plan.current_count,
        planned_count=plan.planned_count,
        reason=plan.reason,
        created_by_id=plan.created_by_id,
        created_by_name=creator.full_name if creator else None,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


async def list_headcount_plans(
    session: AsyncSession,
    *,
    year: Optional[int] = None,
    department_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> HeadcountPlanListPage:
    stmt = select(HeadcountPlan)
    if year is not None:
        stmt = stmt.where(HeadcountPlan.year == year)
    if department_id is not None:
        stmt = stmt.where(HeadcountPlan.department_id == department_id)

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = stmt.order_by(HeadcountPlan.year.desc(), HeadcountPlan.id)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    records = (await session.execute(stmt)).scalars().all()

    items = [await _build_read(session, r) for r in records]
    return HeadcountPlanListPage(items=items, total=total, page=page, page_size=page_size)


async def get_headcount_plan(session: AsyncSession, plan_id: int) -> HeadcountPlanRead:
    plan = await _get_plan_or_404(session, plan_id)
    return await _build_read(session, plan)


async def create_headcount_plan(
    session: AsyncSession,
    data: HeadcountPlanCreate,
    created_by_id: int,
) -> HeadcountPlanRead:
    if data.department_id is not None:
        dept = await session.get(Department, data.department_id)
        if not dept:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng ban")

    if data.job_position_id is not None:
        pos = await session.get(JobPosition, data.job_position_id)
        if not pos:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy vị trí công việc")
        if data.department_id is not None:
            await department_job_position_service.require_position_allowed_for_department(
                session,
                department_id=data.department_id,
                job_position_id=data.job_position_id,
            )

    # Kiểm tra trùng
    dup_stmt = select(HeadcountPlan).where(
        HeadcountPlan.year == data.year,
        HeadcountPlan.department_id == data.department_id,
        HeadcountPlan.job_position_id == data.job_position_id,
    )
    dup = (await session.execute(dup_stmt)).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Kế hoạch nhân sự cho năm, phòng ban và vị trí này đã tồn tại",
        )

    plan = HeadcountPlan(
        year=data.year,
        department_id=data.department_id,
        job_position_id=data.job_position_id,
        current_count=data.current_count,
        planned_count=data.planned_count,
        reason=data.reason,
        created_by_id=created_by_id,
    )
    session.add(plan)
    await session.flush()
    return await _build_read(session, plan)


async def update_headcount_plan(
    session: AsyncSession,
    plan_id: int,
    data: HeadcountPlanUpdate,
) -> HeadcountPlanRead:
    plan = await _get_plan_or_404(session, plan_id)

    if data.current_count is not None:
        plan.current_count = data.current_count
    if data.planned_count is not None:
        plan.planned_count = data.planned_count
    if data.reason is not None:
        plan.reason = data.reason

    plan.updated_at = _utcnow()
    session.add(plan)
    await session.flush()
    return await _build_read(session, plan)


async def delete_headcount_plan(session: AsyncSession, plan_id: int) -> None:
    plan = await _get_plan_or_404(session, plan_id)
    # Kiểm tra có JR nào đang tham chiếu không
    jr_stmt = select(func.count()).where(JobRequisition.headcount_plan_id == plan_id)
    jr_count = (await session.execute(jr_stmt)).scalar_one()
    if jr_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Không thể xóa — có {jr_count} yêu cầu tuyển dụng đang tham chiếu kế hoạch này",
        )
    await session.delete(plan)


async def get_fulfillment_rate(
    session: AsyncSession,
    year: int,
    department_id: Optional[int] = None,
) -> dict:
    """Tỷ lệ hoàn thành kế hoạch: JR completed / planned_count."""
    plan_stmt = select(HeadcountPlan).where(HeadcountPlan.year == year)
    if department_id is not None:
        plan_stmt = plan_stmt.where(HeadcountPlan.department_id == department_id)
    plans = (await session.execute(plan_stmt)).scalars().all()

    total_planned = sum(p.planned_count for p in plans)

    jr_stmt = (
        select(func.count())
        .where(
            JobRequisition.code.like(f"JR-{year}-%"),
            JobRequisition.status == "completed",
        )
    )
    if department_id is not None:
        jr_stmt = jr_stmt.where(JobRequisition.department_id == department_id)
    completed_jr = (await session.execute(jr_stmt)).scalar_one()

    rate = round(completed_jr / total_planned * 100, 1) if total_planned > 0 else 0.0

    return {
        "year": year,
        "department_id": department_id,
        "total_planned": total_planned,
        "completed_jr": completed_jr,
        "fulfillment_rate": rate,
    }
