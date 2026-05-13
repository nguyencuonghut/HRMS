from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org import Department, OrgChangeLog
from app.schemas.department import DepartmentCreate, DepartmentTreeNode, DepartmentUpdate


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_dict(dept: Department) -> dict:
    return {
        "id":         dept.id,
        "code":       dept.code,
        "name":       dept.name,
        "short_name": dept.short_name,
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


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_by_id(session: AsyncSession, dept_id: int) -> Department:
    result = await session.execute(
        select(Department).where(Department.id == dept_id)
    )
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng/ban")
    return dept


async def get_list(
    session: AsyncSession,
    is_active: Optional[bool] = None,
) -> list[Department]:
    q = select(Department)
    if is_active is not None:
        q = q.where(Department.is_active == is_active)
    q = q.order_by(Department.order_no, Department.name)
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_tree(
    session: AsyncSession,
    is_active: Optional[bool] = None,
) -> list[DepartmentTreeNode]:
    rows = await get_list(session, is_active)

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
    # Kiểm tra mã trùng
    existing = await session.execute(
        select(Department).where(Department.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Mã phòng/ban '{data.code}' đã tồn tại",
        )

    # Kiểm tra phòng/ban cha tồn tại
    if data.parent_id is not None:
        parent = await session.execute(
            select(Department).where(Department.id == data.parent_id)
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
        parent_id=data.parent_id,
        dept_type=data.dept_type.value,
        order_no=data.order_no,
    )
    session.add(dept)
    await session.flush()  # lấy id trước khi log

    await _log(session, dept, "create", None, _to_dict(dept), changed_by)
    await session.commit()
    await session.refresh(dept)
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
            # Kiểm tra parent tồn tại
            parent = await session.execute(
                select(Department).where(Department.id == new_parent_id)
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
    return dept


async def delete(
    session: AsyncSession,
    dept_id: int,
    changed_by: Optional[int] = None,
) -> dict:
    dept = await get_by_id(session, dept_id)

    # Kiểm tra còn đơn vị con
    child_count_result = await session.execute(
        select(func.count()).where(Department.parent_id == dept_id)
    )
    child_count = child_count_result.scalar_one()
    if child_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Không thể xóa: phòng/ban này còn {child_count} đơn vị con",
        )

    # Kiểm tra còn vị trí công việc
    pos_count_result = await session.execute(
        text("SELECT COUNT(*) FROM job_positions WHERE department_id = :dept_id"),
        {"dept_id": dept_id},
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
    await session.delete(dept)
    await session.commit()

    return {"message": f"Đã xóa phòng/ban '{dept_name}' thành công"}
