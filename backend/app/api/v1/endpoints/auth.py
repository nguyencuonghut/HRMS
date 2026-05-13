from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_active_user
from app.core.database import get_session
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.auth import User
from app.services import auth_service

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserMeResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    roles: list[str]
    permissions: list[str]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Đăng nhập")
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user = await auth_service.authenticate_user(session, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai email hoặc mật khẩu",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa",
        )

    roles = await auth_service.get_user_roles(session, user.id)
    access_token = create_access_token(
        user.email, extra_claims={"user_id": user.id, "roles": roles}
    )
    refresh_token = create_refresh_token(user.email)

    await auth_service.update_last_login(session, user)
    await auth_service.log_audit(
        session, user.id, "LOGIN",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse, summary="Làm mới access token")
async def refresh_token(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token không hợp lệ hoặc đã hết hạn",
    )
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise exc
        email: str = data.get("sub", "")
        if not email:
            raise exc
    except JWTError:
        raise exc

    user = await auth_service.get_user_by_email(session, email)
    if not user or not user.is_active:
        raise exc

    roles = await auth_service.get_user_roles(session, user.id)
    new_access = create_access_token(
        user.email, extra_claims={"user_id": user.id, "roles": roles}
    )
    new_refresh = create_refresh_token(user.email)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.get("/me", response_model=UserMeResponse, summary="Thông tin người dùng hiện tại")
async def get_me(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    roles = await auth_service.get_user_roles(session, current_user.id)
    if current_user.is_superuser:
        permissions = ["*"]
    else:
        permissions = sorted(await auth_service.get_user_permissions(session, current_user.id))

    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        roles=roles,
        permissions=permissions,
    )


@router.post("/change-password", summary="Đổi mật khẩu")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu cũ không đúng",
        )
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mật khẩu mới phải có ít nhất 8 ký tự",
        )

    current_user.hashed_password = hash_password(payload.new_password)
    session.add(current_user)
    await auth_service.log_audit(
        session, current_user.id, "RESET_PASSWORD",
        entity_type="user", entity_id=current_user.id, entity_name=current_user.email,
    )
    await session.commit()
    return {"message": "Đổi mật khẩu thành công"}
