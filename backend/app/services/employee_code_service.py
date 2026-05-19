from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_code import EmployeeCodeSequence, EmployeeCodeSequenceRule
from app.models.org import Department
from app.services import employee_job_service


def compute_employee_display_code(
    employee_seq: int,
    dept_display_prefix: Optional[str] = None,
    *,
    min_digits: int = 4,
) -> str:
    digits = max(1, min_digits)
    seq_str = f"{employee_seq:0{digits}d}"
    return f"{dept_display_prefix}{seq_str}" if dept_display_prefix else seq_str


async def get_default_employee_code_sequence(
    session: AsyncSession,
) -> Optional[EmployeeCodeSequence]:
    return (
        await session.execute(
            select(EmployeeCodeSequence).where(
                EmployeeCodeSequence.is_default.is_(True),
                EmployeeCodeSequence.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()


async def resolve_employee_code_sequence(
    session: AsyncSession,
    *,
    department_id: int | None = None,
    job_position_id: int | None = None,
) -> Optional[EmployeeCodeSequence]:
    if job_position_id is not None:
        row = (
            await session.execute(
                select(EmployeeCodeSequence)
                .join(
                    EmployeeCodeSequenceRule,
                    EmployeeCodeSequenceRule.employee_code_sequence_id == EmployeeCodeSequence.id,
                )
                .where(
                    EmployeeCodeSequenceRule.scope_type == "job_position",
                    EmployeeCodeSequenceRule.job_position_id == job_position_id,
                    EmployeeCodeSequenceRule.is_active.is_(True),
                    EmployeeCodeSequence.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if row:
            return row

    current_department_id = department_id
    while current_department_id is not None:
        rule = (
            await session.execute(
                select(EmployeeCodeSequenceRule, EmployeeCodeSequence, Department.parent_id)
                .join(
                    EmployeeCodeSequence,
                    EmployeeCodeSequence.id == EmployeeCodeSequenceRule.employee_code_sequence_id,
                )
                .join(Department, Department.id == EmployeeCodeSequenceRule.department_id)
                .where(
                    EmployeeCodeSequenceRule.scope_type == "department",
                    EmployeeCodeSequenceRule.department_id == current_department_id,
                    EmployeeCodeSequenceRule.is_active.is_(True),
                    EmployeeCodeSequence.is_active.is_(True),
                )
            )
        ).first()
        if rule:
            rule_row, sequence_row, parent_id = rule
            if current_department_id == department_id or rule_row.apply_to_descendants:
                return sequence_row
            current_department_id = parent_id
            continue

        if current_department_id == department_id:
            parent_row = await session.execute(
                select(Department.parent_id).where(Department.id == current_department_id)
            )
            current_department_id = parent_row.scalar_one_or_none()
        else:
            parent_row = await session.execute(
                select(Department.parent_id).where(Department.id == current_department_id)
            )
            current_department_id = parent_row.scalar_one_or_none()

    return await get_default_employee_code_sequence(session)


async def _get_sequence_min_digits_map(
    session: AsyncSession,
    sequence_ids: set[int],
) -> dict[int, int]:
    if not sequence_ids:
        return {}
    rows = (
        await session.execute(
            select(EmployeeCodeSequence.id, EmployeeCodeSequence.min_digits).where(
                EmployeeCodeSequence.id.in_(sequence_ids)
            )
        )
    ).all()
    return {row.id: row.min_digits for row in rows}


async def build_employee_display_code(
    session: AsyncSession,
    emp: Employee,
) -> str:
    prefix = await employee_job_service.get_display_code_prefix(session, emp.id)
    min_digits = 4
    if emp.employee_code_sequence_id is not None:
        sequence = await session.get(EmployeeCodeSequence, emp.employee_code_sequence_id)
        if sequence:
            min_digits = sequence.min_digits
    return compute_employee_display_code(emp.employee_seq, prefix, min_digits=min_digits)


async def batch_build_employee_display_codes(
    session: AsyncSession,
    employees: list[Employee],
) -> dict[int, str]:
    if not employees:
        return {}

    emp_ids = [emp.id for emp in employees]
    prefixes = await employee_job_service.batch_get_display_code_prefixes(session, emp_ids)
    min_digits_map = await _get_sequence_min_digits_map(
        session,
        {emp.employee_code_sequence_id for emp in employees if emp.employee_code_sequence_id is not None},
    )

    return {
        emp.id: compute_employee_display_code(
            emp.employee_seq,
            prefixes.get(emp.id),
            min_digits=min_digits_map.get(emp.employee_code_sequence_id, 4),
        )
        for emp in employees
    }
