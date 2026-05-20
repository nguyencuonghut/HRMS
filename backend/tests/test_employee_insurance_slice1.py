"""Regression checks cho Slice 1 employee insurance schema + compatibility."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_backfill_created_one_profile_per_employee():
    async with _make_session()() as s:
        counts = (
            await s.execute(
                text(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM employees) AS employee_count,
                        (SELECT COUNT(*) FROM employee_insurance_profiles) AS profile_count
                    """
                )
            )
        ).one()
        assert counts.employee_count == counts.profile_count


@pytest.mark.asyncio
async def test_backfill_maps_resigned_employees_to_stopped():
    async with _make_session()() as s:
        mismatch_count = (
            await s.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM employee_insurance_profiles profile
                    JOIN employees employee ON employee.id = profile.employee_id
                    WHERE employee.status = 'resigned'
                      AND profile.participation_status <> 'stopped'
                    """
                )
            )
        ).scalar_one()
        assert mismatch_count == 0
