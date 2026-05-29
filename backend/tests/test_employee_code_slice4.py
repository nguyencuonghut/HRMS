import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.employee import Employee
from app.models.employee_code import EmployeeCodeSequence
from app.schemas.employee import EmployeeCreate
from app.services import employee_service


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _cleanup():
    async with _make_session()() as s:
        employee_ids = [e.id for e in (await s.execute(select(Employee))).scalars().all() if e.id_number.startswith("TESTSEQ4")]
        if employee_ids:
            await s.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
        await s.commit()


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    await _cleanup()


async def _get_sequence(code: str) -> EmployeeCodeSequence:
    async with _make_session()() as s:
        return (
            await s.execute(
                select(EmployeeCodeSequence).where(EmployeeCodeSequence.code == code)
            )
        ).scalar_one()


def _payload(id_number: str, *, sequence_id: int | None = None, employee_seq: int | None = None) -> EmployeeCreate:
    return EmployeeCreate(
        employee_seq=employee_seq,
        employee_code_sequence_id=sequence_id,
        full_name=f"Slice4 {id_number}",
        last_name="Slice4",
        first_name=id_number,
        date_of_birth="1990-01-01",
        gender="male",
        nationality_id=1,
        id_number=id_number,
        id_issued_on="2020-01-01",
        id_issued_by="Cuc Canh sat",
        status="probation",
        start_date="2026-01-01",
    )


async def _create_employee_with_sequence(id_number: str, sequence_code: str) -> Employee:
    sequence = await _get_sequence(sequence_code)
    async with _make_session()() as s:
        employee = await employee_service.create_employee(
            s,
            _payload(id_number, sequence_id=sequence.id),
        )
        await s.commit()
        await s.refresh(employee)
        return employee


@pytest.mark.asyncio
async def test_allocator_concurrent_same_sequence_no_duplicates():
    sys2_before = await _get_sequence("SYS2")
    start_value = sys2_before.next_value

    first, second = await asyncio.gather(
        _create_employee_with_sequence("TESTSEQ4A001", "SYS2"),
        _create_employee_with_sequence("TESTSEQ4A002", "SYS2"),
    )

    assert sorted([first.employee_seq, second.employee_seq]) == [start_value, start_value + 1]

    sys2_after = await _get_sequence("SYS2")
    assert sys2_after.next_value == start_value + 2


@pytest.mark.asyncio
async def test_allocator_concurrent_different_sequences_increment_independently():
    sys2_before = await _get_sequence("SYS2")
    sys3_before = await _get_sequence("SYS3")

    emp_sys2, emp_sys3 = await asyncio.gather(
        _create_employee_with_sequence("TESTSEQ4B001", "SYS2"),
        _create_employee_with_sequence("TESTSEQ4B002", "SYS3"),
    )

    assert emp_sys2.employee_seq == sys2_before.next_value
    assert emp_sys3.employee_seq == sys3_before.next_value

    sys2_after = await _get_sequence("SYS2")
    sys3_after = await _get_sequence("SYS3")
    assert sys2_after.next_value == sys2_before.next_value + 1
    assert sys3_after.next_value == sys3_before.next_value + 1


@pytest.mark.asyncio
async def test_explicit_employee_seq_is_unique_per_sequence_only():
    sys2 = await _get_sequence("SYS2")
    sys3 = await _get_sequence("SYS3")

    async with _make_session()() as s:
        first = await employee_service.create_employee(
            s,
            _payload("TESTSEQ4C001", sequence_id=sys2.id, employee_seq=9000),
        )
        await s.commit()
        await s.refresh(first)

    async with _make_session()() as s:
        second = await employee_service.create_employee(
            s,
            _payload("TESTSEQ4C002", sequence_id=sys3.id, employee_seq=9000),
        )
        await s.commit()
        await s.refresh(second)

    assert first.employee_seq == second.employee_seq == 9000

    async with _make_session()() as s:
        with pytest.raises(HTTPException) as exc:
            await employee_service.create_employee(
                s,
                _payload("TESTSEQ4C003", sequence_id=sys2.id, employee_seq=9000),
            )
        assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_employee_sequence_cutover_constraints_applied():
    async with _make_session()() as s:
        nullable = (
            await s.execute(
                text(
                    """
                    SELECT is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'employees' AND column_name = 'employee_code_sequence_id'
                    """
                )
            )
        ).scalar_one()
        assert nullable == "NO"

        indexes = (
            await s.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'employees'
                    """
                )
            )
        ).scalars().all()
        assert "uq_employees_sequence_seq" in indexes
