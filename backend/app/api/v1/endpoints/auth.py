from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from jose import JWTError
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_active_user, oauth2_scheme
from app.core.database import get_session
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.models.auth import User
from app.schemas.user import validate_password_strength
from app.services import auth_service

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # refresh_token không còn trong body — được set qua HttpOnly cookie


class RefreshRequest(BaseModel):
    # Vẫn giữ để backward compat với client cũ; cookie được ưu tiên
    refresh_token: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserMeResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone_number: Optional[str]
    is_active: bool
    is_superuser: bool
    roles: list[str]
    permissions: list[str]


class UserMeUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None


def _refresh_rate_limit_key(request: Request) -> str:
    """Rate-limit /auth/refresh theo user/session logic thay vì proxy IP chung."""
    raw_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if raw_token:
        try:
            data = decode_token(raw_token)
            if data.get("type") == "refresh":
                email = data.get("sub")
                if email:
                    return f"refresh:{email}"
        except JWTError:
            pass

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"
    if request.client:
        return f"ip:{request.client.host}"
    return "ip:unknown"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Đăng nhập")
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()
    await auth_service.check_login_rate_limit(client_ip)
    await auth_service.check_login_allowed(payload.email)
    user = await auth_service.authenticate_user(session, payload.email, payload.password)
    if not user:
        await auth_service.record_failed_login(payload.email)
        await auth_service.record_login_rate_limit(client_ip)
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

    await auth_service.clear_failed_login(payload.email)
    await auth_service.update_last_login(session, user)
    await auth_service.log_audit(
        session, user.id, "LOGIN",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()

    data = TokenResponse(access_token=access_token).model_dump()
    response = JSONResponse(content=data)
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86_400,
        path="/api/v1/auth",   # chỉ gửi đến auth endpoints
    )
    return response


@router.post("/refresh", response_model=TokenResponse, summary="Làm mới access token")
@limiter.limit("20/hour", key_func=_refresh_rate_limit_key)
async def refresh_token(
    request: Request,
    payload: Optional[RefreshRequest] = None,
    session: AsyncSession = Depends(get_session),
):
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token không hợp lệ hoặc đã hết hạn",
    )

    # Cookie ưu tiên → fallback sang request body (backward compat)
    raw_token = (
        request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        or (payload.refresh_token if payload else None)
    )
    if not raw_token:
        raise exc

    try:
        data = decode_token(raw_token)
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

    # Set cookie mới + trả access_token trong body
    result = TokenResponse(access_token=new_access).model_dump()
    response = JSONResponse(content=result)
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=new_refresh,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86_400,
        path="/api/v1/auth",
    )
    return response


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
        phone_number=current_user.phone_number,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        roles=roles,
        permissions=permissions,
    )


@router.post("/logout", summary="Đăng xuất")
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if not jti or not exp:
            raise ValueError("missing token claims")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không thể xác thực thông tin đăng nhập",
        )

    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    await auth_service.blacklist_token(jti, expires_at)
    await auth_service.log_audit(
        session, current_user.id, "LOGOUT",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()

    # Xóa refresh_token cookie
    resp = JSONResponse(content={"message": "Đăng xuất thành công"})
    resp.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path="/api/v1/auth",
        httponly=True,
        samesite="strict",
    )
    return resp


@router.put("/me", response_model=UserMeResponse, summary="Cập nhật thông tin cá nhân")
async def update_me(
    payload: UserMeUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    from datetime import datetime, timezone
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.phone_number is not None:
        current_user.phone_number = payload.phone_number
    current_user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    from app.services.auth_service import get_user_roles, get_user_permissions
    roles = await get_user_roles(session, current_user.id)
    permissions = ["*"] if current_user.is_superuser else sorted(await get_user_permissions(session, current_user.id))
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone_number=current_user.phone_number,
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
    current_user.hashed_password = hash_password(payload.new_password)
    session.add(current_user)
    await auth_service.log_audit(
        session, current_user.id, "RESET_PASSWORD",
        entity_type="user", entity_id=current_user.id, entity_name=current_user.email,
    )
    await session.commit()
    return {"message": "Đổi mật khẩu thành công"}
