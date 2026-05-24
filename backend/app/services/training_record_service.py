"""Service theo dõi đào tạo nhân viên (9.2)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import String, func, or_, select
from sqlalchemy import cast as sa_cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department
from app.models.training import EmployeeTrainingRecord, TrainingCourse, TrainingPlan, TrainingPlanCourse
from app.schemas.training import (
    COURSE_TYPES,
    RECORD_RESULTS,
    RECORD_STATUSES,
    BulkAssignRequest,
    BulkAssignResult,
    TrainingRecordCreate,
    TrainingRecordListPage,
    TrainingRecordRead,
    TrainingRecordUpdate,
)
from app.services import employee_code_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_or_404(session: AsyncSession, record_id: int) -> EmployeeTrainingRecord:
    rec = await session.get(EmployeeTrainingRecord, record_id)
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi đào tạo")
    return rec


async def _build_read(session: AsyncSession, rec: EmployeeTrainingRecord) -> TrainingRecordRead:
    emp = await session.get(Employee, rec.employee_id)
    course = await session.get(TrainingCourse, rec.course_id)
    plan: Optional[TrainingPlan] = await session.get(TrainingPlan, rec.plan_id) if rec.plan_id else None
    creator: Optional[User] = await session.get(User, rec.created_by_id) if rec.created_by_id else None

    emp_code = ""
    dept_name: Optional[str] = None
    if emp:
        emp_code = await employee_code_service.build_employee_display_code(session, emp)
        jr = (
            await session.execute(
                select(EmployeeJobRecord)
                .where(EmployeeJobRecord.employee_id == emp.id, EmployeeJobRecord.is_current == True)  # noqa: E712
                .limit(1)
            )
        ).scalar_one_or_none()
        if jr and jr.department_id:
            dept = await session.get(Department, jr.department_id)
            dept_name = dept.name if dept else None

    return TrainingRecordRead(
        id=rec.id,
        employee_id=rec.employee_id,
        employee_code=emp_code,
        employee_name=emp.full_name if emp else "",
        department_name=dept_name,
        course_id=rec.course_id,
        course_name=course.name if course else "",
        course_type=course.course_type if course else "",
        course_type_label=COURSE_TYPES.get(course.course_type, course.course_type) if course else "",
        plan_id=rec.plan_id,
        plan_title=plan.title if plan else None,
        status=rec.status,
        status_label=RECORD_STATUSES.get(rec.status, rec.status),
        result=rec.result,
        result_label=RECORD_RESULTS.get(rec.result, rec.result) if rec.result else None,
        score=rec.score,
        start_date=rec.start_date,
        end_date=rec.end_date,
        note=rec.note,
        created_by_name=getattr(creator, "full_name", None) or (creator.email if creator else None),
        created_at=rec.created_at,
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def get_records(
    session: AsyncSession,
    *,
    employee_id: Optional[int] = None,
    course_id: Optional[int] = None,
    plan_id: Optional[int] = None,
    status: Optional[str] = None,
    result: Optional[str] = None,
    department_id: Optional[int] = None,
    from_date: Optional[object] = None,
    to_date: Optional[object] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> TrainingRecordListPage:
    stmt = (
        select(EmployeeTrainingRecord)
        .join(Employee, Employee.id == EmployeeTrainingRecord.employee_id)
        .outerjoin(
            EmployeeJobRecord,
            (EmployeeJobRecord.employee_id == Employee.id) & (EmployeeJobRecord.is_current == True),  # noqa: E712
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
    )

    if employee_id is not None:
        stmt = stmt.where(EmployeeTrainingRecord.employee_id == employee_id)
    if course_id is not None:
        stmt = stmt.where(EmployeeTrainingRecord.course_id == course_id)
    if plan_id is not None:
        stmt = stmt.where(EmployeeTrainingRecord.plan_id == plan_id)
    if status is not None:
        stmt = stmt.where(EmployeeTrainingRecord.status == status)
    if result is not None:
        if result == "null":
            stmt = stmt.where(EmployeeTrainingRecord.result.is_(None))
        else:
            stmt = stmt.where(EmployeeTrainingRecord.result == result)
    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)
    if from_date is not None:
        stmt = stmt.where(EmployeeTrainingRecord.end_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(EmployeeTrainingRecord.end_date <= to_date)
    if search:
        from app.services.administrative_import_service import normalize_text
        kw = f"%{search.strip()}%"
        norm_kw = f"%{normalize_text(search.strip())}%"
        dept_prefix = func.coalesce(
            func.nullif(func.btrim(Department.display_prefix), ""),
            Department.code,
        )
        generated_code = dept_prefix + func.lpad(
            sa_cast(Employee.employee_seq, String),
            4,
            "0",
        )
        # Also need to join courses for course_name search
        from app.models.training import TrainingCourse as TC
        stmt = stmt.join(TC, TC.id == EmployeeTrainingRecord.course_id)
        stmt = stmt.where(
            or_(
                Employee.full_name.ilike(kw),
                Employee.normalized_name.ilike(norm_kw),
                generated_code.ilike(kw),
                TC.name.ilike(kw),
            )
        )
    else:
        # Still need course join for list query completeness (already joined implicitly)
        pass

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = stmt.order_by(EmployeeTrainingRecord.created_at.desc(), EmployeeTrainingRecord.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()

    items: List[TrainingRecordRead] = []
    for row in rows:
        items.append(await _build_read(session, row))

    return TrainingRecordListPage(items=items, total=total, page=page, page_size=page_size)


async def get_record(session: AsyncSession, record_id: int) -> TrainingRecordRead:
    rec = await _get_or_404(session, record_id)
    return await _build_read(session, rec)


async def create_record(
    session: AsyncSession,
    data: TrainingRecordCreate,
    created_by_id: int,
) -> TrainingRecordRead:
    emp = await session.get(Employee, data.employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    course = await session.get(TrainingCourse, data.course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khóa học")
    if not course.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Khóa học đã ngừng hoạt động")

    if data.plan_id is not None:
        plan = await session.get(TrainingPlan, data.plan_id)
        if not plan:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kế hoạch đào tạo")
        # Validate course belongs to plan
        pc_exists = (
            await session.execute(
                select(TrainingPlanCourse).where(
                    TrainingPlanCourse.plan_id == data.plan_id,
                    TrainingPlanCourse.course_id == data.course_id,
                )
            )
        ).scalar_one_or_none()
        if not pc_exists:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Khóa học không thuộc kế hoạch đào tạo này",
            )

    rec = EmployeeTrainingRecord(
        employee_id=data.employee_id,
        course_id=data.course_id,
        plan_id=data.plan_id,
        status=data.status,
        start_date=data.start_date,
        end_date=data.end_date,
        note=data.note,
        created_by_id=created_by_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(rec)
    await session.flush()
    return await _build_read(session, rec)


async def update_record(
    session: AsyncSession,
    record_id: int,
    data: TrainingRecordUpdate,
) -> TrainingRecordRead:
    rec = await _get_or_404(session, record_id)

    if data.status is not None:
        rec.status = data.status
    if data.result is not None:
        rec.result = data.result
    if data.score is not None:
        rec.score = data.score
    if data.start_date is not None:
        rec.start_date = data.start_date
    if data.end_date is not None:
        rec.end_date = data.end_date
    if data.note is not None:
        rec.note = data.note

    # Re-validate dates after update
    eff_start = rec.start_date
    eff_end = rec.end_date
    if eff_start and eff_end and eff_end < eff_start:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date phải >= start_date",
        )

    rec.updated_at = _utcnow()
    session.add(rec)
    await session.flush()
    return await _build_read(session, rec)


async def delete_record(session: AsyncSession, record_id: int) -> None:
    rec = await _get_or_404(session, record_id)
    await session.delete(rec)


# ── Bulk assign ───────────────────────────────────────────────────────────────


async def bulk_assign(
    session: AsyncSession,
    data: BulkAssignRequest,
    created_by_id: int,
) -> BulkAssignResult:
    plan = await session.get(TrainingPlan, data.plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kế hoạch đào tạo")
    if plan.status == "cancelled":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Không thể gán nhân viên vào kế hoạch đã hủy",
        )

    pc = (
        await session.execute(
            select(TrainingPlanCourse).where(
                TrainingPlanCourse.plan_id == data.plan_id,
                TrainingPlanCourse.course_id == data.course_id,
            )
        )
    ).scalar_one_or_none()
    if not pc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Khóa học không thuộc kế hoạch đào tạo này",
        )

    # Resolve employee IDs — either from explicit list or from departments
    if data.department_ids:
        emp_ids_rows = (
            await session.execute(
                select(EmployeeJobRecord.employee_id).where(
                    EmployeeJobRecord.department_id.in_(data.department_ids),
                    EmployeeJobRecord.is_current == True,  # noqa: E712
                )
            )
        ).scalars().all()
        target_ids = list(emp_ids_rows)
    else:
        target_ids = data.employee_ids

    if not target_ids:
        return BulkAssignResult(created=0, skipped=0)

    # Fetch existing records for this (course, plan) to detect duplicates
    existing_rows = (
        await session.execute(
            select(EmployeeTrainingRecord.employee_id).where(
                EmployeeTrainingRecord.course_id == data.course_id,
                EmployeeTrainingRecord.plan_id == data.plan_id,
                EmployeeTrainingRecord.employee_id.in_(target_ids),
            )
        )
    ).scalars().all()
    existing_set = set(existing_rows)

    created = 0
    skipped = 0
    now = _utcnow()

    for emp_id in target_ids:
        if emp_id in existing_set:
            skipped += 1
            continue
        emp = await session.get(Employee, emp_id)
        if not emp:
            skipped += 1
            continue
        rec = EmployeeTrainingRecord(
            employee_id=emp_id,
            course_id=data.course_id,
            plan_id=data.plan_id,
            status="chua_bat_dau",
            note=data.note,
            created_by_id=created_by_id,
            created_at=now,
            updated_at=now,
        )
        session.add(rec)
        created += 1

    await session.flush()
    return BulkAssignResult(created=created, skipped=skipped)


# ── Training Passport ─────────────────────────────────────────────────────────


async def get_training_passport(
    session: AsyncSession,
    employee_id: int,
) -> List[TrainingRecordRead]:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    stmt = (
        select(EmployeeTrainingRecord)
        .where(EmployeeTrainingRecord.employee_id == employee_id)
        .order_by(
            EmployeeTrainingRecord.end_date.desc().nulls_last(),
            EmployeeTrainingRecord.created_at.desc(),
        )
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [await _build_read(session, r) for r in rows]
