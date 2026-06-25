from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_pattern, cache_get, cache_set
from app.core.security import create_signed_token
from app.models.employee_attachment import EmployeeAttachment
from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department, DepartmentHead, DepartmentJobPosition, JobPosition, JobTitle, OrgChangeLog
from app.schemas.department import (
    DepartmentBrief,
    DepartmentCreate,
    DepartmentDetailRead,
    DepartmentOrgChartHeadRead,
    DepartmentOrgChartNodeRead,
    DepartmentDetailSummary,
    DepartmentDirectEmployeeItem,
    DepartmentRead,
    DepartmentTreeNode,
    DepartmentUpdate,
)
from app.services import employee_code_service

_CACHE_TTL = 3600          # 1 giờ
_CACHE_KEY  = "cache:departments:{suffix}"
_PREVIEW_TOKEN_TTL_SECONDS = 300


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_dict(dept: Department) -> dict:
    return {
        "id":         dept.id,
        "code":       dept.code,
        "name":       dept.name,
        "short_name": dept.short_name,
        "display_prefix": dept.display_prefix,
        "parent_id":  dept.parent_id,
        "dept_type":  dept.dept_type,
        "order_no":   dept.order_no,
        "is_active":  dept.is_active,
    }


async def _log(
    session: AsyncSession,
    dept: Department,
    action: str,
    old_data: Optional[dict],
    new_data: Optional[dict],
    changed_by: Optional[int],
) -> None:
    session.add(OrgChangeLog(
        entity_type="department",
        entity_id=dept.id,
        entity_name=dept.name,
        action=action,
        changed_by=changed_by,
        old_data=old_data,
        new_data=new_data,
    ))


async def _get_descendant_ids(session: AsyncSession, dept_id: int) -> set[int]:
    """Trả về tập id tất cả đơn vị con cháu (không bao gồm bản thân)."""
    result = await session.execute(
        text("""
            WITH RECURSIVE subtree AS (
                SELECT id FROM departments WHERE parent_id = :dept_id
                UNION ALL
                SELECT d.id FROM departments d JOIN subtree s ON d.parent_id = s.id
            )
            SELECT id FROM subtree
        """),
        {"dept_id": dept_id},
    )
    return {row[0] for row in result.fetchall()}


async def _get_subtree_ids(session: AsyncSession, dept_id: int) -> set[int]:
    result = await session.execute(
        text(
            """
            WITH RECURSIVE subtree AS (
                SELECT id
                FROM departments
                WHERE id = :dept_id AND deleted_at IS NULL
                UNION ALL
                SELECT d.id
                FROM departments d
                JOIN subtree s ON d.parent_id = s.id
                WHERE d.deleted_at IS NULL
            )
            SELECT id FROM subtree
            """
        ),
        {"dept_id": dept_id},
    )
    return {row[0] for row in result.fetchall()}


async def _invalidate_cache() -> None:
    await cache_delete_pattern("cache:departments:*")


def _build_attachment_preview_url(*, employee_id: int, attachment_id: int) -> str:
    token = create_signed_token(
        "employee-file-preview",
        token_type="preview",
        expires=timedelta(seconds=_PREVIEW_TOKEN_TTL_SECONDS),
        extra_claims={
            "scope": "employee-file-preview",
            "employee_id": employee_id,
            "resource_id": attachment_id,
            "resource_kind": "attachment",
        },
    )
    return f"/api/v1/employees/{employee_id}/attachments/{attachment_id}/preview?token={token}"


def _avatar_initials(full_name: str) -> str:
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:1].upper()
    return f"{parts[0][:1]}{parts[-1][:1]}".upper()


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_by_id(
    session: AsyncSession,
    dept_id: int,
    *,
    allowed_department_ids: Optional[Sequence[int]] = None,
) -> Department:
    result = await session.execute(
        _apply_department_scope(
            select(Department).where(Department.id == dept_id, Department.deleted_at.is_(None)),
            allowed_department_ids,
        )
    )
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng/ban")
    return dept


def _apply_department_scope(
    stmt,
    allowed_department_ids: Optional[Sequence[int]],
):
    if allowed_department_ids is None:
        return stmt
    if not allowed_department_ids:
        return stmt.where(text("1 = 0"))
    return stmt.where(Department.id.in_(allowed_department_ids))


async def _build_org_chart(
    session: AsyncSession,
    *,
    root_id: int,
    subtree_ids: set[int],
) -> DepartmentOrgChartNodeRead:
    departments = list(
        (
            await session.execute(
                select(Department)
                .where(
                    Department.id.in_(subtree_ids),
                    Department.deleted_at.is_(None),
                )
                .order_by(Department.order_no.asc(), Department.id.asc())
            )
        ).scalars().all()
    )
    department_map = {department.id: department for department in departments}
    children_map: dict[int | None, list[Department]] = {}
    for department in departments:
        children_map.setdefault(department.parent_id, []).append(department)

    direct_headcount_rows = (
        await session.execute(
            select(
                EmployeeJobRecord.department_id,
                func.count(Employee.id.distinct()),
            )
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
                EmployeeJobRecord.department_id.in_(subtree_ids),
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
            .group_by(EmployeeJobRecord.department_id)
        )
    ).all()
    direct_headcounts = {department_id: int(count or 0) for department_id, count in direct_headcount_rows}

    avatar_ranked = (
        select(
            EmployeeAttachment.employee_id.label("employee_id"),
            EmployeeAttachment.id.label("attachment_id"),
            func.row_number()
            .over(
                partition_by=EmployeeAttachment.employee_id,
                order_by=(
                    EmployeeAttachment.uploaded_at.desc(),
                    EmployeeAttachment.id.desc(),
                ),
            )
            .label("row_no"),
        )
        .where(EmployeeAttachment.document_type == "avatar")
        .subquery()
    )

    head_rows = (
        await session.execute(
            select(
                DepartmentHead.department_id.label("department_id"),
                DepartmentHead.employee_id.label("employee_id"),
                DepartmentHead.head_role_label.label("head_role_label"),
                Employee.full_name.label("full_name"),
                Employee.status.label("status"),
                Department.id.label("current_department_id"),
                Department.name.label("current_department_name"),
                JobPosition.name.label("current_job_position_name"),
                JobTitle.name.label("current_job_title_name"),
                avatar_ranked.c.attachment_id.label("avatar_attachment_id"),
            )
            .select_from(DepartmentHead)
            .join(Employee, Employee.id == DepartmentHead.employee_id)
            .outerjoin(
                EmployeeJobRecord,
                and_(
                    EmployeeJobRecord.employee_id == Employee.id,
                    EmployeeJobRecord.is_current == True,  # noqa: E712
                ),
            )
            .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
            .outerjoin(JobPosition, JobPosition.id == EmployeeJobRecord.job_position_id)
            .outerjoin(JobTitle, JobTitle.id == EmployeeJobRecord.job_title_id)
            .outerjoin(
                avatar_ranked,
                and_(
                    avatar_ranked.c.employee_id == Employee.id,
                    avatar_ranked.c.row_no == 1,
                ),
            )
            .where(
                DepartmentHead.department_id.in_(subtree_ids),
                DepartmentHead.is_current == True,  # noqa: E712
            )
        )
    ).all()

    head_employee_ids = [row.employee_id for row in head_rows]
    display_codes: dict[int, str] = {}
    if head_employee_ids:
        head_employees = list(
            (
                await session.execute(
                    select(Employee).where(Employee.id.in_(head_employee_ids))
                )
            ).scalars().all()
        )
        display_codes = await employee_code_service.batch_build_employee_display_codes(session, head_employees)

    head_map: dict[int, DepartmentOrgChartHeadRead] = {}
    for row in head_rows:
        display_position_label = (
            (row.head_role_label or "").strip()
            or row.current_job_position_name
            or row.current_job_title_name
            or "Người phụ trách"
        )
        avatar_preview_url = None
        if row.avatar_attachment_id is not None:
            avatar_preview_url = _build_attachment_preview_url(
                employee_id=row.employee_id,
                attachment_id=row.avatar_attachment_id,
            )
        head_map[row.department_id] = DepartmentOrgChartHeadRead(
            employee_id=row.employee_id,
            display_code=display_codes.get(row.employee_id, str(row.employee_id)),
            full_name=row.full_name,
            status=row.status,
            display_position_label=display_position_label,
            current_department_name=row.current_department_name,
            current_job_position_name=row.current_job_position_name,
            current_job_title_name=row.current_job_title_name,
            is_cross_department_assignment=(
                row.current_department_id is not None and row.current_department_id != row.department_id
            ),
            avatar_preview_url=avatar_preview_url,
            avatar_initials=_avatar_initials(row.full_name),
        )

    total_headcounts: dict[int, int] = {}

    def build_node(department: Department) -> DepartmentOrgChartNodeRead:
        child_nodes = [build_node(child) for child in children_map.get(department.id, [])]
        total_headcount = direct_headcounts.get(department.id, 0) + sum(
            child.total_headcount for child in child_nodes
        )
        total_headcounts[department.id] = total_headcount
        return DepartmentOrgChartNodeRead(
            key=f"dept-{department.id}",
            department_id=department.id,
            department_code=department.code,
            department_name=department.name,
            dept_type=department.dept_type,
            dept_type_label=DepartmentRead.model_validate(department).dept_type_label,
            direct_headcount=direct_headcounts.get(department.id, 0),
            total_headcount=total_headcount,
            head=head_map.get(department.id),
            children=child_nodes,
        )

    root_department = department_map.get(root_id)
    if root_department is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng/ban")
    return build_node(root_department)


async def get_detail(
    session: AsyncSession,
    dept_id: int,
    *,
    allowed_department_ids: Optional[Sequence[int]] = None,
) -> DepartmentDetailRead:
    dept = await get_by_id(session, dept_id, allowed_department_ids=allowed_department_ids)

    parent = None
    if dept.parent_id is not None:
        parent_row = await session.execute(
            select(Department).where(
                Department.id == dept.parent_id,
                Department.deleted_at.is_(None),
            )
        )
        parent_dept = parent_row.scalar_one_or_none()
        if parent_dept is not None:
            parent = DepartmentBrief.model_validate(parent_dept)

    subtree_ids = await _get_subtree_ids(session, dept_id)
    org_chart = await _build_org_chart(session, root_id=dept_id, subtree_ids=subtree_ids)

    direct_child_count = (
        await session.execute(
            select(func.count())
            .select_from(Department)
            .where(
                Department.parent_id == dept_id,
                Department.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    job_position_count = (
        await session.execute(
            select(func.count())
            .select_from(DepartmentJobPosition)
            .where(
                DepartmentJobPosition.department_id == dept_id,
                DepartmentJobPosition.is_active == True,  # noqa: E712
            )
        )
    ).scalar_one()

    direct_headcount = (
        await session.execute(
            select(func.count(Employee.id.distinct()))
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
                EmployeeJobRecord.department_id == dept_id,
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
        )
    ).scalar_one()

    total_headcount = 0
    if subtree_ids:
        total_headcount = (
            await session.execute(
                select(func.count(Employee.id.distinct()))
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
                    EmployeeJobRecord.department_id.in_(subtree_ids),
                    EmployeeJobRecord.is_current == True,  # noqa: E712
                )
            )
        ).scalar_one()

    direct_rows = (
        await session.execute(
            select(
                Employee,
                Department,
                JobTitle.name.label("job_title_name"),
                JobPosition.name.label("job_position_name"),
            )
            .select_from(EmployeeJobRecord)
            .join(
                Employee,
                and_(
                    Employee.id == EmployeeJobRecord.employee_id,
                    Employee.is_active == True,  # noqa: E712
                    Employee.status != "resigned",
                ),
            )
            .join(Department, Department.id == EmployeeJobRecord.department_id)
            .outerjoin(JobTitle, JobTitle.id == EmployeeJobRecord.job_title_id)
            .outerjoin(JobPosition, JobPosition.id == EmployeeJobRecord.job_position_id)
            .where(
                EmployeeJobRecord.department_id.in_(subtree_ids),
                EmployeeJobRecord.is_current == True,  # noqa: E712
            )
            .order_by(
                Department.order_no.asc(),
                Department.id.asc(),
                Employee.employee_seq.asc(),
                Employee.id.asc(),
            )
        )
    ).all()

    employees = [row[0] for row in direct_rows]
    display_codes = await employee_code_service.batch_build_employee_display_codes(session, employees)
    direct_employees = [
        DepartmentDirectEmployeeItem(
            id=employee.id,
            display_code=display_codes.get(employee.id, str(employee.employee_seq)),
            full_name=employee.full_name,
            status=employee.status,
            start_date=employee.start_date,
            department_id=department.id,
            department_code=department.code,
            department_name=department.name,
            department_parent_id=department.parent_id,
            department_dept_type=department.dept_type,
            department_dept_type_label=DepartmentRead.model_validate(department).dept_type_label,
            job_title_name=job_title_name,
            job_position_name=job_position_name,
        )
        for employee, department, job_title_name, job_position_name in direct_rows
    ]

    return DepartmentDetailRead(
        department=DepartmentRead.model_validate(dept),
        parent=parent,
        summary=DepartmentDetailSummary(
            direct_headcount=int(direct_headcount or 0),
            total_headcount=int(total_headcount or 0),
            direct_child_count=int(direct_child_count or 0),
            job_position_count=int(job_position_count or 0),
        ),
        org_chart=org_chart,
        direct_employees=direct_employees,
    )


async def get_list(
    session: AsyncSession,
    is_active: Optional[bool] = None,
    allowed_department_ids: Optional[Sequence[int]] = None,
) -> list[Department]:
    if allowed_department_ids is not None:
        q = _apply_department_scope(
            select(Department).where(Department.deleted_at.is_(None)),
            allowed_department_ids,
        )
        if is_active is not None:
            q = q.where(Department.is_active == is_active)
        q = q.order_by(Department.order_no, Department.name)
        result = await session.execute(q)
        return list(result.scalars().all())

    cache_key = _CACHE_KEY.format(suffix=f"list:{is_active}")
    cached = await cache_get(cache_key)
    if cached is not None:
        return [Department.model_validate(d) for d in cached]

    q = select(Department).where(Department.deleted_at.is_(None))
    if is_active is not None:
        q = q.where(Department.is_active == is_active)
    q = q.order_by(Department.order_no, Department.name)
    result = await session.execute(q)
    rows = list(result.scalars().all())

    await cache_set(cache_key, [_to_dict(r) for r in rows], _CACHE_TTL)
    return rows


async def get_tree(
    session: AsyncSession,
    is_active: Optional[bool] = None,
    allowed_department_ids: Optional[Sequence[int]] = None,
) -> list[DepartmentTreeNode]:
    rows = await get_list(session, is_active, allowed_department_ids=allowed_department_ids)

    # Build map id → node
    nodes: dict[int, DepartmentTreeNode] = {
        row.id: DepartmentTreeNode.model_validate(row) for row in rows
    }

    roots: list[DepartmentTreeNode] = []
    for node in nodes.values():
        if node.parent_id is None or node.parent_id not in nodes:
            roots.append(node)
        else:
            nodes[node.parent_id].children.append(node)

    # Sắp xếp mỗi cấp theo order_no rồi name
    def _sort(nodes_list: list[DepartmentTreeNode]) -> None:
        nodes_list.sort(key=lambda n: (n.order_no, n.name))
        for n in nodes_list:
            _sort(n.children)

    _sort(roots)
    return roots


async def create(
    session: AsyncSession,
    data: DepartmentCreate,
    changed_by: Optional[int] = None,
) -> Department:
    # Kiểm tra mã trùng (chỉ kiểm tra các phòng ban chưa bị xóa mềm)
    existing = await session.execute(
        select(Department).where(Department.code == data.code, Department.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Mã phòng/ban '{data.code}' đã tồn tại",
        )

    # Kiểm tra phòng/ban cha tồn tại (và chưa bị xóa mềm)
    if data.parent_id is not None:
        parent = await session.execute(
            select(Department).where(Department.id == data.parent_id, Department.deleted_at.is_(None))
        )
        if not parent.scalar_one_or_none():
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phòng/ban cha",
            )

    dept = Department(
        code=data.code,
        name=data.name,
        short_name=data.short_name,
        display_prefix=data.display_prefix,
        parent_id=data.parent_id,
        dept_type=data.dept_type.value,
        order_no=data.order_no,
    )
    session.add(dept)
    await session.flush()  # lấy id trước khi log

    await _log(session, dept, "create", None, _to_dict(dept), changed_by)
    await session.commit()
    await session.refresh(dept)
    await _invalidate_cache()
    return dept


async def update(
    session: AsyncSession,
    dept_id: int,
    data: DepartmentUpdate,
    changed_by: Optional[int] = None,
) -> Department:
    dept = await get_by_id(session, dept_id)
    old_snapshot = _to_dict(dept)
    provided = data.model_fields_set

    if "name" in provided and data.name is not None:
        dept.name = data.name

    if "short_name" in provided:
        dept.short_name = data.short_name

    if "display_prefix" in provided:
        dept.display_prefix = data.display_prefix

    if "dept_type" in provided and data.dept_type is not None:
        dept.dept_type = data.dept_type.value

    if "order_no" in provided and data.order_no is not None:
        dept.order_no = data.order_no

    if "is_active" in provided and data.is_active is not None:
        dept.is_active = data.is_active

    if "parent_id" in provided:
        new_parent_id = data.parent_id
        if new_parent_id is not None:
            # Không được tự làm cha của chính mình
            if new_parent_id == dept_id:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Không thể chuyển phòng/ban thành con của chính nó",
                )
            # Không được chuyển thành con của một đơn vị con cháu (tạo vòng lặp)
            descendants = await _get_descendant_ids(session, dept_id)
            if new_parent_id in descendants:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Không thể chuyển phòng/ban thành con của đơn vị trực thuộc nó",
                )
            # Kiểm tra parent tồn tại và chưa bị xóa mềm
            parent = await session.execute(
                select(Department).where(Department.id == new_parent_id, Department.deleted_at.is_(None))
            )
            if not parent.scalar_one_or_none():
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy phòng/ban cha",
                )
        dept.parent_id = new_parent_id

    dept.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await _log(session, dept, "update", old_snapshot, _to_dict(dept), changed_by)
    await session.commit()
    await session.refresh(dept)
    await _invalidate_cache()
    return dept


async def delete(
    session: AsyncSession,
    dept_id: int,
    changed_by: Optional[int] = None,
) -> dict:
    dept = await get_by_id(session, dept_id)

    # Kiểm tra còn đơn vị con chưa bị xóa mềm
    child_count_result = await session.execute(
        select(func.count()).where(Department.parent_id == dept_id, Department.deleted_at.is_(None))
    )
    child_count = child_count_result.scalar_one()
    if child_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Không thể xóa: phòng/ban này còn {child_count} đơn vị con",
        )

    # Kiểm tra còn vị trí công việc chưa bị xóa mềm
    pos_count_result = await session.execute(
        select(func.count())
        .select_from(DepartmentJobPosition)
        .join(JobPosition, JobPosition.id == DepartmentJobPosition.job_position_id)
        .where(
            DepartmentJobPosition.department_id == dept_id,
            DepartmentJobPosition.is_active == True,  # noqa: E712
            JobPosition.deleted_at.is_(None),
        )
    )
    pos_count = pos_count_result.scalar_one()
    if pos_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Không thể xóa: phòng/ban này còn {pos_count} vị trí công việc",
        )

    old_snapshot = _to_dict(dept)
    dept_name = dept.name

    await _log(session, dept, "delete", old_snapshot, None, changed_by)
    # Soft delete — không xóa khỏi DB
    dept.soft_delete()
    await session.commit()
    await _invalidate_cache()

    return {"message": f"Đã xóa phòng/ban '{dept_name}' thành công"}
