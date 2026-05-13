"""User Management API — CRUD tài khoản người dùng hệ thống."""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import Role, User
from app.schemas.user import (
    PasswordReset,
    RoleAssign,
    RoleRef,
    UserCreate,
    UserListResponse,
    UserRead,
    UserUpdate,
)
from app.services import auth_service, user_service

from fastapi import Depends
from typing import Optional

router = APIRouter()


def _build_user_read(user: User, roles: list[RoleRef]) -> UserRead:
    data = UserRead.model_validate(user)
    data.roles = roles
    return data


async def _load_roles(session: AsyncSession, user_id: int) -> list[RoleRef]:
    pairs = await user_service.get_roles_for_user(session, user_id)
    return [RoleRef.model_validate(role) for role, _ in pairs]


async def _get_or_404(session: AsyncSession, user_id: int) -> User:
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    return user


# ── List ───────────────────────────────────────────────────────────────────────

@router.get("", response_model=UserListResponse, summary="Danh sách users")
async def list_users(
    search:    Optional[str]  = Query(None),
    is_active: Optional[bool] = Query(None),
    skip:      int            = Query(0, ge=0),
    limit:     int            = Query(20, ge=1, le=100),
    _:    User           = require_permission("users:view"),
    session: AsyncSession = Depends(get_session),
):
    users, total = await user_service.list_users(
        session, search=search, is_active=is_active, skip=skip, limit=limit
    )
    items = []
    for u in users:
        from app.schemas.user import UserListItem
        roles = await _load_roles(session, u.id)
        item = UserListItem.model_validate(u)
        item.roles = roles
        items.append(item)
    return UserListResponse(items=items, total=total, skip=skip, limit=limit)


# ── Create ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=UserRead, status_code=201, summary="Tạo user mới")
async def create_user(
    payload: UserCreate,
    current_user: User = require_permission("users:create"),
    session:      AsyncSession = Depends(get_session),
):
    existing = await user_service.get_user_by_email(session, payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email đã tồn tại")

    user = await user_service.create_user(session, payload)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="user", entity_id=user.id, entity_name=user.email,
        new_data={"email": user.email, "full_name": user.full_name},
    )
    await session.commit()
    await session.refresh(user)
    return UserRead.model_validate(user)


# ── Get by ID ──────────────────────────────────────────────────────────────────

@router.get("/{user_id}", response_model=UserRead, summary="Chi tiết user")
async def get_user(
    user_id:  int,
    _:        User           = require_permission("users:view"),
    session:  AsyncSession   = Depends(get_session),
):
    user = await _get_or_404(session, user_id)
    roles = await _load_roles(session, user.id)
    return _build_user_read(user, roles)


# ── Update ─────────────────────────────────────────────────────────────────────

@router.put("/{user_id}", response_model=UserRead, summary="Cập nhật user")
async def update_user(
    user_id:      int,
    payload:      UserUpdate,
    current_user: User           = require_permission("users:edit"),
    session:      AsyncSession   = Depends(get_session),
):
    user = await _get_or_404(session, user_id)

    if payload.email and payload.email != user.email:
        conflict = await user_service.get_user_by_email(session, payload.email)
        if conflict:
            raise HTTPException(status_code=409, detail="Email đã tồn tại")

    old_data = {"email": user.email, "full_name": user.full_name, "is_active": user.is_active}
    user = await user_service.update_user(session, user, payload)
    new_data = {"email": user.email, "full_name": user.full_name, "is_active": user.is_active}

    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="user", entity_id=user.id, entity_name=user.email,
        old_data=old_data, new_data=new_data,
    )
    await session.commit()
    await session.refresh(user)
    roles = await _load_roles(session, user.id)
    return _build_user_read(user, roles)


# ── Soft delete ────────────────────────────────────────────────────────────────

@router.delete("/{user_id}", status_code=204, summary="Vô hiệu hóa user")
async def deactivate_user(
    user_id:      int,
    current_user: User         = require_permission("users:delete"),
    session:      AsyncSession = Depends(get_session),
):
    user = await _get_or_404(session, user_id)

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Không thể vô hiệu hóa chính mình")
    if user.is_superuser and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Không đủ quyền vô hiệu hóa superuser")

    from app.schemas.user import UserUpdate as _UU
    await user_service.update_user(session, user, _UU(is_active=False))
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="user", entity_id=user.id, entity_name=user.email,
    )
    await session.commit()


# ── Reset password ─────────────────────────────────────────────────────────────

@router.post("/{user_id}/reset-password", summary="Đặt lại mật khẩu")
async def reset_password(
    user_id:      int,
    payload:      PasswordReset,
    current_user: User         = require_permission("users:edit"),
    session:      AsyncSession = Depends(get_session),
):
    user = await _get_or_404(session, user_id)
    await user_service.reset_password(session, user, payload.new_password)
    await auth_service.log_audit(
        session, current_user.id, "RESET_PASSWORD",
        entity_type="user", entity_id=user.id, entity_name=user.email,
    )
    await session.commit()
    return {"message": "Đặt lại mật khẩu thành công"}


# ── Roles ──────────────────────────────────────────────────────────────────────

@router.get("/{user_id}/roles", response_model=list[RoleRef], summary="Roles của user")
async def get_user_roles(
    user_id: int,
    _:       User         = require_permission("users:view"),
    session: AsyncSession = Depends(get_session),
):
    await _get_or_404(session, user_id)
    return await _load_roles(session, user_id)


@router.post("/{user_id}/roles", response_model=RoleRef, status_code=201, summary="Gán role cho user")
async def assign_role(
    user_id:      int,
    payload:      RoleAssign,
    current_user: User         = require_permission("users:edit"),
    session:      AsyncSession = Depends(get_session),
):
    await _get_or_404(session, user_id)

    role = await session.get(Role, payload.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Không tìm thấy role")

    await user_service.assign_role(
        session, user_id, payload.role_id,
        scope_type=payload.scope_type,
        department_ids=payload.department_ids,
    )
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="user_role",
        entity_id=user_id,
        entity_name=f"user:{user_id} role:{role.code}",
    )
    await session.commit()
    return RoleRef.model_validate(role)


@router.delete("/{user_id}/roles/{role_id}", status_code=204, summary="Bỏ role khỏi user")
async def remove_role(
    user_id:      int,
    role_id:      int,
    current_user: User         = require_permission("users:edit"),
    session:      AsyncSession = Depends(get_session),
):
    await _get_or_404(session, user_id)
    removed = await user_service.remove_role(session, user_id, role_id)
    if not removed:
        raise HTTPException(status_code=404, detail="User không có role này")
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="user_role",
        entity_id=user_id,
        entity_name=f"user:{user_id} remove_role:{role_id}",
    )
    await session.commit()
