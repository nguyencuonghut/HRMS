"""FastAPI dependencies dùng chung: xác thực và kiểm tra quyền."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decode_token
from app.models.auth import User
from app.services import auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin đăng nhập",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        email: str = payload.get("sub", "")
        jti: str = payload.get("jti", "")
        if not email or not jti:
            raise exc
    except JWTError:
        raise exc

    if await auth_service.is_token_blacklisted(jti):
        raise exc

    user = await auth_service.get_user_by_email(session, email)
    if not user:
        raise exc
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản đã bị vô hiệu hóa",
        )
    return user


def require_permission(*perms: str):
    """Trả Depends kiểm tra user có ít nhất 1 trong các permission được liệt kê.

    is_superuser bypass mọi permission check.
    """
    async def _dependency(
        user: User = Depends(get_current_active_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        if user.is_superuser:
            return user
        user_perms = await auth_service.get_user_permissions(session, user.id)
        if not any(p in user_perms for p in perms):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền thực hiện thao tác này",
            )
        return user
    return Depends(_dependency)


_HR_ROLES = frozenset({"admin", "hr_manager", "hr_officer"})


def require_admin_or_hr():
    """Depends: chỉ cho phép superuser hoặc user thuộc vai trò admin/HR."""
    async def _dependency(
        user: User = Depends(get_current_active_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        if user.is_superuser:
            return user
        roles = await auth_service.get_user_roles(session, user.id)
        if not any(r in _HR_ROLES for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Admin hoặc HR mới có quyền xác nhận báo cáo",
            )
        return user
    return Depends(_dependency)
