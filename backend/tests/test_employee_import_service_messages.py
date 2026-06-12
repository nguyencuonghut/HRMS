from __future__ import annotations

import io
from datetime import date

import openpyxl
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.org import Department, JobPosition
from app.schemas.employee_import import IMPORT_COLUMNS
from app.services.employee_import_service import process_import


def _make_session():
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


def _valid_row(*, department_code: str, position_name: str, suffix: str) -> list[str]:
    return [
        f"Import Message {suffix}",
        "Import",
        f"Message {suffix}",
        "01/01/1990",
        "nam",
        f"MSG{suffix}",
        "01/01/2020",
        "Cục Cảnh sát ĐKQLCƯ",
        "probation",
        date.today().strftime("%d/%m/%Y"),
        "",
        "",
        "",
        "",
        department_code,
        "",
        position_name,
        "",
        "",
        "",
    ]


@pytest.mark.asyncio
async def test_import_position_error_shows_actual_department_when_department_is_wrong():
    engine, session_factory = _make_session()
    async with session_factory() as session:
        actual_department = Department(code="TMSG_ACTUAL", name="Phòng ban thực tế")
        selected_department = Department(code="TMSG_SELECTED", name="Phòng ban nhập nhầm")
        session.add(actual_department)
        session.add(selected_department)
        await session.flush()

        position = JobPosition(
            code="TMSG_POS",
            name="Vị trí kiểm thử import message",
            department_id=actual_department.id,
            is_active=True,
        )
        session.add(position)
        await session.flush()

        workbook = _make_xlsx(
            [
                IMPORT_COLUMNS,
                _valid_row(
                    department_code=selected_department.code,
                    position_name=position.name,
                    suffix="POSERR001",
                ),
            ]
        )

        result = await process_import(session, workbook)
        await session.rollback()

    await engine.dispose()

    assert result.success == 0
    assert result.failed == 1
    assert len(result.errors) == 1
    assert result.errors[0].column == "Vị trí công việc"
    assert "có tồn tại nhưng thuộc phòng ban" in result.errors[0].message
    assert f"{actual_department.code} - {actual_department.name}" in result.errors[0].message
    assert f"{selected_department.code} - {selected_department.name}" in result.errors[0].message
