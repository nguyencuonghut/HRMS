"""Service tính toán sự kiện nhân sự sắp đến (3.6)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.schemas.reminder import (
    ANNIVERSARY_MILESTONES,
    ReminderItem,
    RemindersResponse,
)


def _add_years(d: date, years: int) -> date:
    """Cộng N năm vào ngày, xử lý 29/2 → 28/2 nếu năm đích không nhuận."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # 29/2 trong năm nhuận → 28/2 trong năm thường
        return d.replace(year=d.year + years, day=28)


def _next_occurrence(month: int, day: int, today: date) -> date:
    """Trả về ngày (month, day) gần nhất >= today (năm nay hoặc năm sau)."""
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        # 29/2 → 28/2
        candidate = date(today.year, month, 28)
    if candidate < today:
        try:
            candidate = date(today.year + 1, month, day)
        except ValueError:
            candidate = date(today.year + 1, month, 28)
    return candidate


async def _get_active_employees(session: AsyncSession) -> list[Employee]:
    rows = await session.execute(
        select(Employee).where(Employee.status != "resigned", Employee.is_active.is_(True))
    )
    return list(rows.scalars().all())


async def _get_department_map(session: AsyncSession) -> dict[int, str]:
    """employee_id → department_name từ bản ghi công việc hiện hành."""
    rows = await session.execute(
        text("""
            SELECT ejr.employee_id, d.name
            FROM employee_job_records ejr
            JOIN departments d ON d.id = ejr.department_id
            WHERE ejr.is_current = TRUE
        """)
    )
    return {row[0]: row[1] for row in rows.fetchall()}


async def _get_birthdays(
    session: AsyncSession,
    employees: list[Employee],
    dept_map: dict[int, str],
    today: date,
    end: date,
) -> list[ReminderItem]:
    items: list[ReminderItem] = []
    for emp in employees:
        if not emp.date_of_birth:
            continue
        event_date = _next_occurrence(emp.date_of_birth.month, emp.date_of_birth.day, today)
        if today <= event_date <= end:
            items.append(ReminderItem(
                employee_id=emp.id,
                employee_code=emp.id_number or "",
                employee_name=emp.full_name,
                department=dept_map.get(emp.id),
                event_type="birthday",
                event_date=event_date,
                days_until=(event_date - today).days,
            ))
    return sorted(items, key=lambda x: x.days_until)


async def _get_anniversaries(
    session: AsyncSession,
    employees: list[Employee],
    dept_map: dict[int, str],
    today: date,
    end: date,
) -> list[ReminderItem]:
    items: list[ReminderItem] = []
    for emp in employees:
        if not emp.start_date:
            continue
        for years in ANNIVERSARY_MILESTONES:
            ann_date = _add_years(emp.start_date, years)
            if today <= ann_date <= end:
                items.append(ReminderItem(
                    employee_id=emp.id,
                    employee_code=emp.id_number or "",
                    employee_name=emp.full_name,
                    department=dept_map.get(emp.id),
                    event_type="anniversary",
                    event_date=ann_date,
                    days_until=(ann_date - today).days,
                    extra={"years": years},
                ))
    return sorted(items, key=lambda x: x.days_until)


async def _get_probation_ends(
    session: AsyncSession,
    dept_map: dict[int, str],
    today: date,
    end: date,
) -> list[ReminderItem]:
    rows = await session.execute(
        select(Employee, EmployeeJobRecord)
        .join(EmployeeJobRecord, EmployeeJobRecord.employee_id == Employee.id)
        .where(
            EmployeeJobRecord.is_current.is_(True),
            EmployeeJobRecord.probation_end_date.isnot(None),
            EmployeeJobRecord.probation_end_date >= today,
            EmployeeJobRecord.probation_end_date <= end,
            Employee.status == "probation",
        )
    )
    items: list[ReminderItem] = []
    for emp, job in rows.fetchall():
        items.append(ReminderItem(
            employee_id=emp.id,
            employee_code=emp.id_number or "",
            employee_name=emp.full_name,
            department=dept_map.get(emp.id),
            event_type="probation_end",
            event_date=job.probation_end_date,
            days_until=(job.probation_end_date - today).days,
        ))
    return sorted(items, key=lambda x: x.days_until)


async def get_reminders(
    session: AsyncSession,
    days: int = 30,
    types: Optional[set[str]] = None,
) -> RemindersResponse:
    types = types or {"birthday", "anniversary", "probation_end"}
    today = date.today()
    end   = today + timedelta(days=days)

    employees = await _get_active_employees(session)
    dept_map  = await _get_department_map(session)

    birthday      = await _get_birthdays(session, employees, dept_map, today, end)      if "birthday"      in types else []
    anniversary   = await _get_anniversaries(session, employees, dept_map, today, end)  if "anniversary"   in types else []
    probation_end = await _get_probation_ends(session, dept_map, today, end)            if "probation_end" in types else []

    return RemindersResponse(
        birthday=birthday,
        anniversary=anniversary,
        probation_end=probation_end,
        total=len(birthday) + len(anniversary) + len(probation_end),
    )
