"""Service cho thông tin người thân nhân viên (3.3)."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee_relative import EmployeeRelative
from app.schemas.employee import RelativeCreate, RelativeUpdate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_relatives(
    session: AsyncSession, employee_id: int
) -> list[EmployeeRelative]:
    rows = (
        await session.execute(
            select(EmployeeRelative)
            .where(EmployeeRelative.employee_id == employee_id)
            .order_by(
                EmployeeRelative.is_emergency_contact.desc(),
                EmployeeRelative.created_at.asc(),
            )
        )
    ).scalars().all()
    return list(rows)


async def create_relative(
    session: AsyncSession,
    employee_id: int,
    payload: RelativeCreate,
) -> EmployeeRelative:
    rel = EmployeeRelative(
        employee_id=employee_id,
        full_name=payload.full_name,
        relationship_type=payload.relationship_type,
        date_of_birth=payload.date_of_birth,
        occupation=payload.occupation,
        phone_number=payload.phone_number,
        is_emergency_contact=payload.is_emergency_contact,
        note=payload.note,
        created_at=_utcnow(),
    )
    session.add(rel)
    return rel


async def _get_relative_or_404(
    session: AsyncSession, employee_id: int, relative_id: int
) -> EmployeeRelative:
    rel = await session.get(EmployeeRelative, relative_id)
    if not rel or rel.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người thân")
    return rel


async def update_relative(
    session: AsyncSession,
    employee_id: int,
    relative_id: int,
    payload: RelativeUpdate,
) -> EmployeeRelative:
    rel = await _get_relative_or_404(session, employee_id, relative_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rel, field, value)
    rel.updated_at = _utcnow()
    return rel


async def delete_relative(
    session: AsyncSession, employee_id: int, relative_id: int
) -> None:
    rel = await _get_relative_or_404(session, employee_id, relative_id)
    await session.delete(rel)
