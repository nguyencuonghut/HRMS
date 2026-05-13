"""User service — CRUD tài khoản người dùng."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.auth import Role, User, UserRole
from app.schemas.user import UserCreate, UserUpdate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    return await session.get(User, user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def list_users(
    session: AsyncSession,
    *,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[User], int]:
    q = select(User)
    if search:
        pattern = f"%{search}%"
        q = q.where(
            User.full_name.ilike(pattern) | User.email.ilike(pattern)
        )
    if is_active is not None:
        q = q.where(User.is_active == is_active)

    total = (await session.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar_one()

    users = (await session.execute(
        q.order_by(User.created_at.desc()).offset(skip).limit(limit)
    )).scalars().all()

    return list(users), total


async def create_user(session: AsyncSession, data: UserCreate) -> User:
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        is_active=data.is_active,
        is_superuser=data.is_superuser,
    )
    session.add(user)
    await session.flush()
    return user


async def update_user(
    session: AsyncSession, user: User, data: UserUpdate
) -> User:
    if data.email is not None:
        user.email = data.email
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.is_active is not None:
        user.is_active = data.is_active
    user.updated_at = _utcnow()
    session.add(user)
    return user


async def reset_password(
    session: AsyncSession, user: User, new_password: str
) -> None:
    user.hashed_password = hash_password(new_password)
    user.updated_at = _utcnow()
    session.add(user)


async def get_roles_for_user(
    session: AsyncSession, user_id: int
) -> list[tuple[Role, UserRole]]:
    result = await session.execute(
        select(Role, UserRole)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return result.all()


async def assign_role(
    session: AsyncSession,
    user_id: int,
    role_id: int,
    scope_type: Optional[str] = None,
    department_ids: Optional[list[int]] = None,
) -> UserRole:
    existing = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
    )
    ur = existing.scalar_one_or_none()
    if ur:
        ur.scope_type = scope_type
        ur.department_ids = department_ids
    else:
        ur = UserRole(
            user_id=user_id,
            role_id=role_id,
            scope_type=scope_type,
            department_ids=department_ids,
        )
    session.add(ur)
    await session.flush()
    return ur


async def remove_role(
    session: AsyncSession, user_id: int, role_id: int
) -> bool:
    result = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
    )
    ur = result.scalar_one_or_none()
    if not ur:
        return False
    await session.delete(ur)
    return True
