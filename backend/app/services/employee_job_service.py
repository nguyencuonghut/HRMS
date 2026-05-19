"""Service cho employee_job_records (3.2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department, JobPosition, JobTitle
from app.schemas.employee import JobRecordCreate, JobRecordTransfer, JobRecordUpdate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _require_department(session: AsyncSession, department_id: int) -> Department:
    department = await session.get(Department, department_id)
    if not department:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng ban")
    return department


async def _require_job_title(session: AsyncSession, job_title_id: int) -> JobTitle:
    job_title = await session.get(JobTitle, job_title_id)
    if not job_title:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chức danh")
    return job_title


async def _require_job_position(session: AsyncSession, job_position_id: int) -> JobPosition:
    job_position = await session.get(JobPosition, job_position_id)
    if not job_position:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy vị trí công việc")
    return job_position


async def _validate_job_assignment(
    session: AsyncSession,
    *,
    department_id: int,
    job_title_id: int | None = None,
    job_position_id: int | None = None,
) -> None:
    await _require_department(session, department_id)

    if job_title_id is not None:
        await _require_job_title(session, job_title_id)

    if job_position_id is None:
        return

    job_position = await _require_job_position(session, job_position_id)
    if job_position.department_id != department_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Vị trí công việc không thuộc phòng ban đã chọn",
        )

    if job_title_id is not None and job_position.job_title_id is not None and job_position.job_title_id != job_title_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Vị trí công việc không khớp với chức danh đã chọn",
        )


# ── Queries ───────────────────────────────────────────────────────────────────

async def get_current_job_record(
    session: AsyncSession, employee_id: int
) -> Optional[EmployeeJobRecord]:
    result = await session.execute(
        select(EmployeeJobRecord).where(
            EmployeeJobRecord.employee_id == employee_id,
            EmployeeJobRecord.is_current == True,
        )
    )
    return result.scalar_one_or_none()


async def get_job_records(
    session: AsyncSession, employee_id: int
) -> list[EmployeeJobRecord]:
    result = await session.execute(
        select(EmployeeJobRecord)
        .where(EmployeeJobRecord.employee_id == employee_id)
        .order_by(EmployeeJobRecord.effective_from.desc(), EmployeeJobRecord.id.desc())
    )
    return list(result.scalars().all())


async def get_display_code_prefix(
    session: AsyncSession, employee_id: int
) -> Optional[str]:
    """display_prefix của phòng ban hiện tại. None nếu chưa gán hoặc phòng không có prefix."""
    result = await session.execute(
        select(Department.display_prefix)
        .join(EmployeeJobRecord, EmployeeJobRecord.department_id == Department.id)
        .where(
            EmployeeJobRecord.employee_id == employee_id,
            EmployeeJobRecord.is_current == True,
        )
    )
    return result.scalar_one_or_none()


async def batch_get_display_code_prefixes(
    session: AsyncSession, employee_ids: list[int]
) -> dict[int, Optional[str]]:
    """Batch lookup để tránh N+1 trong danh sách nhân viên."""
    if not employee_ids:
        return {}
    result = await session.execute(
        select(EmployeeJobRecord.employee_id, Department.display_prefix)
        .join(Department, EmployeeJobRecord.department_id == Department.id)
        .where(
            EmployeeJobRecord.employee_id.in_(employee_ids),
            EmployeeJobRecord.is_current == True,
        )
    )
    return {row[0]: row[1] for row in result.all()}


# ── Read enrichment ───────────────────────────────────────────────────────────

async def build_job_record_read(
    session: AsyncSession, record: EmployeeJobRecord
) -> dict:
    dept = await session.get(Department, record.department_id)
    job_title = await session.get(JobTitle, record.job_title_id) if record.job_title_id else None
    job_position = await session.get(JobPosition, record.job_position_id) if record.job_position_id else None

    return {
        "id": record.id,
        "employee_id": record.employee_id,
        "department_id": record.department_id,
        "department": {
            "id": dept.id,
            "code": dept.code,
            "name": dept.name,
            "display_prefix": dept.display_prefix,
        },
        "job_title_id": record.job_title_id,
        "job_title": {"id": job_title.id, "code": job_title.code, "name": job_title.name} if job_title else None,
        "job_position_id": record.job_position_id,
        "job_position": {"id": job_position.id, "code": job_position.code, "name": job_position.name} if job_position else None,
        "probation_start_date": record.probation_start_date,
        "probation_end_date": record.probation_end_date,
        "official_date": record.official_date,
        "effective_from": record.effective_from,
        "effective_to": record.effective_to,
        "is_current": record.is_current,
        "notes": record.notes,
        "changed_by": record.changed_by,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


# ── Mutations ─────────────────────────────────────────────────────────────────

async def create_job_record(
    session: AsyncSession,
    employee_id: int,
    payload: JobRecordCreate,
    actor_id: int,
) -> dict:
    existing = await get_current_job_record(session, employee_id)
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Nhân viên đã có bản ghi công việc hiện tại. Dùng /transfer để chuyển công tác.",
        )

    await _validate_job_assignment(
        session,
        department_id=payload.department_id,
        job_title_id=payload.job_title_id,
        job_position_id=payload.job_position_id,
    )

    record = EmployeeJobRecord(
        employee_id=employee_id,
        department_id=payload.department_id,
        job_title_id=payload.job_title_id,
        job_position_id=payload.job_position_id,
        probation_start_date=payload.probation_start_date,
        probation_end_date=payload.probation_end_date,
        official_date=payload.official_date,
        effective_from=payload.effective_from,
        is_current=True,
        notes=payload.notes,
        changed_by=actor_id,
        created_at=_utcnow(),
    )
    session.add(record)

    if payload.official_date:
        emp = await session.get(Employee, employee_id)
        if emp:
            emp.status = "official"
            emp.updated_at = _utcnow()

    await session.flush()
    await session.refresh(record)
    return await build_job_record_read(session, record)


async def update_current_record(
    session: AsyncSession,
    employee_id: int,
    payload: JobRecordUpdate,
    actor_id: int,
) -> dict:
    record = await get_current_job_record(session, employee_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Chưa có bản ghi công việc hiện tại.")

    target_department_id = payload.department_id or record.department_id
    target_job_title_id = payload.job_title_id if payload.job_title_id is not None else record.job_title_id
    target_job_position_id = payload.job_position_id if payload.job_position_id is not None else record.job_position_id
    await _validate_job_assignment(
        session,
        department_id=target_department_id,
        job_title_id=target_job_title_id,
        job_position_id=target_job_position_id,
    )

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(record, field, value)
    record.changed_by = actor_id
    record.updated_at = _utcnow()
    session.add(record)

    if payload.official_date:
        emp = await session.get(Employee, employee_id)
        if emp:
            emp.status = "official"
            emp.updated_at = _utcnow()

    await session.flush()
    await session.refresh(record)
    return await build_job_record_read(session, record)


async def transfer_job_record(
    session: AsyncSession,
    employee_id: int,
    payload: JobRecordTransfer,
    actor_id: int,
) -> dict:
    current = await get_current_job_record(session, employee_id)
    if not current:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Nhân viên chưa có bản ghi công việc. Dùng POST /job-records để tạo lần đầu.",
        )

    await _validate_job_assignment(
        session,
        department_id=payload.department_id,
        job_title_id=payload.job_title_id,
        job_position_id=payload.job_position_id,
    )

    current.effective_to = payload.effective_from - timedelta(days=1)
    current.is_current = False
    current.updated_at = _utcnow()
    session.add(current)
    # Flush trước để giải phóng partial unique index trước khi insert bản ghi mới
    await session.flush()

    new_record = EmployeeJobRecord(
        employee_id=employee_id,
        department_id=payload.department_id,
        job_title_id=payload.job_title_id,
        job_position_id=payload.job_position_id,
        effective_from=payload.effective_from,
        is_current=True,
        notes=payload.notes,
        changed_by=actor_id,
        created_at=_utcnow(),
    )
    session.add(new_record)
    await session.flush()
    await session.refresh(new_record)
    return await build_job_record_read(session, new_record)
