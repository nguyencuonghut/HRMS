"""Service danh mục khóa học đào tạo (9.1 Slice 1)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import TrainingCourse, TrainingPlanCourse
from app.schemas.training import (
    COURSE_TYPES,
    CourseCreate,
    CourseListPage,
    CourseRead,
    CourseUpdate,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_course_or_404(session: AsyncSession, course_id: int) -> TrainingCourse:
    course = await session.get(TrainingCourse, course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khóa học")
    return course


def _build_read(course: TrainingCourse) -> CourseRead:
    return CourseRead(
        id=course.id,
        code=course.code,
        name=course.name,
        course_type=course.course_type,
        course_type_label=COURSE_TYPES.get(course.course_type, course.course_type),
        duration_hours=course.duration_hours,
        organizer=course.organizer,
        description=course.description,
        cost_per_person=course.cost_per_person,
        is_mandatory=course.is_mandatory,
        is_active=course.is_active,
        created_at=course.created_at,
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def list_courses(
    session: AsyncSession,
    *,
    search: Optional[str] = None,
    course_type: Optional[str] = None,
    is_mandatory: Optional[bool] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> CourseListPage:
    stmt = select(TrainingCourse)

    if search:
        kw = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                TrainingCourse.code.ilike(kw),
                TrainingCourse.name.ilike(kw),
                TrainingCourse.organizer.ilike(kw),
            )
        )
    if course_type is not None:
        stmt = stmt.where(TrainingCourse.course_type == course_type)
    if is_mandatory is not None:
        stmt = stmt.where(TrainingCourse.is_mandatory == is_mandatory)
    if is_active is not None:
        stmt = stmt.where(TrainingCourse.is_active == is_active)

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = stmt.order_by(TrainingCourse.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()

    return CourseListPage(
        items=[_build_read(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_course(session: AsyncSession, course_id: int) -> CourseRead:
    course = await _get_course_or_404(session, course_id)
    return _build_read(course)


async def create_course(session: AsyncSession, data: CourseCreate) -> TrainingCourse:
    # Check code uniqueness
    existing = (
        await session.execute(select(TrainingCourse).where(TrainingCourse.code == data.code))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Mã khóa học '{data.code}' đã tồn tại")

    course = TrainingCourse(
        code=data.code,
        name=data.name,
        course_type=data.course_type,
        duration_hours=data.duration_hours,
        organizer=data.organizer,
        description=data.description,
        cost_per_person=data.cost_per_person,
        is_mandatory=data.is_mandatory,
        is_active=True,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(course)
    await session.flush()
    return course


async def update_course(
    session: AsyncSession,
    course_id: int,
    data: CourseUpdate,
) -> TrainingCourse:
    course = await _get_course_or_404(session, course_id)

    if data.code is not None and data.code != course.code:
        existing = (
            await session.execute(select(TrainingCourse).where(TrainingCourse.code == data.code))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Mã khóa học '{data.code}' đã tồn tại")
        course.code = data.code

    if data.name is not None:
        course.name = data.name
    if data.course_type is not None:
        course.course_type = data.course_type
    if data.duration_hours is not None:
        course.duration_hours = data.duration_hours
    if data.organizer is not None:
        course.organizer = data.organizer
    if data.description is not None:
        course.description = data.description
    if data.cost_per_person is not None:
        course.cost_per_person = data.cost_per_person
    if data.is_mandatory is not None:
        course.is_mandatory = data.is_mandatory
    if data.is_active is not None:
        course.is_active = data.is_active

    course.updated_at = _utcnow()
    session.add(course)
    await session.flush()
    return course


async def delete_course(session: AsyncSession, course_id: int) -> str:
    """Delete or soft-deactivate a course. Returns 'hard' or 'soft'."""
    course = await _get_course_or_404(session, course_id)

    # Check if referenced in any plan
    ref_count = (
        await session.execute(
            select(func.count()).where(TrainingPlanCourse.course_id == course_id)
        )
    ).scalar_one()

    if ref_count > 0:
        # Soft delete: deactivate
        course.is_active = False
        course.updated_at = _utcnow()
        session.add(course)
        await session.flush()
        return "soft"
    else:
        await session.delete(course)
        return "hard"
