"""Service kế hoạch đào tạo (9.1 Slice 2)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.org import Department
from app.models.training import TrainingCourse, TrainingPlan, TrainingPlanCourse
from app.schemas.training import (
    COURSE_TYPES,
    PLAN_STATUSES,
    PlanCourseCreate,
    PlanCourseRead,
    PlanCourseUpdate,
    PlanCreate,
    PlanListPage,
    PlanRead,
    PlanReadDetail,
    PlanUpdate,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_plan_or_404(session: AsyncSession, plan_id: int) -> TrainingPlan:
    plan = await session.get(TrainingPlan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kế hoạch đào tạo")
    return plan


async def _build_plan_read(
    session: AsyncSession,
    plan: TrainingPlan,
    dept_name: Optional[str],
    course_count: int,
) -> PlanRead:
    created_by_name: Optional[str] = None
    if plan.created_by_id:
        creator = await session.get(User, plan.created_by_id)
        if creator:
            created_by_name = getattr(creator, "full_name", None) or creator.email

    return PlanRead(
        id=plan.id,
        title=plan.title,
        year=plan.year,
        quarter=plan.quarter,
        department_id=plan.department_id,
        department_name=dept_name,
        status=plan.status,
        status_label=PLAN_STATUSES.get(plan.status, plan.status),
        description=plan.description,
        created_by_name=created_by_name,
        created_at=plan.created_at,
        course_count=course_count,
    )


def _build_plan_course_read(pc: TrainingPlanCourse, course: TrainingCourse) -> PlanCourseRead:
    return PlanCourseRead(
        id=pc.id,
        plan_id=pc.plan_id,
        course_id=pc.course_id,
        course_code=course.code,
        course_name=course.name,
        course_type_label=COURSE_TYPES.get(course.course_type, course.course_type),
        duration_hours=course.duration_hours,
        target_count=pc.target_count,
        scheduled_date=pc.scheduled_date,
        note=pc.note,
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def list_plans(
    session: AsyncSession,
    *,
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> PlanListPage:
    course_count_sq = (
        select(func.count())
        .where(TrainingPlanCourse.plan_id == TrainingPlan.id)
        .correlate(TrainingPlan)
        .scalar_subquery()
    )

    stmt = (
        select(
            TrainingPlan,
            Department.name.label("dept_name"),
            course_count_sq.label("course_count"),
        )
        .outerjoin(Department, Department.id == TrainingPlan.department_id)
    )

    if year is not None:
        stmt = stmt.where(TrainingPlan.year == year)
    if quarter is not None and quarter != 0:
        stmt = stmt.where(TrainingPlan.quarter == quarter)
    if department_id is not None:
        stmt = stmt.where(TrainingPlan.department_id == department_id)
    if status is not None:
        stmt = stmt.where(TrainingPlan.status == status)

    total_stmt = select(func.count()).select_from(
        select(TrainingPlan)
        .outerjoin(Department, Department.id == TrainingPlan.department_id)
        .filter(
            *([TrainingPlan.year == year] if year is not None else []),
            *([TrainingPlan.quarter == quarter] if quarter is not None and quarter != 0 else []),
            *([TrainingPlan.department_id == department_id] if department_id is not None else []),
            *([TrainingPlan.status == status] if status is not None else []),
        )
        .subquery()
    )
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = (
        stmt
        .order_by(TrainingPlan.year.desc(), TrainingPlan.quarter.asc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(stmt)).all()

    items: List[PlanRead] = []
    for row in rows:
        plan = row[0]
        dept_name = row[1]
        c_count = row[2] or 0
        items.append(await _build_plan_read(session, plan, dept_name, c_count))

    return PlanListPage(items=items, total=total, page=page, page_size=page_size)


async def get_plan(session: AsyncSession, plan_id: int) -> PlanRead:
    plan = await _get_plan_or_404(session, plan_id)
    dept_name: Optional[str] = None
    if plan.department_id:
        dept = await session.get(Department, plan.department_id)
        dept_name = dept.name if dept else None

    c_count = (
        await session.execute(
            select(func.count()).where(TrainingPlanCourse.plan_id == plan_id)
        )
    ).scalar_one()

    return await _build_plan_read(session, plan, dept_name, c_count)


async def get_plan_detail(session: AsyncSession, plan_id: int) -> PlanReadDetail:
    plan_read = await get_plan(session, plan_id)
    plan = await session.get(TrainingPlan, plan_id)

    dept_name: Optional[str] = None
    if plan.department_id:
        dept = await session.get(Department, plan.department_id)
        dept_name = dept.name if dept else None

    c_count = (
        await session.execute(
            select(func.count()).where(TrainingPlanCourse.plan_id == plan_id)
        )
    ).scalar_one()

    plan_courses = await list_plan_courses(session, plan_id)

    return PlanReadDetail(
        **plan_read.model_dump(),
        courses=plan_courses,
    )


async def create_plan(
    session: AsyncSession,
    data: PlanCreate,
    created_by_id: int,
) -> TrainingPlan:
    if data.department_id is not None:
        dept = await session.get(Department, data.department_id)
        if not dept:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng ban")

    plan = TrainingPlan(
        title=data.title,
        year=data.year,
        quarter=data.quarter,
        department_id=data.department_id,
        description=data.description,
        status="draft",
        created_by_id=created_by_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(plan)
    await session.flush()
    return plan


async def update_plan(
    session: AsyncSession,
    plan_id: int,
    data: PlanUpdate,
) -> TrainingPlan:
    plan = await _get_plan_or_404(session, plan_id)

    if data.title is not None:
        plan.title = data.title
    if data.description is not None:
        plan.description = data.description

    plan.updated_at = _utcnow()
    session.add(plan)
    await session.flush()
    return plan


async def delete_plan(session: AsyncSession, plan_id: int) -> None:
    plan = await _get_plan_or_404(session, plan_id)
    if plan.status != "draft":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể xóa kế hoạch ở trạng thái 'Dự thảo'",
        )
    await session.delete(plan)


async def approve_plan(session: AsyncSession, plan_id: int) -> TrainingPlan:
    plan = await _get_plan_or_404(session, plan_id)
    if plan.status != "draft":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể phê duyệt kế hoạch ở trạng thái 'Dự thảo'",
        )
    plan.status = "approved"
    plan.updated_at = _utcnow()
    session.add(plan)
    await session.flush()
    return plan


async def cancel_plan(session: AsyncSession, plan_id: int) -> TrainingPlan:
    plan = await _get_plan_or_404(session, plan_id)
    if plan.status not in ("draft", "approved"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Không thể hủy kế hoạch đã hủy",
        )
    plan.status = "cancelled"
    plan.updated_at = _utcnow()
    session.add(plan)
    await session.flush()
    return plan


async def list_plan_courses(session: AsyncSession, plan_id: int) -> List[PlanCourseRead]:
    stmt = (
        select(TrainingPlanCourse, TrainingCourse)
        .join(TrainingCourse, TrainingCourse.id == TrainingPlanCourse.course_id)
        .where(TrainingPlanCourse.plan_id == plan_id)
        .order_by(TrainingPlanCourse.id)
    )
    rows = (await session.execute(stmt)).all()
    return [_build_plan_course_read(pc, course) for pc, course in rows]


async def add_course_to_plan(
    session: AsyncSession,
    plan_id: int,
    data: PlanCourseCreate,
) -> TrainingPlanCourse:
    plan = await _get_plan_or_404(session, plan_id)
    if plan.status == "cancelled":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Không thể thêm khóa học vào kế hoạch đã hủy",
        )

    course = await session.get(TrainingCourse, data.course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khóa học")

    # Check uniqueness
    existing = (
        await session.execute(
            select(TrainingPlanCourse).where(
                TrainingPlanCourse.plan_id == plan_id,
                TrainingPlanCourse.course_id == data.course_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Khóa học đã có trong kế hoạch này",
        )

    pc = TrainingPlanCourse(
        plan_id=plan_id,
        course_id=data.course_id,
        target_count=data.target_count,
        scheduled_date=data.scheduled_date,
        note=data.note,
        created_at=_utcnow(),
    )
    session.add(pc)
    await session.flush()
    return pc


async def update_plan_course(
    session: AsyncSession,
    plan_id: int,
    course_id: int,
    data: PlanCourseUpdate,
) -> TrainingPlanCourse:
    pc = (
        await session.execute(
            select(TrainingPlanCourse).where(
                TrainingPlanCourse.plan_id == plan_id,
                TrainingPlanCourse.course_id == course_id,
            )
        )
    ).scalar_one_or_none()
    if not pc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy khóa học trong kế hoạch",
        )

    if data.target_count is not None:
        pc.target_count = data.target_count
    if data.scheduled_date is not None:
        pc.scheduled_date = data.scheduled_date
    if data.note is not None:
        pc.note = data.note

    session.add(pc)
    await session.flush()
    return pc


async def remove_course_from_plan(
    session: AsyncSession,
    plan_id: int,
    course_id: int,
) -> None:
    pc = (
        await session.execute(
            select(TrainingPlanCourse).where(
                TrainingPlanCourse.plan_id == plan_id,
                TrainingPlanCourse.course_id == course_id,
            )
        )
    ).scalar_one_or_none()
    if not pc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy khóa học trong kế hoạch",
        )
    await session.delete(pc)
