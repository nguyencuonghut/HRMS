"""Role service — CRUD vai trò và phân quyền."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Permission, Role, RolePermission
from app.schemas.role import RoleCreate, RoleUpdate


async def get_role_by_id(session: AsyncSession, role_id: int) -> Optional[Role]:
    return await session.get(Role, role_id)


async def get_role_by_code(session: AsyncSession, code: str) -> Optional[Role]:
    result = await session.execute(select(Role).where(Role.code == code))
    return result.scalar_one_or_none()


async def list_roles(session: AsyncSession) -> list[tuple[Role, int]]:
    """Trả (role, permission_count) cho tất cả roles."""
    result = await session.execute(
        select(Role, func.count(RolePermission.permission_id).label("perm_count"))
        .outerjoin(RolePermission, RolePermission.role_id == Role.id)
        .group_by(Role.id)
        .order_by(Role.id)
    )
    return result.all()


async def get_permissions_for_role(
    session: AsyncSession, role_id: int
) -> list[Permission]:
    result = await session.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.module, Permission.action)
    )
    return list(result.scalars().all())


async def list_all_permissions(session: AsyncSession) -> list[Permission]:
    result = await session.execute(
        select(Permission).order_by(Permission.module, Permission.action)
    )
    return list(result.scalars().all())


async def create_role(session: AsyncSession, data: RoleCreate) -> Role:
    role = Role(
        code=data.code,
        name=data.name,
        description=data.description,
        is_system=False,
    )
    session.add(role)
    await session.flush()
    return role


async def update_role(
    session: AsyncSession, role: Role, data: RoleUpdate
) -> Role:
    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    session.add(role)
    return role


async def delete_role(session: AsyncSession, role: Role) -> None:
    await session.delete(role)


async def replace_permissions(
    session: AsyncSession, role_id: int, permission_ids: list[int]
) -> list[Permission]:
    """Xóa toàn bộ permissions hiện tại của role và thay bằng danh sách mới."""
    await session.execute(
        delete(RolePermission).where(RolePermission.role_id == role_id)
    )
    for pid in permission_ids:
        session.add(RolePermission(role_id=role_id, permission_id=pid))
    await session.flush()
    return await get_permissions_for_role(session, role_id)
