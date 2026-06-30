"""Service cho dashboard tổng quan nhân sự (11.1)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Sequence

import sqlalchemy as sa
from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_education import EmployeeEducationHistory
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department
from app.models.catalog import EducationLevel
from app.schemas.dashboard import (
    DashboardSummary,
    GenderItem,
    HeadcountByDeptItem,
    MonthlyTrendItem,
    MonthlyTrendReport,
    StructureGroupItem,
    StructureReport,
)

_GENDER_LABELS = {
    "male": "Nam",
    "female": "Nữ",
    "other": "Khác",
}

_AGE_GROUP_ORDER = ["Dưới 25", "25-34", "35-44", "45-54", "55 trở lên"]
_TENURE_GROUP_ORDER = ["Dưới 1 năm", "1-2 năm", "3-5 năm", "6-10 năm", "Trên 10 năm"]


def _round1(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _current_period(year: Optional[int], month: Optional[int]) -> tuple[int, Optional[int]]:
    today = date.today()
    return year or today.year, month


async def _department_scope_ids(
    session: AsyncSession,
    department_id: Optional[int],
) -> Optional[set[int]]:
    if department_id is None:
        return None
    rows = await session.execute(
        sa.text(
            """
            WITH RECURSIVE subtree AS (
                SELECT id
                FROM departments
                WHERE id = :department_id AND is_active = TRUE
                UNION ALL
                SELECT d.id
                FROM departments d
                JOIN subtree s ON d.parent_id = s.id
                WHERE d.is_active = TRUE
            )
            SELECT id FROM subtree
            """
        ),
        {"department_id": department_id},
    )
    return {row[0] for row in rows.fetchall()}


async def _effective_department_scope_ids(
    session: AsyncSession,
    *,
    department_id: Optional[int],
    allowed_department_ids: Optional[Sequence[int]],
) -> Optional[set[int]]:
    requested_scope_ids = await _department_scope_ids(session, department_id)
    if allowed_department_ids is None:
        return requested_scope_ids

    allowed_scope_ids = {int(department_id) for department_id in allowed_department_ids}
    if department_id is not None and department_id not in allowed_scope_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập dữ liệu phòng ban này",
        )

    if requested_scope_ids is None:
        return allowed_scope_ids
    return requested_scope_ids & allowed_scope_ids


def _active_employee_filters(department_ids: Optional[Sequence[int]]) -> list[sa.ColumnElement[bool]]:
    filters: list[sa.ColumnElement[bool]] = [
        Employee.is_active == True,  # noqa: E712
        Employee.status != "resigned",
        EmployeeJobRecord.is_current == True,  # noqa: E712
    ]
    if department_ids is not None:
        if not department_ids:
            filters.append(sa.false())
        else:
            filters.append(EmployeeJobRecord.department_id.in_(department_ids))
    return filters


async def get_summary(
    session: AsyncSession,
    *,
    year: Optional[int] = None,
    month: Optional[int] = None,
    department_id: Optional[int] = None,
    allowed_department_ids: Optional[Sequence[int]] = None,
) -> DashboardSummary:
    year, month = _current_period(year, month)
    period_start = date(year, month, 1) if month is not None else date(year, 1, 1)
    department_ids = await _effective_department_scope_ids(
        session,
        department_id=department_id,
        allowed_department_ids=allowed_department_ids,
    )

    total_stmt = (
        select(func.count(Employee.id.distinct()))
        .join(EmployeeJobRecord, EmployeeJobRecord.employee_id == Employee.id)
        .where(*_active_employee_filters(department_ids))
    )
    total_headcount = (await session.execute(total_stmt)).scalar_one() or 0

    new_hires_stmt = (
        select(func.count(Employee.id))
        .join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
        .where(
            sa.extract("year", Employee.start_date) == year,
            Employee.is_active == True,  # noqa: E712
        )
    )
    if month is not None:
        new_hires_stmt = new_hires_stmt.where(sa.extract("month", Employee.start_date) == month)
    if department_ids is not None:
        if not department_ids:
            new_hires = 0
        else:
            new_hires_stmt = new_hires_stmt.where(EmployeeJobRecord.department_id.in_(department_ids))
            new_hires = (await session.execute(new_hires_stmt)).scalar_one() or 0
    else:
        new_hires = (await session.execute(new_hires_stmt)).scalar_one() or 0

    resigned_stmt = (
        select(func.count(Employee.id))
        .join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
        .where(
            Employee.status == "resigned",
            Employee.resigned_date.is_not(None),
            sa.extract("year", Employee.resigned_date) == year,
        )
    )
    if month is not None:
        resigned_stmt = resigned_stmt.where(sa.extract("month", Employee.resigned_date) == month)
    if department_ids is not None:
        if not department_ids:
            resigned_count = 0
        else:
            resigned_stmt = resigned_stmt.where(EmployeeJobRecord.department_id.in_(department_ids))
            resigned_count = (await session.execute(resigned_stmt)).scalar_one() or 0
    else:
        resigned_count = (await session.execute(resigned_stmt)).scalar_one() or 0

    headcount_start_stmt = (
        select(func.count(Employee.id))
        .join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
        .where(
            Employee.start_date < period_start,
            sa.or_(
                Employee.resigned_date.is_(None),
                Employee.resigned_date >= period_start,
            ),
        )
    )
    if department_ids is not None:
        if not department_ids:
            headcount_start = 0
        else:
            headcount_start_stmt = headcount_start_stmt.where(EmployeeJobRecord.department_id.in_(department_ids))
            headcount_start = (await session.execute(headcount_start_stmt)).scalar_one() or 0
    else:
        headcount_start = (await session.execute(headcount_start_stmt)).scalar_one() or 0

    turnover_rate = _round1(resigned_count / headcount_start * 100) if headcount_start > 0 else 0.0

    return DashboardSummary(
        total_headcount=total_headcount,
        new_hires_this_month=new_hires,
        resigned_this_month=resigned_count,
        headcount_start_of_month=headcount_start,
        turnover_rate=turnover_rate,
        as_of_date=date.today(),
    )


async def get_headcount_by_dept(
    session: AsyncSession,
    *,
    department_id: Optional[int] = None,
    allowed_department_ids: Optional[Sequence[int]] = None,
) -> list[HeadcountByDeptItem]:
    department_ids = await _effective_department_scope_ids(
        session,
        department_id=department_id,
        allowed_department_ids=allowed_department_ids,
    )
    stmt = (
        select(
            Department.id,
            Department.name,
            Department.parent_id,
            Department.order_no,
            func.count(Employee.id).label("headcount"),
        )
        .select_from(Department)
        .outerjoin(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.department_id == Department.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
        .outerjoin(
            Employee,
            and_(
                Employee.id == EmployeeJobRecord.employee_id,
                Employee.is_active == True,  # noqa: E712
                Employee.status != "resigned",
            ),
        )
        .where(Department.is_active == True)  # noqa: E712
        .group_by(Department.id, Department.name, Department.parent_id, Department.order_no)
    )
    if department_ids is not None:
        if not department_ids:
            return []
        stmt = stmt.where(Department.id.in_(department_ids))

    rows = (await session.execute(stmt)).all()
    if not rows:
        return []

    departments = {
        row.id: {
            "id": row.id,
            "name": row.name,
            "parent_id": row.parent_id,
            "order_no": row.order_no or 0,
            "direct_headcount": row.headcount or 0,
        }
        for row in rows
    }
    children_map: dict[int, list[int]] = {dept_id: [] for dept_id in departments}
    for dept in departments.values():
        parent_id = dept["parent_id"]
        if parent_id in children_map:
            children_map[parent_id].append(dept["id"])

    for child_ids in children_map.values():
        child_ids.sort(key=lambda child_id: (departments[child_id]["order_no"], departments[child_id]["name"]))

    totals_cache: dict[int, int] = {}

    def total_headcount(dept_id: int) -> int:
        if dept_id in totals_cache:
            return totals_cache[dept_id]
        total = departments[dept_id]["direct_headcount"] + sum(
            total_headcount(child_id) for child_id in children_map.get(dept_id, [])
        )
        totals_cache[dept_id] = total
        return total

    if department_id is not None:
        if department_id not in departments:
            return []
        scoped_ids = children_map.get(department_id, []) or [department_id]
    else:
        scoped_ids = [
            dept_id
            for dept_id, dept in departments.items()
            if dept["parent_id"] is None or dept["parent_id"] not in departments
        ]
        scoped_ids.sort(key=lambda dept_id: (departments[dept_id]["order_no"], departments[dept_id]["name"]))

    items = [
        HeadcountByDeptItem(
            department_id=dept_id,
            department_name=departments[dept_id]["name"],
            parent_department_id=departments[dept_id]["parent_id"],
            headcount=total_headcount(dept_id),
            direct_headcount=departments[dept_id]["direct_headcount"],
            child_department_count=len(children_map.get(dept_id, [])),
        )
        for dept_id in scoped_ids
    ]
    return sorted(items, key=lambda item: (-item.headcount, item.department_name))


async def get_monthly_trend(
    session: AsyncSession,
    *,
    year: Optional[int] = None,
    department_id: Optional[int] = None,
    allowed_department_ids: Optional[Sequence[int]] = None,
) -> MonthlyTrendReport:
    report_year = year or date.today().year
    department_ids = await _effective_department_scope_ids(
        session,
        department_id=department_id,
        allowed_department_ids=allowed_department_ids,
    )

    hires_stmt = (
        select(
            sa.extract("month", Employee.start_date).label("month"),
            func.count(Employee.id).label("count"),
        )
        .join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
        .where(sa.extract("year", Employee.start_date) == report_year)
        .group_by(sa.extract("month", Employee.start_date))
    )
    if department_ids is not None:
        if not department_ids:
            hire_rows = []
        else:
            hires_stmt = hires_stmt.where(EmployeeJobRecord.department_id.in_(department_ids))
            hire_rows = (await session.execute(hires_stmt)).all()
    else:
        hire_rows = (await session.execute(hires_stmt)).all()

    resigned_stmt = (
        select(
            sa.extract("month", Employee.resigned_date).label("month"),
            func.count(Employee.id).label("count"),
        )
        .join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
        .where(
            Employee.status == "resigned",
            Employee.resigned_date.is_not(None),
            sa.extract("year", Employee.resigned_date) == report_year,
        )
        .group_by(sa.extract("month", Employee.resigned_date))
    )
    if department_ids is not None:
        if not department_ids:
            resigned_rows = []
        else:
            resigned_stmt = resigned_stmt.where(EmployeeJobRecord.department_id.in_(department_ids))
            resigned_rows = (await session.execute(resigned_stmt)).all()
    else:
        resigned_rows = (await session.execute(resigned_stmt)).all()

    hires_map = {int(row.month): row.count for row in hire_rows}
    resigned_map = {int(row.month): row.count for row in resigned_rows}

    monthly = []
    for month in range(1, 13):
        new_hires = hires_map.get(month, 0)
        resigned_count = resigned_map.get(month, 0)
        monthly.append(MonthlyTrendItem(
            month=month,
            new_hires=new_hires,
            resigned_count=resigned_count,
            net_change=new_hires - resigned_count,
        ))

    return MonthlyTrendReport(
        year=report_year,
        department_id=department_id,
        monthly=monthly,
    )


async def get_structure(
    session: AsyncSession,
    *,
    department_id: Optional[int] = None,
    allowed_department_ids: Optional[Sequence[int]] = None,
) -> StructureReport:
    department_ids = await _effective_department_scope_ids(
        session,
        department_id=department_id,
        allowed_department_ids=allowed_department_ids,
    )
    base_filters = _active_employee_filters(department_ids)

    gender_stmt = (
        select(
            Employee.gender,
            func.count(Employee.id).label("count"),
        )
        .join(EmployeeJobRecord, EmployeeJobRecord.employee_id == Employee.id)
        .where(*base_filters)
        .group_by(Employee.gender)
    )
    gender_rows = (await session.execute(gender_stmt)).all()
    total_gender = sum(row.count for row in gender_rows)
    gender = [
        GenderItem(
            label=_GENDER_LABELS.get(row.gender, "Khác"),
            count=row.count,
            percentage=_round1(row.count / total_gender * 100) if total_gender > 0 else 0.0,
        )
        for row in gender_rows
    ]

    age_group_expr = case(
        (func.date_part("year", func.age(func.current_date(), Employee.date_of_birth)) < 25, "Dưới 25"),
        (func.date_part("year", func.age(func.current_date(), Employee.date_of_birth)).between(25, 34), "25-34"),
        (func.date_part("year", func.age(func.current_date(), Employee.date_of_birth)).between(35, 44), "35-44"),
        (func.date_part("year", func.age(func.current_date(), Employee.date_of_birth)).between(45, 54), "45-54"),
        else_="55 trở lên",
    )
    age_stmt = (
        select(age_group_expr.label("label"), func.count(Employee.id).label("count"))
        .join(EmployeeJobRecord, EmployeeJobRecord.employee_id == Employee.id)
        .where(*base_filters)
        .group_by(age_group_expr)
    )
    age_rows = (await session.execute(age_stmt)).all()
    age_map = {row.label: row.count for row in age_rows}
    age_group = [
        StructureGroupItem(label=label, count=age_map[label])
        for label in _AGE_GROUP_ORDER
        if label in age_map
    ]

    education_stmt = (
        select(
            EducationLevel.name.label("education_level_name"),
            func.count(Employee.id.distinct()).label("count"),
        )
        .join(EmployeeJobRecord, EmployeeJobRecord.employee_id == Employee.id)
        .outerjoin(
            EmployeeEducationHistory,
            and_(
                EmployeeEducationHistory.employee_id == Employee.id,
                EmployeeEducationHistory.is_main_education == True,  # noqa: E712
            ),
        )
        .outerjoin(EducationLevel, EducationLevel.id == EmployeeEducationHistory.education_level_id)
        .where(*base_filters)
        .group_by(EducationLevel.name)
        .order_by(func.count(Employee.id.distinct()).desc())
    )
    education_rows = (await session.execute(education_stmt)).all()
    education_level = [
        StructureGroupItem(label=row.education_level_name or "Chưa cập nhật", count=row.count)
        for row in education_rows
    ]

    tenure_group_expr = case(
        (func.date_part("year", func.age(func.current_date(), Employee.start_date)) < 1, "Dưới 1 năm"),
        (func.date_part("year", func.age(func.current_date(), Employee.start_date)).between(1, 2), "1-2 năm"),
        (func.date_part("year", func.age(func.current_date(), Employee.start_date)).between(3, 5), "3-5 năm"),
        (func.date_part("year", func.age(func.current_date(), Employee.start_date)).between(6, 10), "6-10 năm"),
        else_="Trên 10 năm",
    )
    tenure_stmt = (
        select(tenure_group_expr.label("label"), func.count(Employee.id).label("count"))
        .join(EmployeeJobRecord, EmployeeJobRecord.employee_id == Employee.id)
        .where(*base_filters)
        .group_by(tenure_group_expr)
    )
    tenure_rows = (await session.execute(tenure_stmt)).all()
    tenure_map = {row.label: row.count for row in tenure_rows}
    tenure_group = [
        StructureGroupItem(label=label, count=tenure_map[label])
        for label in _TENURE_GROUP_ORDER
        if label in tenure_map
    ]

    return StructureReport(
        gender=gender,
        age_group=age_group,
        education_level=education_level,
        tenure_group=tenure_group,
    )
