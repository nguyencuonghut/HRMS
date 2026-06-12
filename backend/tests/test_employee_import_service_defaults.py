from __future__ import annotations

import io
from datetime import date

import openpyxl
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.encryption import hash_sensitive
from app.models.catalog import Nationality
from app.models.employee import Employee
from app.models.employee_code import EmployeeCodeSequence
from app.services.employee_import_service import IMPORT_COLUMNS, process_import


TEST_ID_NUMBER = "IMPORTNATVN001"


def _make_engine_and_sessionmaker():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def _make_xlsx(rows: list[list[str]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def _cleanup_employee(session: AsyncSession) -> None:
    employee = (
        await session.execute(
            select(Employee).where(Employee.id_number_hash == hash_sensitive(TEST_ID_NUMBER))
        )
    ).scalar_one_or_none()
    if employee:
        await session.execute(delete(Employee).where(Employee.id == employee.id))
        await session.commit()


@pytest.mark.asyncio
async def test_employee_import_defaults_nationality_to_vn():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup_employee(session)

            vn = (
                await session.execute(select(Nationality).where(Nationality.code == "VN"))
            ).scalar_one()
            sequence = (
                await session.execute(
                    select(EmployeeCodeSequence).where(EmployeeCodeSequence.code == "SYS1")
                )
            ).scalar_one()

            workbook = _make_xlsx(
                [
                    IMPORT_COLUMNS,
                    [
                        "Import Default VN",
                        "Import",
                        "Default VN",
                        "01/01/1990",
                        "nam",
                        TEST_ID_NUMBER,
                        "01/01/2020",
                        "Cục Cảnh sát ĐKQLCƯ",
                        "probation",
                        date.today().strftime("%d/%m/%Y"),
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        sequence.code,
                        "",
                        "",
                    ],
                ]
            )

            result = await process_import(session, workbook)
            assert result.success == 1
            assert len(result.created_ids) == 1

            employee = (
                await session.execute(select(Employee).where(Employee.id == result.created_ids[0]))
            ).scalar_one()
            assert employee.nationality_id == vn.id

            await _cleanup_employee(session)
    finally:
        await engine.dispose()
