from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_code import EmployeeCodeSequenceRule
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department, DepartmentJobPosition, JobPosition, JobPositionAttachment, JobTitle, OrgChangeLog
from app.schemas.job_position import (
    JobPositionDepartmentAssignment,
    JobPositionCreate,
    JobPositionListItem,
    JobPositionRead,
    JobPositionUpdate,
    enrich_probation_legal_group_fields,
)
from app.services import department_job_position_service


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
        "probation_legal_group": pos.probation_legal_group,
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


async def _require_departments(session: AsyncSession, dept_ids: list[int]) -> None:
    unique_ids = sorted(set(dept_ids))
    if not unique_ids:
        return
    rows = (
        await session.execute(
            select(Department.id).where(
                Department.id.in_(unique_ids),
                Department.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    found_ids = set(rows)
    missing = [dept_id for dept_id in unique_ids if dept_id not in found_ids]
    if missing:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phòng/ban: {', '.join(str(item) for item in missing)}",
        )


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


async def _has_current_assignee_in_department(
    session: AsyncSession,
    *,
    pos_id: int,
    department_id: int,
) -> bool:
    count = (
        await session.execute(
            select(func.count())
            .select_from(EmployeeJobRecord)
            .join(
                Employee,
                and_(
                    Employee.id == EmployeeJobRecord.employee_id,
                    Employee.is_active == True,  # noqa: E712
                    Employee.status != "resigned",
                ),
            )
            .where(
                EmployeeJobRecord.job_position_id == pos_id,
                EmployeeJobRecord.department_id == department_id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
        )
    ).scalar_one()
    return count > 0


def _normalize_assigned_department_ids(
    *,
    owner_department_id: int,
    assigned_department_ids: Optional[list[int]],
) -> list[int]:
    ordered_ids = [owner_department_id, *(assigned_department_ids or [])]
    result: list[int] = []
    seen: set[int] = set()
    for department_id in ordered_ids:
        if department_id in seen:
            continue
        seen.add(department_id)
        result.append(department_id)
    return result


async def _get_active_mapping_department_ids(
    session: AsyncSession,
    *,
    pos_id: int,
) -> list[int]:
    return list(
        (
            await session.execute(
                select(DepartmentJobPosition.department_id).where(
                    DepartmentJobPosition.job_position_id == pos_id,
                    DepartmentJobPosition.is_active.is_(True),
                )
            )
        ).scalars().all()
    )


async def _sync_position_department_mappings(
    session: AsyncSession,
    *,
    pos_id: int,
    target_department_ids: list[int],
) -> None:
    current_department_ids = set(
        await _get_active_mapping_department_ids(session, pos_id=pos_id)
    )
    target_set = set(target_department_ids)

    to_remove = current_department_ids - target_set
    for department_id in to_remove:
        if await _has_current_assignee_in_department(
            session,
            pos_id=pos_id,
            department_id=department_id,
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Không thể gỡ gán vị trí khỏi đơn vị khi còn nhân sự hiện hành đang dùng vị trí này tại đơn vị đó",
            )
        await department_job_position_service.deactivate_mapping(
            session,
            department_id=department_id,
            job_position_id=pos_id,
        )

    for department_id in target_department_ids:
        await department_job_position_service.ensure_mapping(
            session,
            department_id=department_id,
            job_position_id=pos_id,
        )


async def _get_assignments_by_position_ids(
    session: AsyncSession,
    *,
    pos_ids: list[int],
) -> dict[int, list[JobPositionDepartmentAssignment]]:
    if not pos_ids:
        return {}
    rows = (
        await session.execute(
            select(
                DepartmentJobPosition.job_position_id,
                Department.id,
                Department.code,
                Department.name,
            )
            .join(Department, Department.id == DepartmentJobPosition.department_id)
            .where(
                DepartmentJobPosition.job_position_id.in_(pos_ids),
                DepartmentJobPosition.is_active.is_(True),
                Department.deleted_at.is_(None),
            )
            .order_by(Department.name.asc(), Department.id.asc())
        )
    ).all()
    result: dict[int, list[JobPositionDepartmentAssignment]] = {}
    for pos_id, department_id, code, name in rows:
        result.setdefault(pos_id, []).append(
            JobPositionDepartmentAssignment(id=department_id, code=code, name=name)
        )
    return result


def _serialize_position_read(
    pos: JobPosition,
    *,
    department_name: str,
    assigned_departments: list[JobPositionDepartmentAssignment],
) -> JobPositionRead:
    assigned_department_ids = [item.id for item in assigned_departments]
    return JobPositionRead.model_validate(
        enrich_probation_legal_group_fields(
            {
                "id": pos.id,
                "code": pos.code,
                "name": pos.name,
                "department_id": pos.department_id,
                "department_name": department_name,
                "job_title_id": pos.job_title_id,
                "default_grade": pos.default_grade,
                "bhxh_allowance": int(pos.bhxh_allowance),
                "non_bhxh_allowance": int(pos.non_bhxh_allowance),
                "description": pos.description,
                "requirements": pos.requirements,
                "probation_legal_group": pos.probation_legal_group,
                "assigned_department_ids": assigned_department_ids,
                "assigned_departments": assigned_departments,
                "is_shared": len(assigned_department_ids) > 1,
                "is_active": pos.is_active,
                "created_at": pos.created_at,
                "updated_at": pos.updated_at,
            }
        )
    )


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_by_id(session: AsyncSession, pos_id: int) -> JobPosition:
    r = await session.execute(
        select(JobPosition).where(JobPosition.id == pos_id, JobPosition.deleted_at.is_(None))
    )
    pos = r.scalar_one_or_none()
    if not pos:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy vị trí công việc")
    return pos


async def _ensure_position_in_department_scope(
    session: AsyncSession,
    *,
    pos_id: int,
    allowed_department_ids: Optional[list[int]],
) -> None:
    if allowed_department_ids is None:
        return

    allowed_set = {int(item) for item in allowed_department_ids}
    if not allowed_set:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập vị trí công việc này",
        )

    mapped_department_ids = set(await _get_active_mapping_department_ids(session, pos_id=pos_id))
    if not mapped_department_ids.intersection(allowed_set):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập vị trí công việc này",
        )


async def get_read_by_id(
    session: AsyncSession,
    pos_id: int,
    *,
    allowed_department_ids: Optional[list[int]] = None,
) -> JobPositionRead:
    pos = await get_by_id(session, pos_id)
    await _ensure_position_in_department_scope(
        session,
        pos_id=pos.id,
        allowed_department_ids=allowed_department_ids,
    )
    department = await session.get(Department, pos.department_id)
    assignments = await _get_assignments_by_position_ids(session, pos_ids=[pos.id])
    return _serialize_position_read(
        pos,
        department_name=department.name if department else f"ID {pos.department_id}",
        assigned_departments=assignments.get(pos.id, []),
    )


async def get_list(
    session: AsyncSession,
    department_id: Optional[int] = None,
    is_active:     Optional[bool] = None,
    search:        Optional[str]  = None,
    allowed_department_ids: Optional[list[int]] = None,
) -> list[JobPositionListItem]:
    q = (
        select(
            JobPosition,
            Department.name.label("department_name"),
            JobTitle.name.label("job_title_name"),
        )
        .join(Department, JobPosition.department_id == Department.id)
        .outerjoin(JobTitle, JobPosition.job_title_id == JobTitle.id)
        .where(JobPosition.deleted_at.is_(None))
    )

    if department_id is not None:
        q = q.join(
            DepartmentJobPosition,
            (DepartmentJobPosition.job_position_id == JobPosition.id)
            & (DepartmentJobPosition.is_active.is_(True)),
        ).where(DepartmentJobPosition.department_id == department_id)
    elif allowed_department_ids is not None:
        if not allowed_department_ids:
            return []
        q = q.join(
            DepartmentJobPosition,
            (DepartmentJobPosition.job_position_id == JobPosition.id)
            & (DepartmentJobPosition.is_active.is_(True)),
        ).where(DepartmentJobPosition.department_id.in_(allowed_department_ids))
    if is_active is not None:
        q = q.where(JobPosition.is_active == is_active)
    if search:
        term = f"%{search.strip()}%"
        q = q.where(or_(
            JobPosition.name.ilike(term),
            JobPosition.code.ilike(term),
        ))

    q = q.order_by(Department.name, JobPosition.name)
    rows = (await session.execute(q)).unique().all()
    assignments = await _get_assignments_by_position_ids(
        session,
        pos_ids=[pos.id for pos, _, _ in rows],
    )

    return [
        JobPositionListItem(
            **enrich_probation_legal_group_fields({
                "id": pos.id,
                "code": pos.code,
                "name": pos.name,
                "department_id": pos.department_id,
                "department_name": dept_name,
                "job_title_id": pos.job_title_id,
                "job_title_name": jt_name,
                "bhxh_allowance": int(pos.bhxh_allowance),
                "non_bhxh_allowance": int(pos.non_bhxh_allowance),
                "probation_legal_group": pos.probation_legal_group,
                "assigned_department_ids": [item.id for item in assignments.get(pos.id, [])],
                "assigned_departments": assignments.get(pos.id, []),
                "is_shared": len(assignments.get(pos.id, [])) > 1,
                "is_active": pos.is_active,
                "created_at": pos.created_at,
                "updated_at": pos.updated_at,
            }),
        )
        for pos, dept_name, jt_name in rows
    ]


async def create(
    session: AsyncSession,
    data: JobPositionCreate,
    changed_by: Optional[int] = None,
) -> JobPosition:
    existing = await session.execute(
        select(JobPosition).where(JobPosition.code == data.code, JobPosition.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Mã vị trí '{data.code}' đã tồn tại")

    await _require_department(session, data.department_id)
    target_department_ids = _normalize_assigned_department_ids(
        owner_department_id=data.department_id,
        assigned_department_ids=data.assigned_department_ids,
    )
    await _require_departments(session, target_department_ids)
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
        probation_legal_group=data.probation_legal_group,
    )
    session.add(pos)
    await session.flush()
    await _sync_position_department_mappings(
        session,
        pos_id=pos.id,
        target_department_ids=target_department_ids,
    )

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
    old_department_id = pos.department_id
    current_mapping_ids = await _get_active_mapping_department_ids(session, pos_id=pos.id)
    target_department_id = pos.department_id
    owner_department_changed = False

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
        target_department_id = data.department_id
        owner_department_changed = data.department_id != old_department_id
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
    if "probation_legal_group" in provided: pos.probation_legal_group = data.probation_legal_group
    if "is_active"          in provided and data.is_active is not None: pos.is_active = data.is_active

    if "assigned_department_ids" in provided:
        target_department_ids = _normalize_assigned_department_ids(
            owner_department_id=target_department_id,
            assigned_department_ids=data.assigned_department_ids,
        )
    elif owner_department_changed:
        target_department_ids = _normalize_assigned_department_ids(
            owner_department_id=target_department_id,
            assigned_department_ids=[dept_id for dept_id in current_mapping_ids if dept_id != old_department_id],
        )
    else:
        target_department_ids = _normalize_assigned_department_ids(
            owner_department_id=target_department_id,
            assigned_department_ids=current_mapping_ids,
        )

    await _require_departments(session, target_department_ids)
    await _sync_position_department_mappings(
        session,
        pos_id=pos.id,
        target_department_ids=target_department_ids,
    )

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
    # Soft delete — không xóa khỏi DB
    pos.soft_delete()
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
    *,
    allowed_department_ids: Optional[list[int]] = None,
) -> JobPositionAttachment:
    await _ensure_position_in_department_scope(
        session,
        pos_id=pos_id,
        allowed_department_ids=allowed_department_ids,
    )
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
