from __future__ import annotations

from typing import Iterable, Optional

import sqlalchemy as sa
from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.employee import Employee
from app.models.employee_job import EmployeeJobRecord
from app.models.leave_record import LeaveRecord
from app.models.org import Department
from app.models.performance import EmployeeKpiMonthly, EmployeeYearlyReview
from app.models.reward import EmployeeReward
from app.models.discipline import EmployeeDiscipline

EMPLOYEE_SCOPE_PERMISSIONS = ("employees:view", "employees:edit", "employees:delete")
CONTRACT_SCOPE_PERMISSIONS = ("contracts:view", "contracts:create", "contracts:edit", "contracts:delete")
LEAVE_SCOPE_PERMISSIONS = ("leaves:view", "leaves:create", "leaves:edit", "leaves:delete")
PERFORMANCE_SCOPE_PERMISSIONS = (
    "performance:view",
    "performance:create",
    "performance:edit",
    "performance:delete",
)
REWARD_SCOPE_PERMISSIONS = ("rewards:view", "rewards:create", "rewards:edit", "rewards:delete")
DISCIPLINE_SCOPE_PERMISSIONS = (
    "disciplines:view",
    "disciplines:create",
    "disciplines:edit",
    "disciplines:delete",
)
REPORT_SCOPE_PERMISSIONS = ("reports:view", "reports:export")


async def _expand_department_scope(
    session: AsyncSession,
    department_ids: Iterable[int],
) -> set[int]:
    root_ids = sorted({int(department_id) for department_id in department_ids})
    if not root_ids:
        return set()

    rows = await session.execute(
        sa.text(
            """
            WITH RECURSIVE subtree AS (
                SELECT id
                FROM departments
                WHERE id = ANY(:root_ids)
                  AND deleted_at IS NULL
                  AND is_active = TRUE
                UNION ALL
                SELECT d.id
                FROM departments d
                JOIN subtree s ON d.parent_id = s.id
                WHERE d.deleted_at IS NULL
                  AND d.is_active = TRUE
            )
            SELECT DISTINCT id FROM subtree
            """
        ),
        {"root_ids": root_ids},
    )
    return {int(row[0]) for row in rows.fetchall()}


async def get_department_subtree_ids(
    session: AsyncSession,
    department_id: int | None,
) -> set[int] | None:
    if department_id is None:
        return None
    return await _expand_department_scope(session, [department_id])


async def get_allowed_department_ids(
    session: AsyncSession,
    user: User,
    *,
    permission_codes: Iterable[str],
) -> Optional[set[int]]:
    if user.is_superuser:
        return None

    permission_codes = tuple(dict.fromkeys(permission_codes))
    if not permission_codes:
        return set()

    rows = (
        await session.execute(
            select(
                Role.code.label("role_code"),
                UserRole.scope_type.label("scope_type"),
                UserRole.department_ids.label("department_ids"),
            )
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                UserRole.user_id == user.id,
                Permission.code.in_(permission_codes),
            )
        )
    ).all()

    if not rows:
        return set()

    scoped_root_ids: set[int] = set()
    for role_code, scope_type, department_ids in rows:
        if scope_type == "department" and department_ids:
            scoped_root_ids.update(int(department_id) for department_id in department_ids)
            continue

        return None

    if not scoped_root_ids:
        return set()

    return await _expand_department_scope(session, scoped_root_ids)


async def resolve_effective_department_scope_ids(
    session: AsyncSession,
    *,
    department_id: int | None,
    allowed_department_ids: Iterable[int] | None,
) -> set[int] | None:
    requested_scope_ids = await get_department_subtree_ids(session, department_id)
    if allowed_department_ids is None:
        return requested_scope_ids

    allowed_scope_ids = {int(item) for item in allowed_department_ids}
    if department_id is not None and department_id not in allowed_scope_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập dữ liệu phòng ban này",
        )

    if requested_scope_ids is None:
        return allowed_scope_ids
    return requested_scope_ids & allowed_scope_ids


async def intersect_allowed_department_ids(
    session: AsyncSession,
    user: User,
    *,
    permission_groups: Iterable[Iterable[str]],
    department_id: int | None = None,
) -> set[int] | None:
    requested_scope_ids = await get_department_subtree_ids(session, department_id)

    effective_scope_ids: set[int] | None = None
    for permission_codes in permission_groups:
        allowed_ids = await get_allowed_department_ids(
            session,
            user,
            permission_codes=permission_codes,
        )
        scoped_ids = allowed_ids
        if requested_scope_ids is not None:
            if scoped_ids is None:
                scoped_ids = set(requested_scope_ids)
            else:
                scoped_ids = set(scoped_ids) & requested_scope_ids

        if effective_scope_ids is None:
            effective_scope_ids = None if scoped_ids is None else set(scoped_ids)
            continue

        if scoped_ids is None:
            continue
        effective_scope_ids &= set(scoped_ids)

    return effective_scope_ids


async def ensure_department_access(
    session: AsyncSession,
    user: User,
    *,
    permission_codes: Iterable[str],
    department_id: int,
) -> Optional[set[int]]:
    allowed_ids = await get_allowed_department_ids(
        session,
        user,
        permission_codes=permission_codes,
    )
    if allowed_ids is not None and department_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập dữ liệu phòng ban này",
        )
    return allowed_ids


async def ensure_employee_access(
    session: AsyncSession,
    user: User,
    *,
    permission_codes: Iterable[str],
    employee_id: int,
) -> Optional[set[int]]:
    allowed_ids = await get_allowed_department_ids(
        session,
        user,
        permission_codes=permission_codes,
    )
    if allowed_ids is None:
        return None
    if not allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập dữ liệu nhân sự thuộc phòng ban này",
        )

    row = (
        await session.execute(
            select(EmployeeJobRecord.department_id)
            .select_from(Employee)
            .join(
                EmployeeJobRecord,
                and_(
                    EmployeeJobRecord.employee_id == Employee.id,
                    EmployeeJobRecord.is_current == True,  # noqa: E712
                ),
            )
            .where(Employee.id == employee_id)
        )
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy nhân viên",
        )

    department_id = row[0]
    if department_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập dữ liệu nhân sự thuộc phòng ban này",
        )
    return allowed_ids


async def _ensure_related_employee_access(
    session: AsyncSession,
    user: User,
    *,
    permission_codes: Iterable[str],
    employee_stmt,
    not_found_detail: str,
    forbidden_detail: str,
) -> Optional[set[int]]:
    allowed_ids = await get_allowed_department_ids(
        session,
        user,
        permission_codes=permission_codes,
    )
    if allowed_ids is None:
        return None
    if not allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=forbidden_detail,
        )

    employee_id = (await session.execute(employee_stmt)).scalar_one_or_none()
    if employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )

    await ensure_employee_access(
        session,
        user,
        permission_codes=permission_codes,
        employee_id=employee_id,
    )
    return allowed_ids


async def ensure_leave_record_access(
    session: AsyncSession,
    user: User,
    *,
    permission_codes: Iterable[str] = LEAVE_SCOPE_PERMISSIONS,
    record_id: int,
) -> Optional[set[int]]:
    return await _ensure_related_employee_access(
        session,
        user,
        permission_codes=permission_codes,
        employee_stmt=select(LeaveRecord.employee_id).where(LeaveRecord.id == record_id),
        not_found_detail="Không tìm thấy bản ghi nghỉ phép",
        forbidden_detail="Không có quyền truy cập dữ liệu nghỉ phép thuộc phòng ban này",
    )


async def ensure_kpi_access(
    session: AsyncSession,
    user: User,
    *,
    permission_codes: Iterable[str] = PERFORMANCE_SCOPE_PERMISSIONS,
    kpi_id: int,
) -> Optional[set[int]]:
    return await _ensure_related_employee_access(
        session,
        user,
        permission_codes=permission_codes,
        employee_stmt=select(EmployeeKpiMonthly.employee_id).where(EmployeeKpiMonthly.id == kpi_id),
        not_found_detail="Không tìm thấy bản ghi KPI",
        forbidden_detail="Không có quyền truy cập dữ liệu KPI thuộc phòng ban này",
    )


async def ensure_yearly_review_access(
    session: AsyncSession,
    user: User,
    *,
    permission_codes: Iterable[str] = PERFORMANCE_SCOPE_PERMISSIONS,
    review_id: int,
) -> Optional[set[int]]:
    return await _ensure_related_employee_access(
        session,
        user,
        permission_codes=permission_codes,
        employee_stmt=select(EmployeeYearlyReview.employee_id).where(EmployeeYearlyReview.id == review_id),
        not_found_detail="Không tìm thấy bản ghi đánh giá",
        forbidden_detail="Không có quyền truy cập dữ liệu đánh giá thuộc phòng ban này",
    )


async def ensure_reward_access(
    session: AsyncSession,
    user: User,
    *,
    permission_codes: Iterable[str] = REWARD_SCOPE_PERMISSIONS,
    reward_id: int,
) -> Optional[set[int]]:
    return await _ensure_related_employee_access(
        session,
        user,
        permission_codes=permission_codes,
        employee_stmt=select(EmployeeReward.employee_id).where(EmployeeReward.id == reward_id),
        not_found_detail="Không tìm thấy quyết định khen thưởng",
        forbidden_detail="Không có quyền truy cập dữ liệu khen thưởng thuộc phòng ban này",
    )


async def ensure_discipline_access(
    session: AsyncSession,
    user: User,
    *,
    permission_codes: Iterable[str] = DISCIPLINE_SCOPE_PERMISSIONS,
    discipline_id: int,
) -> Optional[set[int]]:
    return await _ensure_related_employee_access(
        session,
        user,
        permission_codes=permission_codes,
        employee_stmt=select(EmployeeDiscipline.employee_id).where(EmployeeDiscipline.id == discipline_id),
        not_found_detail="Không tìm thấy quyết định kỷ luật",
        forbidden_detail="Không có quyền truy cập dữ liệu kỷ luật thuộc phòng ban này",
    )


async def list_visible_departments(
    session: AsyncSession,
    allowed_department_ids: Optional[set[int]],
) -> list[Department]:
    stmt = select(Department).where(Department.deleted_at.is_(None))
    if allowed_department_ids is not None:
        if not allowed_department_ids:
            return []
        stmt = stmt.where(Department.id.in_(allowed_department_ids))
    return list((await session.execute(stmt)).scalars().all())
