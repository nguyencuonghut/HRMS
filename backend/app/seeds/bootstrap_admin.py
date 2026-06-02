"""Bootstrap first admin account for clean production deployments."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Role, User
from app.schemas.user import UserCreate, validate_password_strength
from app.services import user_service


class BootstrapAdminInput(BaseModel):
    email: EmailStr
    full_name: str = Field(..., max_length=200)
    password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("full_name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("BOOTSTRAP_ADMIN_FULL_NAME không được để trống")
        return value

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


async def run(session: AsyncSession, *, email: str, full_name: str, password: str) -> str:
    """Create or ensure a first admin account.

    Returns:
        "created" if a new user was created.
        "ensured" if an existing user was elevated/confirmed as admin.
    """

    payload = BootstrapAdminInput(
        email=email,
        full_name=full_name,
        password=password,
    )

    admin_role = (
        await session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one_or_none()
    if admin_role is None:
        raise RuntimeError(
            "Không tìm thấy role 'admin'. Chạy seed-required trước khi bootstrap admin."
        )

    existing = await user_service.get_user_by_email(session, payload.email)
    if existing is None:
        existing = await user_service.create_user(
            session,
            UserCreate(
                email=payload.email,
                full_name=payload.full_name,
                password=payload.password,
                is_active=True,
                is_superuser=True,
            ),
        )
        await user_service.assign_role(session, existing.id, admin_role.id)
        await session.commit()
        print(f"  [bootstrap-admin] Created admin user: {existing.email}")
        return "created"

    changed = False
    if existing.full_name != payload.full_name:
        existing.full_name = payload.full_name
        changed = True
    if not existing.is_active:
        existing.is_active = True
        changed = True
    if not existing.is_superuser:
        existing.is_superuser = True
        changed = True
    if changed:
        session.add(existing)

    assignments = await user_service.get_roles_for_user(session, existing.id)
    if not any(role.code == "admin" for role, _ in assignments):
        await user_service.assign_role(session, existing.id, admin_role.id)
        changed = True

    if changed:
        await session.commit()
    else:
        await session.rollback()

    print(f"  [bootstrap-admin] Ensured admin user: {existing.email}")
    return "ensured"
