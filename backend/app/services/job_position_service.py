from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee_code import EmployeeCodeSequenceRule
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department, JobPosition, JobPositionAttachment, JobTitle, OrgChangeLog
from app.schemas.job_position import (
    JobPositionCreate,
    JobPositionListItem,
    JobPositionRead,
    JobPositionUpdate,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_dict(pos: JobPosition) -> dict:
    return {
        "id":                 pos.id,
        "code":               pos.code,
        "name":               pos.name,
        "department_id":      pos.department_id,
        "job_title_id":       pos.job_title_id,
        "default_grade":      pos.default_grade,
        "bhxh_allowance":     int(pos.bhxh_allowance),
        "non_bhxh_allowance": int(pos.non_bhxh_allowance),
        "is_active":          pos.is_active,
    }


async def _log(session, pos, action, old_data, new_data, changed_by):
    session.add(OrgChangeLog(
        entity_type="job_position",
        entity_id=pos.id,
        entity_name=pos.name,
        action=action,
        changed_by=changed_by,
        old_data=old_data,
        new_data=new_data,
    ))


async def _require_department(session: AsyncSession, dept_id: int) -> None:
    r = await session.execute(select(Department).where(Department.id == dept_id))
    if not r.scalar_one_or_none():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng/ban")


async def _require_job_title(session: AsyncSession, jt_id: int) -> None:
    r = await session.execute(select(JobTitle).where(JobTitle.id == jt_id))
    if not r.scalar_one_or_none():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chức danh")


async def _has_active_job_position_rule(session: AsyncSession, pos_id: int) -> bool:
    count = (
        await session.execute(
            select(func.count()).select_from(EmployeeCodeSequenceRule).where(
                EmployeeCodeSequenceRule.scope_type == "job_position",
                EmployeeCodeSequenceRule.job_position_id == pos_id,
                EmployeeCodeSequenceRule.is_active.is_(True),
            )
        )
    ).scalar_one()
    return count > 0


async def _has_current_assignee(session: AsyncSession, pos_id: int) -> bool:
    count = (
        await session.execute(
            select(func.count()).select_from(EmployeeJobRecord).where(
                EmployeeJobRecord.job_position_id == pos_id,
                EmployeeJobRecord.is_current.is_(True),
            )
        )
    ).scalar_one()
    return count > 0


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_by_id(session: AsyncSession, pos_id: int) -> JobPosition:
    r = await session.execute(select(JobPosition).where(JobPosition.id == pos_id))
    pos = r.scalar_one_or_none()
    if not pos:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy vị trí công việc")
    return pos


async def get_list(
    session: AsyncSession,
    department_id: Optional[int] = None,
    is_active:     Optional[bool] = None,
    search:        Optional[str]  = None,
) -> list[JobPositionListItem]:
    q = (
        select(
            JobPosition,
            Department.name.label("department_name"),
            JobTitle.name.label("job_title_name"),
        )
        .join(Department, JobPosition.department_id == Department.id)
        .outerjoin(JobTitle, JobPosition.job_title_id == JobTitle.id)
    )

    if department_id is not None:
        q = q.where(JobPosition.department_id == department_id)
    if is_active is not None:
        q = q.where(JobPosition.is_active == is_active)
    if search:
        term = f"%{search.strip()}%"
        q = q.where(or_(
            JobPosition.name.ilike(term),
            JobPosition.code.ilike(term),
        ))

    q = q.order_by(Department.name, JobPosition.name)
    rows = (await session.execute(q)).all()

    return [
        JobPositionListItem(
            id=pos.id,
            code=pos.code,
            name=pos.name,
            department_id=pos.department_id,
            department_name=dept_name,
            job_title_id=pos.job_title_id,
            job_title_name=jt_name,
            bhxh_allowance=int(pos.bhxh_allowance),
            non_bhxh_allowance=int(pos.non_bhxh_allowance),
            is_active=pos.is_active,
            created_at=pos.created_at,
            updated_at=pos.updated_at,
        )
        for pos, dept_name, jt_name in rows
    ]


async def create(
    session: AsyncSession,
    data: JobPositionCreate,
    changed_by: Optional[int] = None,
) -> JobPosition:
    existing = await session.execute(select(JobPosition).where(JobPosition.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Mã vị trí '{data.code}' đã tồn tại")

    await _require_department(session, data.department_id)
    if data.job_title_id is not None:
        await _require_job_title(session, data.job_title_id)

    pos = JobPosition(
        code=data.code,
        name=data.name,
        department_id=data.department_id,
        job_title_id=data.job_title_id,
        default_grade=data.default_grade,
        bhxh_allowance=data.bhxh_allowance,
        non_bhxh_allowance=data.non_bhxh_allowance,
        description=data.description,
        requirements=data.requirements,
    )
    session.add(pos)
    await session.flush()

    await _log(session, pos, "create", None, _to_dict(pos), changed_by)
    await session.commit()
    await session.refresh(pos)
    return pos


async def update(
    session: AsyncSession,
    pos_id: int,
    data: JobPositionUpdate,
    changed_by: Optional[int] = None,
) -> JobPosition:
    pos = await get_by_id(session, pos_id)
    old_snapshot = _to_dict(pos)
    provided = data.model_fields_set

    if "name"               in provided and data.name               is not None: pos.name               = data.name.strip()
    if "department_id"      in provided and data.department_id      is not None:
        await _require_department(session, data.department_id)
        if data.department_id != pos.department_id:
            if await _has_active_job_position_rule(session, pos.id):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Không thể chuyển phòng ban cho vị trí khi còn rule active của hệ mã nhân viên",
                )
            if await _has_current_assignee(session, pos.id):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Không thể chuyển phòng ban cho vị trí đang được gán cho nhân viên hiện hành",
                )
        pos.department_id = data.department_id
    if "job_title_id"       in provided:
        if data.job_title_id is not None:
            await _require_job_title(session, data.job_title_id)
        pos.job_title_id = data.job_title_id
    if "default_grade"      in provided and data.default_grade      is not None: pos.default_grade      = data.default_grade
    if "bhxh_allowance"     in provided and data.bhxh_allowance     is not None: pos.bhxh_allowance     = data.bhxh_allowance
    if "non_bhxh_allowance" in provided and data.non_bhxh_allowance is not None: pos.non_bhxh_allowance = data.non_bhxh_allowance
    if "description"        in provided: pos.description  = data.description
    if "requirements"       in provided: pos.requirements = data.requirements
    if "is_active"          in provided and data.is_active is not None: pos.is_active = data.is_active

    pos.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await _log(session, pos, "update", old_snapshot, _to_dict(pos), changed_by)
    await session.commit()
    await session.refresh(pos)
    return pos


async def delete(
    session: AsyncSession,
    pos_id: int,
    changed_by: Optional[int] = None,
) -> dict:
    pos = await get_by_id(session, pos_id)
    if await _has_active_job_position_rule(session, pos.id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Không thể xóa vị trí khi còn rule active của hệ mã nhân viên",
        )
    if await _has_current_assignee(session, pos.id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Không thể xóa vị trí đang được gán cho nhân viên hiện hành",
        )

    old_snapshot = _to_dict(pos)
    pos_name = pos.name

    await _log(session, pos, "delete", old_snapshot, None, changed_by)
    await session.delete(pos)
    await session.commit()

    return {"message": f"Đã xóa vị trí '{pos_name}' thành công"}


# ── Attachments ────────────────────────────────────────────────────────────────

async def get_attachments(
    session: AsyncSession,
    pos_id: int,
) -> list[JobPositionAttachment]:
    r = await session.execute(
        select(JobPositionAttachment)
        .where(JobPositionAttachment.job_position_id == pos_id)
        .order_by(JobPositionAttachment.uploaded_at.desc())
    )
    return list(r.scalars().all())


async def get_attachment_by_id(
    session: AsyncSession,
    pos_id: int,
    att_id: int,
) -> JobPositionAttachment:
    r = await session.execute(
        select(JobPositionAttachment).where(
            JobPositionAttachment.id == att_id,
            JobPositionAttachment.job_position_id == pos_id,
        )
    )
    att = r.scalar_one_or_none()
    if not att:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy file đính kèm")
    return att
