from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_insurance import EmployeeInsuranceProfile


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_bhxh_code(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def derive_participation_status(employee_status: str) -> str:
    return "stopped" if employee_status == "resigned" else "active"


async def get_employee_insurance_profile(
    session: AsyncSession,
    employee_id: int,
) -> Optional[EmployeeInsuranceProfile]:
    return (
        await session.execute(
            select(EmployeeInsuranceProfile).where(
                EmployeeInsuranceProfile.employee_id == employee_id
            )
        )
    ).scalar_one_or_none()


async def ensure_employee_insurance_profile(
    session: AsyncSession,
    employee: Employee,
) -> EmployeeInsuranceProfile:
    profile = await get_employee_insurance_profile(session, employee.id)
    if profile:
        return profile

    profile = EmployeeInsuranceProfile(
        employee_id=employee.id,
        bhxh_code=normalize_bhxh_code(employee.bhxh_code),
        participation_status=derive_participation_status(employee.status),
        insurance_basis_source="contract",
        created_at=_utcnow(),
    )
    session.add(profile)
    await session.flush()
    return profile


async def sync_employee_profile_from_employee(
    session: AsyncSession,
    employee: Employee,
) -> EmployeeInsuranceProfile:
    employee.bhxh_code = normalize_bhxh_code(employee.bhxh_code)
    profile = await ensure_employee_insurance_profile(session, employee)
    profile.bhxh_code = employee.bhxh_code
    profile.updated_at = _utcnow()
    return profile
