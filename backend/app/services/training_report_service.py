"""Service báo cáo đào tạo (9.4)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department
from app.models.training import EmployeeTrainingRecord, TrainingCourse
from app.schemas.training import COURSE_TYPES
from app.schemas.training_report import (
    CourseCompletionStat,
    DepartmentTrainingStat,
    IncompleteMandatoryEmployee,
    TrainingReportSummary,
)
from app.services import employee_code_service


async def get_training_report_summary(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    department_id: Optional[int] = None,
    course_id: Optional[int] = None,
) -> TrainingReportSummary:
    # Base query: records trong kỳ
    # Record thuộc kỳ khi: end_date BETWEEN from_date AND to_date
    #   hoặc (end_date IS NULL AND start_date BETWEEN from_date AND to_date)
    from sqlalchemy import and_, or_

    stmt = (
        select(EmployeeTrainingRecord)
        .join(Employee, Employee.id == EmployeeTrainingRecord.employee_id)
        .outerjoin(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
        .where(
            or_(
                and_(
                    EmployeeTrainingRecord.end_date >= from_date,
                    EmployeeTrainingRecord.end_date <= to_date,
                ),
                and_(
                    EmployeeTrainingRecord.end_date.is_(None),
                    EmployeeTrainingRecord.start_date >= from_date,
                    EmployeeTrainingRecord.start_date <= to_date,
                ),
            )
        )
    )

    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)
    if course_id is not None:
        stmt = stmt.where(EmployeeTrainingRecord.course_id == course_id)

    rows = (await session.execute(stmt)).scalars().all()

    # Fetch all courses needed in one shot
    course_ids_needed = {r.course_id for r in rows}
    courses_map: Dict[int, TrainingCourse] = {}
    for cid in course_ids_needed:
        c = await session.get(TrainingCourse, cid)
        if c:
            courses_map[cid] = c

    # Fetch department names for rows via EmployeeJobRecord
    dept_name_map: Dict[int, Optional[str]] = {}  # employee_id → dept_name
    dept_id_map: Dict[int, Optional[int]] = {}    # employee_id → dept_id
    for r in rows:
        if r.employee_id not in dept_name_map:
            jr = (
                await session.execute(
                    select(EmployeeJobRecord)
                    .where(
                        EmployeeJobRecord.employee_id == r.employee_id,
                        EmployeeJobRecord.is_current == True,  # noqa: E712
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if jr and jr.department_id:
                dept = await session.get(Department, jr.department_id)
                dept_name_map[r.employee_id] = dept.name if dept else None
                dept_id_map[r.employee_id] = jr.department_id
            else:
                dept_name_map[r.employee_id] = None
                dept_id_map[r.employee_id] = None

    # Empty period
    if not rows:
        dept_name: Optional[str] = None
        course_name: Optional[str] = None
        if department_id is not None:
            dept = await session.get(Department, department_id)
            dept_name = dept.name if dept else None
        if course_id is not None:
            c = await session.get(TrainingCourse, course_id)
            course_name = c.name if c else None
        return TrainingReportSummary(
            from_date=from_date,
            to_date=to_date,
            department_id=department_id,
            department_name=dept_name,
            course_id=course_id,
            course_name=course_name,
            total_records=0,
            total_completed=0,
            total_not_completed=0,
            total_in_progress=0,
            total_cost=Decimal("0"),
            avg_completion_rate=0.0,
            by_course=[],
            by_department=[],
        )

    # Group by course
    course_groups: Dict[int, List[EmployeeTrainingRecord]] = defaultdict(list)
    for r in rows:
        course_groups[r.course_id].append(r)

    by_course: List[CourseCompletionStat] = []
    for cid, recs in course_groups.items():
        c = courses_map.get(cid)
        total = len(recs)
        completed = sum(1 for r in recs if r.status == "hoan_thanh")
        not_completed = sum(1 for r in recs if r.status in ("khong_hoan_thanh", "vang_mat"))
        in_progress = total - completed - not_completed
        rate = round(completed / total * 100, 1) if total > 0 else 0.0
        by_course.append(CourseCompletionStat(
            course_id=cid,
            course_name=c.name if c else "",
            course_type_label=COURSE_TYPES.get(c.course_type, c.course_type) if c else "",
            total_assigned=total,
            completed=completed,
            not_completed=not_completed,
            in_progress=in_progress,
            completion_rate=rate,
        ))
    by_course.sort(key=lambda x: x.completion_rate, reverse=True)

    # Group by department
    dept_groups: Dict[Optional[int], List[EmployeeTrainingRecord]] = defaultdict(list)
    for r in rows:
        dept_groups[dept_id_map.get(r.employee_id)].append(r)

    by_department: List[DepartmentTrainingStat] = []
    for did, recs in dept_groups.items():
        total = len(recs)
        completed_recs = [r for r in recs if r.status == "hoan_thanh"]
        completed = len(completed_recs)
        rate = round(completed / total * 100, 1) if total > 0 else 0.0

        # total_cost: sum of cost_per_person for completed records
        dept_cost: Optional[Decimal] = None
        for r in completed_recs:
            c = courses_map.get(r.course_id)
            if c and c.cost_per_person is not None:
                dept_cost = (dept_cost or Decimal("0")) + c.cost_per_person

        # Resolve dept name
        dn: Optional[str] = None
        if did is not None:
            dept = await session.get(Department, did)
            dn = dept.name if dept else None

        by_department.append(DepartmentTrainingStat(
            department_id=did,
            department_name=dn,
            total_records=total,
            completed=completed,
            completion_rate=rate,
            total_cost=dept_cost,
        ))
    by_department.sort(key=lambda x: x.completion_rate, reverse=True)

    # Totals
    total_records = len(rows)
    total_completed = sum(1 for r in rows if r.status == "hoan_thanh")
    total_not_completed = sum(1 for r in rows if r.status in ("khong_hoan_thanh", "vang_mat"))
    total_in_progress = total_records - total_completed - total_not_completed

    total_cost = Decimal("0")
    for r in rows:
        if r.status == "hoan_thanh":
            c = courses_map.get(r.course_id)
            if c and c.cost_per_person is not None:
                total_cost += c.cost_per_person

    avg_completion_rate = 0.0
    if by_course:
        avg_completion_rate = round(sum(s.completion_rate for s in by_course) / len(by_course), 1)

    # Filter labels
    dept_name = None
    course_name = None
    if department_id is not None:
        dept = await session.get(Department, department_id)
        dept_name = dept.name if dept else None
    if course_id is not None:
        c = courses_map.get(course_id)
        course_name = c.name if c else None

    return TrainingReportSummary(
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
        department_name=dept_name,
        course_id=course_id,
        course_name=course_name,
        total_records=total_records,
        total_completed=total_completed,
        total_not_completed=total_not_completed,
        total_in_progress=total_in_progress,
        total_cost=total_cost,
        avg_completion_rate=avg_completion_rate,
        by_course=by_course,
        by_department=by_department,
    )


async def get_incomplete_mandatory_employees(
    session: AsyncSession,
    *,
    department_id: Optional[int] = None,
) -> List[IncompleteMandatoryEmployee]:
    # All mandatory courses
    mandatory_stmt = select(TrainingCourse).where(
        TrainingCourse.is_mandatory == True,  # noqa: E712
        TrainingCourse.is_active == True,     # noqa: E712
    )
    mandatory_courses: List[Tuple[int, str]] = [
        (c.id, c.name)
        for c in (await session.execute(mandatory_stmt)).scalars().all()
    ]
    if not mandatory_courses:
        return []

    mandatory_ids = [c[0] for c in mandatory_courses]

    # All active employees
    emp_stmt = select(Employee).where(Employee.status == "active")
    if department_id is not None:
        emp_stmt = (
            emp_stmt
            .join(EmployeeJobRecord, and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ))
            .where(EmployeeJobRecord.department_id == department_id)
        )
    employees = (await session.execute(emp_stmt)).scalars().all()
    if not employees:
        return []

    # 1 query to get all completed mandatory records across all employees
    completed_stmt = select(
        EmployeeTrainingRecord.employee_id,
        EmployeeTrainingRecord.course_id,
    ).where(
        EmployeeTrainingRecord.course_id.in_(mandatory_ids),
        EmployeeTrainingRecord.status == "hoan_thanh",
        EmployeeTrainingRecord.employee_id.in_([e.id for e in employees]),
    )
    completed_rows = (await session.execute(completed_stmt)).all()
    completed_map: Dict[int, Set[int]] = defaultdict(set)
    for emp_id, cid in completed_rows:
        completed_map[emp_id].add(cid)

    # Build employee code map and department map
    result: List[IncompleteMandatoryEmployee] = []
    for emp in employees:
        completed_ids = completed_map.get(emp.id, set())
        incomplete = [(cid, cname) for cid, cname in mandatory_courses if cid not in completed_ids]
        if not incomplete:
            continue

        emp_code = await employee_code_service.build_employee_display_code(session, emp)

        # Dept name
        jr = (
            await session.execute(
                select(EmployeeJobRecord)
                .where(
                    EmployeeJobRecord.employee_id == emp.id,
                    EmployeeJobRecord.is_current == True,  # noqa: E712
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        dept_name: Optional[str] = None
        if jr and jr.department_id:
            dept = await session.get(Department, jr.department_id)
            dept_name = dept.name if dept else None

        result.append(IncompleteMandatoryEmployee(
            employee_id=emp.id,
            employee_code=emp_code,
            employee_name=emp.full_name,
            department_name=dept_name,
            incomplete_courses=[cname for _, cname in incomplete],
            incomplete_count=len(incomplete),
        ))

    result.sort(key=lambda x: (-x.incomplete_count, x.employee_code))
    return result
