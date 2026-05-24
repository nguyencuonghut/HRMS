"""Service báo cáo hiệu suất KPI (10.4)."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department
from app.models.performance import EmployeeKpiMonthly, EmployeeYearlyReview
from app.schemas.performance import (
    DepartmentKpiStat,
    MonthlyKpiTrend,
    MonthlyPoint,
    RatingCount,
    RatingDistributionReport,
)
from app.services.yearly_review_service import RATING_LABELS

_ALL_RATINGS = ["xuat_sac", "tot", "dat", "can_cai_thien"]


def _round1(v: float) -> float:
    return float(Decimal(str(v)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


async def get_rating_distribution(
    session: AsyncSession,
    year: int,
) -> RatingDistributionReport:
    rows = (
        await session.execute(
            select(EmployeeYearlyReview.rating, func.count().label("cnt"))
            .where(EmployeeYearlyReview.year == year)
            .group_by(EmployeeYearlyReview.rating)
        )
    ).all()

    counts: dict[str, int] = {r: 0 for r in _ALL_RATINGS}
    for rating, cnt in rows:
        if rating in counts:
            counts[rating] = cnt

    total_reviewed = sum(counts.values())

    total_emp_row = (
        await session.execute(
            select(func.count()).where(Employee.is_active == True)  # noqa: E712
        )
    ).scalar_one()
    total_employees = total_emp_row or 0

    coverage_rate = _round1(total_reviewed / total_employees * 100) if total_employees > 0 else 0.0

    distribution: List[RatingCount] = []
    for rating in _ALL_RATINGS:
        cnt = counts[rating]
        pct = _round1(cnt / total_reviewed * 100) if total_reviewed > 0 else 0.0
        distribution.append(RatingCount(
            rating=rating,
            rating_label=RATING_LABELS.get(rating, rating),
            count=cnt,
            percentage=pct,
        ))

    return RatingDistributionReport(
        year=year,
        total_reviewed=total_reviewed,
        total_employees=total_employees,
        coverage_rate=coverage_rate,
        distribution=distribution,
    )


async def get_department_kpi_stats(
    session: AsyncSession,
    year: int,
    month: Optional[int] = None,
    department_id: Optional[int] = None,
) -> List[DepartmentKpiStat]:
    stmt = (
        select(
            EmployeeJobRecord.department_id,
            Department.name.label("dept_name"),
            func.count(EmployeeKpiMonthly.employee_id.distinct()).label("emp_count"),
            func.avg(EmployeeKpiMonthly.score).label("avg_score"),
            func.min(EmployeeKpiMonthly.score).label("min_score"),
            func.max(EmployeeKpiMonthly.score).label("max_score"),
            func.count().label("months_count"),
        )
        .join(Employee, Employee.id == EmployeeKpiMonthly.employee_id)
        .join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
        .where(EmployeeKpiMonthly.year == year)
    )

    if month is not None:
        stmt = stmt.where(EmployeeKpiMonthly.month == month)
    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)

    stmt = stmt.group_by(EmployeeJobRecord.department_id, Department.name)
    stmt = stmt.order_by(func.avg(EmployeeKpiMonthly.score).desc().nullslast())

    rows = (await session.execute(stmt)).all()

    result: List[DepartmentKpiStat] = []
    for row in rows:
        result.append(DepartmentKpiStat(
            department_id=row.department_id,
            department_name=row.dept_name,
            employee_count=row.emp_count,
            avg_score=row.avg_score,
            min_score=row.min_score,
            max_score=row.max_score,
            months_data_count=row.months_count,
        ))
    return result


async def get_monthly_trend(
    session: AsyncSession,
    year: int,
    department_id: Optional[int] = None,
) -> MonthlyKpiTrend:
    dept_name: Optional[str] = None
    if department_id is not None:
        dept = await session.get(Department, department_id)
        dept_name = dept.name if dept else None

    stmt = (
        select(
            EmployeeKpiMonthly.month,
            func.avg(EmployeeKpiMonthly.score).label("avg_score"),
            func.count(EmployeeKpiMonthly.employee_id.distinct()).label("emp_count"),
        )
        .join(Employee, Employee.id == EmployeeKpiMonthly.employee_id)
        .join(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            ),
        )
        .where(EmployeeKpiMonthly.year == year)
    )

    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)

    stmt = stmt.group_by(EmployeeKpiMonthly.month).order_by(EmployeeKpiMonthly.month)
    rows = (await session.execute(stmt)).all()

    month_map: dict[int, tuple] = {r.month: (r.avg_score, r.emp_count) for r in rows}

    points: List[MonthlyPoint] = []
    for m in range(1, 13):
        if m in month_map:
            avg, cnt = month_map[m]
            points.append(MonthlyPoint(month=m, avg_score=avg, employee_count=cnt))
        else:
            points.append(MonthlyPoint(month=m, avg_score=None, employee_count=0))

    return MonthlyKpiTrend(
        year=year,
        department_id=department_id,
        department_name=dept_name,
        points=points,
    )
