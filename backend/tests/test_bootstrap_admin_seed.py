"""Regression tests for production bootstrap-admin seeding."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.seeds import bootstrap_admin, rbac


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _scalar(sql: str, **params):
    async with _make_session()() as session:
        return (await session.execute(text(sql), params)).scalar()


async def _row(sql: str, **params):
    async with _make_session()() as session:
        return (await session.execute(text(sql), params)).fetchone()


async def _cleanup(email: str) -> None:
    async with _make_session()() as session:
        await session.execute(
            text(
                """
                DELETE FROM user_roles
                WHERE user_id IN (SELECT id FROM users WHERE email = :email)
                """
            ),
            {"email": email},
        )
        await session.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})
        await session.commit()


@pytest.mark.asyncio
async def test_bootstrap_admin_creates_first_admin_user():
    email = f"bootstrap-admin-{uuid4().hex[:8]}@example.com"
    password = "Bootstrap#2026"
    full_name = "Bootstrap Admin"

    await _cleanup(email)
    try:
        async with _make_session()() as session:
            await rbac.run(session, include_users=False)

        async with _make_session()() as session:
            result = await bootstrap_admin.run(
                session,
                email=email,
                full_name=full_name,
                password=password,
            )

        assert result == "created"
        row = await _row(
            """
            SELECT u.email, u.full_name, u.is_active, u.is_superuser, u.hashed_password, r.code AS role_code
            FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN roles r ON r.id = ur.role_id
            WHERE u.email = :email
            """,
            email=email,
        )
        assert row is not None
        assert row.email == email
        assert row.full_name == full_name
        assert row.is_active is True
        assert row.is_superuser is True
        assert row.role_code == "admin"
        assert verify_password(password, row.hashed_password) is True
    finally:
        await _cleanup(email)


@pytest.mark.asyncio
async def test_bootstrap_admin_ensures_existing_user_without_resetting_password():
    email = f"bootstrap-existing-{uuid4().hex[:8]}@example.com"
    original_password = "Original#2026"
    bootstrap_password = "Bootstrap#2026"

    await _cleanup(email)
    try:
        async with _make_session()() as session:
            await rbac.run(session, include_users=False)
            await session.execute(
                text(
                    """
                    INSERT INTO users (email, full_name, hashed_password, is_active, is_superuser)
                    VALUES (:email, :full_name, :hashed_password, false, false)
                    """
                ),
                {
                    "email": email,
                    "full_name": "Existing User",
                    "hashed_password": hash_password(original_password),
                },
            )
            await session.commit()

        async with _make_session()() as session:
            result = await bootstrap_admin.run(
                session,
                email=email,
                full_name="System Owner",
                password=bootstrap_password,
            )

        assert result == "ensured"
        row = await _row(
            """
            SELECT u.full_name, u.is_active, u.is_superuser, u.hashed_password,
                   COUNT(*) FILTER (WHERE r.code = 'admin') AS admin_role_count
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON r.id = ur.role_id
            WHERE u.email = :email
            GROUP BY u.id
            """,
            email=email,
        )
        assert row is not None
        assert row.full_name == "System Owner"
        assert row.is_active is True
        assert row.is_superuser is True
        assert row.admin_role_count == 1
        assert verify_password(original_password, row.hashed_password) is True
        assert verify_password(bootstrap_password, row.hashed_password) is False
    finally:
        await _cleanup(email)


def test_bootstrap_admin_env_model_rejects_blank_full_name():
    with pytest.raises(ValueError):
        bootstrap_admin.BootstrapAdminInput(
            email="owner@example.com",
            full_name="   ",
            password="Bootstrap#2026",
        )
