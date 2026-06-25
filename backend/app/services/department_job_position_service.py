from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org import DepartmentJobPosition


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_active_mapping(
    session: AsyncSession,
    *,
    department_id: int,
    job_position_id: int,
) -> DepartmentJobPosition | None:
    result = await session.execute(
        select(DepartmentJobPosition).where(
            DepartmentJobPosition.department_id == department_id,
            DepartmentJobPosition.job_position_id == job_position_id,
            DepartmentJobPosition.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def is_position_allowed_for_department(
    session: AsyncSession,
    *,
    department_id: int,
    job_position_id: int,
) -> bool:
    return (
        await get_active_mapping(
            session,
            department_id=department_id,
            job_position_id=job_position_id,
        )
    ) is not None


async def require_position_allowed_for_department(
    session: AsyncSession,
    *,
    department_id: int,
    job_position_id: int,
) -> None:
    if not await is_position_allowed_for_department(
        session,
        department_id=department_id,
        job_position_id=job_position_id,
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Vị trí công việc không thuộc phòng ban đã chọn hoặc chưa được gán cho phòng ban này",
        )


async def ensure_mapping(
    session: AsyncSession,
    *,
    department_id: int,
    job_position_id: int,
) -> DepartmentJobPosition:
    existing = await get_active_mapping(
        session,
        department_id=department_id,
        job_position_id=job_position_id,
    )
    if existing:
        return existing

    result = await session.execute(
        select(DepartmentJobPosition).where(
            DepartmentJobPosition.department_id == department_id,
            DepartmentJobPosition.job_position_id == job_position_id,
        )
    )
    mapping = result.scalar_one_or_none()
    if mapping:
        mapping.is_active = True
        mapping.updated_at = _utcnow()
        session.add(mapping)
        await session.flush()
        return mapping

    mapping = DepartmentJobPosition(
        department_id=department_id,
        job_position_id=job_position_id,
        is_active=True,
    )
    session.add(mapping)
    await session.flush()
    return mapping


async def deactivate_mapping(
    session: AsyncSession,
    *,
    department_id: int,
    job_position_id: int,
) -> None:
    mapping = await get_active_mapping(
        session,
        department_id=department_id,
        job_position_id=job_position_id,
    )
    if not mapping:
        return
    mapping.is_active = False
    mapping.updated_at = _utcnow()
    session.add(mapping)
    await session.flush()
