from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department, DepartmentHead, JobPosition, JobTitle
from app.schemas.department import DepartmentHeadRead, DepartmentHeadEmployeeRead, DepartmentHeadUpsert
from app.services import employee_code_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _require_department(session: AsyncSession, dept_id: int) -> Department:
    department = await session.get(Department, dept_id)
    if not department or department.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng/ban")
    return department


async def _require_employee(session: AsyncSession, employee_id: int) -> Employee:
    employee = await session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    if not employee.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Nhân viên đã bị vô hiệu hóa")
    if employee.status == "resigned":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Không thể gán nhân viên đã nghỉ việc làm người đứng đầu")
    return employee


async def _get_current_head_record(
    session: AsyncSession,
    dept_id: int,
) -> Optional[DepartmentHead]:
    result = await session.execute(
        select(DepartmentHead).where(
            DepartmentHead.department_id == dept_id,
            DepartmentHead.is_current.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def _get_employee_current_context(
    session: AsyncSession,
    employee_id: int,
):
    result = await session.execute(
        select(
            EmployeeJobRecord.department_id.label("department_id"),
            Department.name.label("department_name"),
            JobPosition.id.label("job_position_id"),
            JobPosition.name.label("job_position_name"),
            JobTitle.id.label("job_title_id"),
            JobTitle.name.label("job_title_name"),
        )
        .select_from(EmployeeJobRecord)
        .join(Department, Department.id == EmployeeJobRecord.department_id)
        .outerjoin(JobPosition, JobPosition.id == EmployeeJobRecord.job_position_id)
        .outerjoin(JobTitle, JobTitle.id == EmployeeJobRecord.job_title_id)
        .where(
            EmployeeJobRecord.employee_id == employee_id,
            EmployeeJobRecord.is_current.is_(True),
        )
    )
    return result.first()


async def _build_read(
    session: AsyncSession,
    record: DepartmentHead,
) -> DepartmentHeadRead:
    employee = await _require_employee(session, record.employee_id)
    context = await _get_employee_current_context(session, record.employee_id)
    display_code = await employee_code_service.build_employee_display_code(session, employee)
    current_department_id = context.department_id if context else None
    current_job_position_name = context.job_position_name if context else None
    display_position_label = (
        (record.head_role_label or "").strip()
        or current_job_position_name
        or "Người phụ trách"
    )
    return DepartmentHeadRead(
        id=record.id,
        department_id=record.department_id,
        employee_id=record.employee_id,
        head_role_label=record.head_role_label,
        display_position_label=display_position_label,
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        is_current=record.is_current,
        employee=DepartmentHeadEmployeeRead(
            id=employee.id,
            display_code=display_code,
            full_name=employee.full_name,
            status=employee.status,
            current_department_id=current_department_id,
            current_department_name=context.department_name if context else None,
            current_job_position_id=context.job_position_id if context else None,
            current_job_position_name=current_job_position_name,
            current_job_title_id=context.job_title_id if context else None,
            current_job_title_name=context.job_title_name if context else None,
            is_cross_department_assignment=(
                current_department_id is not None and current_department_id != record.department_id
            ),
        ),
    )


async def get_current_head(
    session: AsyncSession,
    dept_id: int,
) -> Optional[DepartmentHeadRead]:
    await _require_department(session, dept_id)
    current = await _get_current_head_record(session, dept_id)
    if current is None:
        return None
    return await _build_read(session, current)


async def upsert_head(
    session: AsyncSession,
    dept_id: int,
    payload: DepartmentHeadUpsert,
    actor_id: int,
) -> tuple[DepartmentHeadRead, str, Optional[dict], dict]:
    await _require_department(session, dept_id)
    employee = await _require_employee(session, payload.employee_id)

    label = payload.head_role_label.strip() if payload.head_role_label and payload.head_role_label.strip() else None
    current = await _get_current_head_record(session, dept_id)
    old_snapshot = None
    action = "CREATE"

    if current is not None:
        old_snapshot = {
            "id": current.id,
            "department_id": current.department_id,
            "employee_id": current.employee_id,
            "head_role_label": current.head_role_label,
            "effective_from": current.effective_from.isoformat(),
            "effective_to": current.effective_to.isoformat() if current.effective_to else None,
            "is_current": current.is_current,
        }
        action = "UPDATE"

        if payload.effective_from < current.effective_from:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="effective_from mới không được sớm hơn effective_from của head hiện tại",
            )

        if payload.effective_from == current.effective_from:
            current.employee_id = payload.employee_id
            current.head_role_label = label
            current.changed_by = actor_id
            current.updated_at = _utcnow()
            await session.flush()
            await session.refresh(current)
            new_snapshot = {
                "id": current.id,
                "department_id": current.department_id,
                "employee_id": current.employee_id,
                "head_role_label": current.head_role_label,
                "effective_from": current.effective_from.isoformat(),
                "effective_to": current.effective_to.isoformat() if current.effective_to else None,
                "is_current": current.is_current,
            }
            return await _build_read(session, current), action, old_snapshot, new_snapshot

        current.is_current = False
        current.effective_to = payload.effective_from - timedelta(days=1)
        current.changed_by = actor_id
        current.updated_at = _utcnow()
        await session.flush()

    new_record = DepartmentHead(
        department_id=dept_id,
        employee_id=employee.id,
        head_role_label=label,
        effective_from=payload.effective_from,
        effective_to=None,
        is_current=True,
        changed_by=actor_id,
        created_at=_utcnow(),
    )
    session.add(new_record)
    await session.flush()
    await session.refresh(new_record)
    new_snapshot = {
        "id": new_record.id,
        "department_id": new_record.department_id,
        "employee_id": new_record.employee_id,
        "head_role_label": new_record.head_role_label,
        "effective_from": new_record.effective_from.isoformat(),
        "effective_to": new_record.effective_to.isoformat() if new_record.effective_to else None,
        "is_current": new_record.is_current,
    }
    return await _build_read(session, new_record), action, old_snapshot, new_snapshot


async def delete_current_head(
    session: AsyncSession,
    dept_id: int,
    actor_id: int,
) -> tuple[dict, dict]:
    await _require_department(session, dept_id)
    current = await _get_current_head_record(session, dept_id)
    if current is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Đơn vị này chưa có người đứng đầu hiện hành",
        )

    old_snapshot = {
        "id": current.id,
        "department_id": current.department_id,
        "employee_id": current.employee_id,
        "head_role_label": current.head_role_label,
        "effective_from": current.effective_from.isoformat(),
        "effective_to": current.effective_to.isoformat() if current.effective_to else None,
        "is_current": current.is_current,
    }

    current.is_current = False
    current.effective_to = date.today()
    current.changed_by = actor_id
    current.updated_at = _utcnow()
    await session.flush()

    new_snapshot = {
        "id": current.id,
        "department_id": current.department_id,
        "employee_id": current.employee_id,
        "head_role_label": current.head_role_label,
        "effective_from": current.effective_from.isoformat(),
        "effective_to": current.effective_to.isoformat() if current.effective_to else None,
        "is_current": current.is_current,
    }
    return old_snapshot, new_snapshot
