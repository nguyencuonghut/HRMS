"""Regression checks cho Slice 1 employee insurance schema + compatibility."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.encryption import hash_sensitive
from app.models.employee import Employee
from app.services.employee_insurance_service import ensure_employee_insurance_profile


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_backfill_does_not_create_duplicate_profiles():
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
        assert counts.profile_count <= counts.employee_count

        duplicate_count = (
            await s.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT employee_id
                        FROM employee_insurance_profiles
                        GROUP BY employee_id
                        HAVING COUNT(*) > 1
                    ) duplicated
                    """
                )
            )
        ).scalar_one()
        assert duplicate_count == 0


@pytest.mark.asyncio
async def test_backfill_maps_resigned_employees_to_stopped():
    async with _make_session()() as s:
        max_seq = (
            await s.execute(
                select(func.coalesce(func.max(Employee.employee_seq), 0)).select_from(Employee)
            )
        ).scalar_one()
        employee = Employee(
            employee_seq=max_seq + 1,
            employee_code_sequence_id=1,
            full_name="Test Insurance Resigned",
            normalized_name="test insurance resigned",
            last_name="Test Insurance",
            first_name="Resigned",
            date_of_birth=date(1990, 1, 1),
            gender="male",
            nationality_id=1,
            id_number="TESTINSURANCE999001",
            id_number_hash=hash_sensitive("TESTINSURANCE999001"),
            id_issued_on=date(2020, 1, 1),
            id_issued_by="CA Test",
            status="resigned",
            start_date=date(2020, 1, 1),
            resigned_date=date(2025, 1, 1),
        )
        s.add(employee)
        await s.flush()

        try:
            profile = await ensure_employee_insurance_profile(s, employee)
            assert profile.participation_status == "stopped"
        finally:
            await s.execute(
                text("DELETE FROM employee_insurance_profiles WHERE employee_id = :employee_id"),
                {"employee_id": employee.id},
            )
            await s.execute(
                text("DELETE FROM employees WHERE id = :employee_id"),
                {"employee_id": employee.id},
            )
            await s.commit()
