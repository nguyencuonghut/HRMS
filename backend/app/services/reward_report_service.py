"""Service báo cáo khen thưởng – kỷ luật (8.3)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discipline import EmployeeDiscipline
from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department
from app.models.reward import EmployeeReward, RewardType
from app.schemas.discipline import DISCIPLINE_FORMS
from app.schemas.reward_report import (
    DepartmentRewardStat,
    DisciplineFormStat,
    RewardDisciplineReportPage,
    RewardDisciplineSummary,
    RewardTypeStat,
)
from app.services import access_scope_service, discipline_service, reward_service

# Thứ tự cố định các hình thức kỷ luật
_DISCIPLINE_FORM_ORDER = [
    "khien_trach",
    "keo_dai_nang_luong",
    "cach_chuc",
    "sa_thai",
]


async def get_reward_discipline_report(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    department_id: Optional[int] = None,
    allowed_department_ids: Optional[list[int] | set[int] | tuple[int, ...]] = None,
    reward_page: int = 1,
    reward_page_size: int = 20,
    discipline_page: int = 1,
    discipline_page_size: int = 20,
) -> RewardDisciplineReportPage:
    scope_ids = await access_scope_service.resolve_effective_department_scope_ids(
        session,
        department_id=department_id,
        allowed_department_ids=allowed_department_ids,
    )

    # ── 1. Fetch department name nếu có filter ────────────────────────────────
    department_name: Optional[str] = None
    if department_id is not None:
        dept = await session.get(Department, department_id)
        department_name = dept.name if dept else None

    # ── 2. Reward stats: by_reward_type ──────────────────────────────────────
    reward_type_stmt = (
        select(
            EmployeeReward.reward_type_id,
            RewardType.name,
            RewardType.is_monetary,
            func.count(EmployeeReward.id).label("cnt"),
            func.sum(EmployeeReward.value).label("total_val"),
        )
        .join(Employee, Employee.id == EmployeeReward.employee_id)
        .join(RewardType, RewardType.id == EmployeeReward.reward_type_id)
        .outerjoin(
            EmployeeJobRecord,
            (EmployeeJobRecord.employee_id == Employee.id)
            & (EmployeeJobRecord.is_current == True),  # noqa: E712
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
        .where(EmployeeReward.reward_date >= from_date)
        .where(EmployeeReward.reward_date <= to_date)
        .group_by(EmployeeReward.reward_type_id, RewardType.name, RewardType.is_monetary)
    )
    if scope_ids is not None:
        if not scope_ids:
            reward_type_stmt = reward_type_stmt.where(False)
        else:
            reward_type_stmt = reward_type_stmt.where(EmployeeJobRecord.department_id.in_(scope_ids))

    reward_type_rows = (await session.execute(reward_type_stmt)).all()

    by_reward_type: list[RewardTypeStat] = []
    total_rewards = 0
    total_reward_value = Decimal("0")
    for row in reward_type_rows:
        cnt = row.cnt or 0
        total_rewards += cnt
        tv: Optional[Decimal] = None
        if row.is_monetary and row.total_val is not None:
            tv = Decimal(str(row.total_val))
            total_reward_value += tv
        by_reward_type.append(
            RewardTypeStat(
                reward_type_id=row.reward_type_id,
                reward_type_name=row.name,
                count=cnt,
                total_value=tv,
            )
        )

    # ── 3. Reward stats: by_department (reward counts) ───────────────────────
    reward_dept_stmt = (
        select(
            EmployeeJobRecord.department_id,
            Department.name.label("dept_name"),
            func.count(EmployeeReward.id).label("cnt"),
        )
        .join(Employee, Employee.id == EmployeeReward.employee_id)
        .outerjoin(
            EmployeeJobRecord,
            (EmployeeJobRecord.employee_id == Employee.id)
            & (EmployeeJobRecord.is_current == True),  # noqa: E712
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
        .where(EmployeeReward.reward_date >= from_date)
        .where(EmployeeReward.reward_date <= to_date)
        .group_by(EmployeeJobRecord.department_id, Department.name)
    )
    if scope_ids is not None:
        if not scope_ids:
            reward_dept_stmt = reward_dept_stmt.where(False)
        else:
            reward_dept_stmt = reward_dept_stmt.where(EmployeeJobRecord.department_id.in_(scope_ids))

    reward_dept_rows = (await session.execute(reward_dept_stmt)).all()

    # dept_id → {dept_name, reward_count, discipline_count}
    dept_map: dict[Optional[int], dict] = defaultdict(
        lambda: {"department_name": None, "reward_count": 0, "discipline_count": 0}
    )
    for row in reward_dept_rows:
        key = row.department_id
        dept_map[key]["department_name"] = row.dept_name
        dept_map[key]["reward_count"] += row.cnt or 0

    # ── 4. Discipline stats: by_discipline_form ───────────────────────────────
    disc_form_stmt = (
        select(
            EmployeeDiscipline.discipline_form,
            func.count(EmployeeDiscipline.id).label("cnt"),
        )
        .join(Employee, Employee.id == EmployeeDiscipline.employee_id)
        .outerjoin(
            EmployeeJobRecord,
            (EmployeeJobRecord.employee_id == Employee.id)
            & (EmployeeJobRecord.is_current == True),  # noqa: E712
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
        .where(EmployeeDiscipline.effective_date >= from_date)
        .where(EmployeeDiscipline.effective_date <= to_date)
        .group_by(EmployeeDiscipline.discipline_form)
    )
    if scope_ids is not None:
        if not scope_ids:
            disc_form_stmt = disc_form_stmt.where(False)
        else:
            disc_form_stmt = disc_form_stmt.where(EmployeeJobRecord.department_id.in_(scope_ids))

    disc_form_rows = (await session.execute(disc_form_stmt)).all()
    disc_form_map: dict[str, int] = {row.discipline_form: row.cnt or 0 for row in disc_form_rows}
    total_disciplines = sum(disc_form_map.values())

    # Always include all 4 forms (count=0 if none), in fixed order
    by_discipline_form: list[DisciplineFormStat] = [
        DisciplineFormStat(
            discipline_form=form,
            discipline_form_label=DISCIPLINE_FORMS[form],
            count=disc_form_map.get(form, 0),
        )
        for form in _DISCIPLINE_FORM_ORDER
    ]

    # ── 5. Discipline stats: by_department (discipline counts) ───────────────
    disc_dept_stmt = (
        select(
            EmployeeJobRecord.department_id,
            Department.name.label("dept_name"),
            func.count(EmployeeDiscipline.id).label("cnt"),
        )
        .join(Employee, Employee.id == EmployeeDiscipline.employee_id)
        .outerjoin(
            EmployeeJobRecord,
            (EmployeeJobRecord.employee_id == Employee.id)
            & (EmployeeJobRecord.is_current == True),  # noqa: E712
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
        .where(EmployeeDiscipline.effective_date >= from_date)
        .where(EmployeeDiscipline.effective_date <= to_date)
        .group_by(EmployeeJobRecord.department_id, Department.name)
    )
    if scope_ids is not None:
        if not scope_ids:
            disc_dept_stmt = disc_dept_stmt.where(False)
        else:
            disc_dept_stmt = disc_dept_stmt.where(EmployeeJobRecord.department_id.in_(scope_ids))

    disc_dept_rows = (await session.execute(disc_dept_stmt)).all()
    for row in disc_dept_rows:
        key = row.department_id
        dept_map[key]["department_name"] = dept_map[key]["department_name"] or row.dept_name
        dept_map[key]["discipline_count"] += row.cnt or 0

    # ── 6. Build by_department list ───────────────────────────────────────────
    by_department: list[DepartmentRewardStat] = [
        DepartmentRewardStat(
            department_id=dept_id,
            department_name=info["department_name"],
            reward_count=info["reward_count"],
            discipline_count=info["discipline_count"],
        )
        for dept_id, info in sorted(
            dept_map.items(),
            key=lambda x: (x[0] is None, x[1]["department_name"] or ""),
        )
    ]

    # ── 7. Paginated items via existing services ──────────────────────────────
    reward_page_result = await reward_service.list_rewards(
        session,
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
        allowed_department_ids=allowed_department_ids,
        page=reward_page,
        page_size=reward_page_size,
    )
    discipline_page_result = await discipline_service.list_disciplines(
        session,
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
        allowed_department_ids=allowed_department_ids,
        page=discipline_page,
        page_size=discipline_page_size,
    )

    summary = RewardDisciplineSummary(
        total_rewards=total_rewards,
        total_disciplines=total_disciplines,
        total_reward_value=total_reward_value,
        by_reward_type=by_reward_type,
        by_discipline_form=by_discipline_form,
        by_department=by_department,
    )

    return RewardDisciplineReportPage(
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
        department_name=department_name,
        summary=summary,
        reward_items=reward_page_result.items,
        discipline_items=discipline_page_result.items,
        total_rewards=reward_page_result.total,
        total_disciplines=discipline_page_result.total,
    )
