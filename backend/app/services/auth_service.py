"""Auth service — xác thực người dùng, phân quyền, audit log."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.core.config import settings
from app.models.auth import AuditLog, Permission, Role, RolePermission, User, UserRole

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 30 * 60
LOGIN_RATE_LIMIT_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60
_TOKEN_BLACKLIST_PREFIX = "token:blacklist:"
_LOGIN_FAILED_PREFIX = "login_failed:"
_LOGIN_RATE_PREFIX = "login_rate:"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def get_redis() -> redis.Redis:
    return redis.from_url(settings.effective_redis_url, decode_responses=True)


def _login_failed_key(email: str) -> str:
    return f"{_LOGIN_FAILED_PREFIX}{email.strip().lower()}"


def _token_blacklist_key(jti: str) -> str:
    return f"{_TOKEN_BLACKLIST_PREFIX}{jti}"


def _login_rate_key(client_ip: str) -> str:
    return f"{_LOGIN_RATE_PREFIX}{client_ip}"


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


async def check_login_allowed(email: str) -> None:
    client = await get_redis()
    count = await client.get(_login_failed_key(email))
    if count and int(count) >= MAX_FAILED_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Tài khoản tạm khóa 30 phút do quá nhiều lần đăng nhập sai",
        )


async def record_failed_login(email: str) -> None:
    client = await get_redis()
    key = _login_failed_key(email)
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, LOCKOUT_SECONDS)


async def check_login_rate_limit(client_ip: str) -> None:
    client = await get_redis()
    count = await client.get(_login_rate_key(client_ip))
    if count and int(count) >= LOGIN_RATE_LIMIT_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau.",
            headers={"Retry-After": str(LOGIN_RATE_LIMIT_WINDOW_SECONDS)},
        )


async def record_login_rate_limit(client_ip: str) -> None:
    client = await get_redis()
    key = _login_rate_key(client_ip)
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, LOGIN_RATE_LIMIT_WINDOW_SECONDS)


async def clear_failed_login(email: str) -> None:
    client = await get_redis()
    await client.delete(_login_failed_key(email))


async def blacklist_token(jti: str, expires_at: datetime) -> None:
    ttl = int((expires_at - _utcnow()).total_seconds())
    if ttl <= 0:
        return
    client = await get_redis()
    await client.setex(_token_blacklist_key(jti), ttl, "1")


async def is_token_blacklisted(jti: str) -> bool:
    client = await get_redis()
    return bool(await client.exists(_token_blacklist_key(jti)))


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
