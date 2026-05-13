"""Auth service — xác thực người dùng, phân quyền, audit log."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.auth import AuditLog, Permission, Role, RolePermission, User, UserRole


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def authenticate_user(
    session: AsyncSession, email: str, password: str
) -> Optional[User]:
    user = await get_user_by_email(session, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_user_roles(session: AsyncSession, user_id: int) -> list[str]:
    result = await session.execute(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return [row[0] for row in result.fetchall()]


async def get_user_permissions(session: AsyncSession, user_id: int) -> set[str]:
    """Trả tập permission codes của user. is_superuser check nằm ở deps.py."""
    result = await session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
    )
    return {row[0] for row in result.fetchall()}


async def update_last_login(session: AsyncSession, user: User) -> None:
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(user)


async def log_audit(
    session: AsyncSession,
    user_id: Optional[int],
    action: str,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    entity_name: Optional[str] = None,
    old_data: Optional[dict] = None,
    new_data: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    session.add(AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        old_data=old_data,
        new_data=new_data,
        ip_address=ip_address,
        user_agent=user_agent,
    ))
