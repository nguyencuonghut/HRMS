import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_employee_code_sequences_seeded_and_backfilled():
    async with _make_session()() as session:
        rows = (await session.execute(
            text(
                """
                SELECT code, next_value, is_default, is_active
                FROM employee_code_sequences
                ORDER BY code
                """
            )
        )).all()

        assert [row.code for row in rows] == ["SYS1", "SYS2", "SYS3"]
        sys1 = next(row for row in rows if row.code == "SYS1")
        assert sys1.is_default is True
        assert sys1.is_active is True

        max_seq = (await session.execute(
            text("SELECT COALESCE(MAX(employee_seq), 0) FROM employees")
        )).scalar_one()
        assert sys1.next_value == max_seq + 1

        null_count = (await session.execute(
            text("SELECT COUNT(*) FROM employees WHERE employee_code_sequence_id IS NULL")
        )).scalar_one()
        assert null_count == 0

        sys1_employee_count = (await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM employees e
                JOIN employee_code_sequences s ON s.id = e.employee_code_sequence_id
                WHERE s.code = 'SYS1'
                """
            )
        )).scalar_one()
        total_employee_count = (await session.execute(
            text("SELECT COUNT(*) FROM employees")
        )).scalar_one()
        assert sys1_employee_count == total_employee_count
