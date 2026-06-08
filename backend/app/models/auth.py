from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(SQLModel, table=True):
    """Tài khoản người dùng hệ thống. Email là định danh đăng nhập."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(
        sa_column=Column(sa.String(200), unique=True, index=True, nullable=False)
    )
    full_name: str = Field(max_length=200)
    hashed_password: str = Field()
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    # Liên kết hồ sơ nhân viên — sẽ có FK thực khi triển khai module Nhân sự
    employee_id: Optional[int] = Field(default=None)
    last_login_at: Optional[datetime] = Field(default=None)
    refresh_token_version: int = Field(
        default=0,
        sa_column=Column(sa.Integer(), nullable=False, server_default="0"),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class Role(SQLModel, table=True):
    """Vai trò hệ thống. is_system=True → không được xóa."""

    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        sa_column=Column(sa.String(50), unique=True, index=True, nullable=False)
    )
    name: str = Field(max_length=200)
    description: Optional[str] = Field(
        default=None, sa_column=Column(sa.Text(), nullable=True)
    )
    is_system: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utcnow)


class Permission(SQLModel, table=True):
    """Quyền hạn theo format '{module}:{action}'. Seeded, không sửa qua UI."""

    __tablename__ = "permissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        sa_column=Column(sa.String(100), unique=True, index=True, nullable=False)
    )
    name: str = Field(max_length=200)
    module: str = Field(max_length=50)
    action: str = Field(max_length=20)
    description: Optional[str] = Field(
        default=None, sa_column=Column(sa.Text(), nullable=True)
    )


class RolePermission(SQLModel, table=True):
    """Bảng trung gian Role ↔ Permission (many-to-many)."""

    __tablename__ = "role_permissions"

    role_id: int = Field(foreign_key="roles.id", primary_key=True)
    permission_id: int = Field(foreign_key="permissions.id", primary_key=True)


class UserRole(SQLModel, table=True):
    """Bảng trung gian User ↔ Role với phạm vi tổ chức tùy chọn."""

    __tablename__ = "user_roles"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    role_id: int = Field(foreign_key="roles.id", primary_key=True)
    # NULL = toàn công ty; 'department' = giới hạn theo department_ids
    scope_type: Optional[str] = Field(default=None, max_length=20)
    department_ids: Optional[Any] = Field(
        default=None,
        sa_column=Column(ARRAY(sa.Integer()), nullable=True),
    )


class AuditLog(SQLModel, table=True):
    """Nhật ký thao tác toàn hệ thống. Không bao giờ xóa/sửa dòng cũ."""

    __tablename__ = "audit_logs"

    id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.BigInteger(), primary_key=True, autoincrement=True),
    )
    # Người thực hiện — nullable: system action hoặc trước khi đăng nhập
    user_id: Optional[int] = Field(default=None)
    # LOGIN | CREATE | UPDATE | DELETE | EXPORT | RESET_PASSWORD | VIEW_SENSITIVE
    action: str = Field(max_length=50)
    entity_type: Optional[str] = Field(default=None, max_length=50)
    entity_id: Optional[int] = Field(default=None)
    entity_name: Optional[str] = Field(default=None, max_length=200)
    old_data: Optional[Any] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    new_data: Optional[Any] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(
        default=None, sa_column=Column(sa.Text(), nullable=True)
    )
    created_at: datetime = Field(default_factory=_utcnow)
