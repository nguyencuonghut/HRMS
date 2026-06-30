"""Role & Permission Management API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.core.rbac_catalog import ACTION_LABELS, ACTION_ORDER, MODULE_LABELS, MODULE_ORDER
from app.models.auth import User
from app.schemas.role import (
    PermissionRead,
    PermissionsReplace,
    RoleCreate,
    RoleListItem,
    RoleRead,
    RoleUpdate,
)
from app.services import auth_service, role_service

router = APIRouter()


async def _get_or_404(session: AsyncSession, role_id: int):
    role = await role_service.get_role_by_id(session, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Không tìm thấy role")
    return role


def _to_permission_read(permission) -> PermissionRead:
    return PermissionRead(
        id=permission.id,
        code=permission.code,
        name=permission.name,
        module=permission.module,
        module_label=MODULE_LABELS.get(permission.module, permission.module),
        module_order=MODULE_ORDER.get(permission.module, 9_999),
        action=permission.action,
        action_label=ACTION_LABELS.get(permission.action, permission.action),
        action_order=ACTION_ORDER.get(permission.action, 9_999),
        description=permission.description,
    )


# ── GET /permissions ───────────────────────────────────────────────────────────

@router.get("/permissions", response_model=list[PermissionRead], summary="Danh sách tất cả permissions")
async def list_permissions(
    _:       User         = require_permission("roles:view"),
    session: AsyncSession = Depends(get_session),
):
    permissions = await role_service.list_all_permissions(session)
    return [_to_permission_read(permission) for permission in permissions]


# ── GET /roles ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[RoleListItem], summary="Danh sách roles")
async def list_roles(
    _:       User         = require_permission("roles:view"),
    session: AsyncSession = Depends(get_session),
):
    pairs = await role_service.list_roles(session)
    items = []
    for role, perm_count in pairs:
        item = RoleListItem.model_validate(role)
        item.permission_count = perm_count
        items.append(item)
    return items


# ── POST /roles ────────────────────────────────────────────────────────────────

@router.post("", response_model=RoleRead, status_code=201, summary="Tạo role mới")
async def create_role(
    payload:      RoleCreate,
    current_user: User         = require_permission("roles:create"),
    session:      AsyncSession = Depends(get_session),
):
    existing = await role_service.get_role_by_code(session, payload.code)
    if existing:
        raise HTTPException(status_code=409, detail="Mã role đã tồn tại")

    role = await role_service.create_role(session, payload)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="role", entity_id=role.id, entity_name=role.code,
        new_data={"code": role.code, "name": role.name},
    )
    await session.commit()
    await session.refresh(role)
    result = RoleRead.model_validate(role)
    result.permissions = []
    return result


# ── GET /roles/{id} ────────────────────────────────────────────────────────────

@router.get("/{role_id}", response_model=RoleRead, summary="Chi tiết role + permissions")
async def get_role(
    role_id: int,
    _:       User         = require_permission("roles:view"),
    session: AsyncSession = Depends(get_session),
):
    role = await _get_or_404(session, role_id)
    perms = await role_service.get_permissions_for_role(session, role_id)
    result = RoleRead.model_validate(role)
    result.permissions = [_to_permission_read(permission) for permission in perms]
    return result


# ── PUT /roles/{id} ────────────────────────────────────────────────────────────

@router.put("/{role_id}", response_model=RoleRead, summary="Cập nhật role")
async def update_role(
    role_id:      int,
    payload:      RoleUpdate,
    current_user: User         = require_permission("roles:edit"),
    session:      AsyncSession = Depends(get_session),
):
    role = await _get_or_404(session, role_id)
    old_data = {"name": role.name, "description": role.description}
    role = await role_service.update_role(session, role, payload)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="role", entity_id=role.id, entity_name=role.code,
        old_data=old_data,
        new_data={"name": role.name, "description": role.description},
    )
    await session.commit()
    await session.refresh(role)
    perms = await role_service.get_permissions_for_role(session, role_id)
    result = RoleRead.model_validate(role)
    result.permissions = [_to_permission_read(permission) for permission in perms]
    return result


# ── DELETE /roles/{id} ─────────────────────────────────────────────────────────

@router.delete("/{role_id}", status_code=204, summary="Xóa role")
async def delete_role(
    role_id:      int,
    current_user: User         = require_permission("roles:delete"),
    session:      AsyncSession = Depends(get_session),
):
    role = await _get_or_404(session, role_id)
    if role.is_system:
        raise HTTPException(status_code=400, detail="Không thể xóa role hệ thống")

    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="role", entity_id=role.id, entity_name=role.code,
    )
    await role_service.delete_role(session, role)
    await session.commit()


# ── GET /roles/{id}/permissions ────────────────────────────────────────────────

@router.get("/{role_id}/permissions", response_model=list[PermissionRead], summary="Permissions của role")
async def get_role_permissions(
    role_id: int,
    _:       User         = require_permission("roles:view"),
    session: AsyncSession = Depends(get_session),
):
    await _get_or_404(session, role_id)
    perms = await role_service.get_permissions_for_role(session, role_id)
    return [_to_permission_read(permission) for permission in perms]


# ── PUT /roles/{id}/permissions ────────────────────────────────────────────────

@router.put("/{role_id}/permissions", response_model=list[PermissionRead], summary="Cập nhật toàn bộ permissions của role")
async def replace_role_permissions(
    role_id:      int,
    payload:      PermissionsReplace,
    current_user: User         = require_permission("roles:edit"),
    session:      AsyncSession = Depends(get_session),
):
    role = await _get_or_404(session, role_id)

    perms = await role_service.replace_permissions(session, role_id, payload.permission_ids)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="role_permissions", entity_id=role_id, entity_name=role.code,
        new_data={"permission_ids": payload.permission_ids},
    )
    await session.commit()
    return [_to_permission_read(permission) for permission in perms]
