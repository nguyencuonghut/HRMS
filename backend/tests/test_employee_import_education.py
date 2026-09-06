from __future__ import annotations

import io
from datetime import date

import openpyxl
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.encryption import hash_sensitive
from app.models.employee import Employee
from app.models.employee_code import EmployeeCodeSequence
from app.models.employee_education import EmployeeEducationHistory
from app.services.employee_import_service import IMPORT_COLUMNS, process_import

TEST_ID_NUMBER_EDU_FULL = "IMPORTEDU001"
TEST_ID_NUMBER_EDU_NO_MAJOR = "IMPORTEDU002"
TEST_ID_NUMBER_EDU_NONE = "IMPORTEDU003"
TEST_ID_NUMBER_EDU_MISSING_LEVEL = "IMPORTEDU004"
TEST_ID_NUMBER_EDU_UNKNOWN_INSTITUTION = "IMPORTEDU005"
TEST_ID_NUMBER_EDU_UNKNOWN_MAJOR = "IMPORTEDU006"
TEST_ID_NUMBER_EDU_UNKNOWN_LEVEL = "IMPORTEDU007"
TEST_ID_NUMBER_EDU_BAD_YEAR = "IMPORTEDU008"

VALID_NEW_ADDRESS = "thôn Vạc, Phường An Bình, Thành phố Cần Thơ"
VALID_INSTITUTION = "Học viện Nông nghiệp Việt Nam"
VALID_MAJOR = "Thú y"
VALID_LEVEL = "Đại học"


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


def _make_row(
    *,
    id_number: str,
    sequence_code: str,
    education_level: str = "",
    institution: str = "",
    major: str = "",
    graduation_year: str = "",
    diploma_type: str = "",
) -> list[str]:
    values = {column: "" for column in IMPORT_COLUMNS}
    values.update(
        {
            "Họ và tên": "Import Education Test",
            "Họ": "Import",
            "Tên": "Education Test",
            "Ngày sinh": "01/01/1990",
            "Giới tính": "nam",
            "Số CCCD/CMND": id_number,
            "Ngày cấp CCCD": "01/01/2020",
            "Nơi cấp CCCD": "Cục Cảnh sát ĐKQLCƯ",
            "Trạng thái": "probation",
            "Ngày vào làm": date.today().strftime("%d/%m/%Y"),
            "Hệ mã nhân viên": sequence_code,
            "Địa chỉ thường trú (Hệ mới 2 cấp)": VALID_NEW_ADDRESS,
            "Địa chỉ liên lạc (Hệ mới 2 cấp)": VALID_NEW_ADDRESS,
            "Trình độ học vấn": education_level,
            "Trường học": institution,
            "Chuyên ngành": major,
            "Năm tốt nghiệp": graduation_year,
            "Loại hình đào tạo": diploma_type,
        }
    )
    return [values[column] for column in IMPORT_COLUMNS]


async def _cleanup(session: AsyncSession) -> None:
    for test_id_number in (
        TEST_ID_NUMBER_EDU_FULL,
        TEST_ID_NUMBER_EDU_NO_MAJOR,
        TEST_ID_NUMBER_EDU_NONE,
        TEST_ID_NUMBER_EDU_MISSING_LEVEL,
        TEST_ID_NUMBER_EDU_UNKNOWN_INSTITUTION,
        TEST_ID_NUMBER_EDU_UNKNOWN_MAJOR,
        TEST_ID_NUMBER_EDU_UNKNOWN_LEVEL,
        TEST_ID_NUMBER_EDU_BAD_YEAR,
    ):
        employee = (
            await session.execute(
                select(Employee).where(Employee.id_number_hash == hash_sensitive(test_id_number))
            )
        ).scalar_one_or_none()
        if employee:
            await session.execute(
                delete(EmployeeEducationHistory).where(EmployeeEducationHistory.employee_id == employee.id)
            )
            await session.execute(delete(Employee).where(Employee.id == employee.id))
    await session.commit()


@pytest.mark.asyncio
async def test_import_education_full_info_creates_history():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)
            sequence = (
                await session.execute(select(EmployeeCodeSequence).where(EmployeeCodeSequence.code == "SYS1"))
            ).scalar_one()

            workbook = _make_xlsx([
                IMPORT_COLUMNS,
                _make_row(
                    id_number=TEST_ID_NUMBER_EDU_FULL,
                    sequence_code=sequence.code,
                    education_level=VALID_LEVEL,
                    institution=VALID_INSTITUTION,
                    major=VALID_MAJOR,
                    graduation_year="2015",
                    diploma_type="chính quy",
                ),
            ])

            result = await process_import(session, workbook)
            assert result.success == 1, result.errors

            history = (
                await session.execute(
                    select(EmployeeEducationHistory).where(
                        EmployeeEducationHistory.employee_id == result.created_ids[0]
                    )
                )
            ).scalar_one()
            assert history.institution_id is not None
            assert history.major_id is not None
            assert history.education_level_id is not None
            assert history.graduation_year == 2015
            assert history.diploma_type == "chính quy"
            assert history.is_main_education is True

            await _cleanup(session)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_import_education_without_major_is_optional():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)
            sequence = (
                await session.execute(select(EmployeeCodeSequence).where(EmployeeCodeSequence.code == "SYS1"))
            ).scalar_one()

            workbook = _make_xlsx([
                IMPORT_COLUMNS,
                _make_row(
                    id_number=TEST_ID_NUMBER_EDU_NO_MAJOR,
                    sequence_code=sequence.code,
                    education_level=VALID_LEVEL,
                    institution=VALID_INSTITUTION,
                ),
            ])

            result = await process_import(session, workbook)
            assert result.success == 1, result.errors

            history = (
                await session.execute(
                    select(EmployeeEducationHistory).where(
                        EmployeeEducationHistory.employee_id == result.created_ids[0]
                    )
                )
            ).scalar_one()
            assert history.institution_id is not None
            assert history.major_id is None

            await _cleanup(session)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_import_education_blank_institution_skips_entirely():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)
            sequence = (
                await session.execute(select(EmployeeCodeSequence).where(EmployeeCodeSequence.code == "SYS1"))
            ).scalar_one()

            workbook = _make_xlsx([
                IMPORT_COLUMNS,
                _make_row(id_number=TEST_ID_NUMBER_EDU_NONE, sequence_code=sequence.code),
            ])

            result = await process_import(session, workbook)
            assert result.success == 1, result.errors

            count = (
                await session.execute(
                    select(EmployeeEducationHistory).where(
                        EmployeeEducationHistory.employee_id == result.created_ids[0]
                    )
                )
            ).scalars().all()
            assert count == []

            await _cleanup(session)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_import_education_institution_without_level_fails():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)
            sequence = (
                await session.execute(select(EmployeeCodeSequence).where(EmployeeCodeSequence.code == "SYS1"))
            ).scalar_one()

            workbook = _make_xlsx([
                IMPORT_COLUMNS,
                _make_row(
                    id_number=TEST_ID_NUMBER_EDU_MISSING_LEVEL,
                    sequence_code=sequence.code,
                    institution=VALID_INSTITUTION,
                ),
            ])

            result = await process_import(session, workbook)
            assert result.success == 0
            assert result.failed == 1
            assert any(
                error.column == "Trình độ học vấn" and "Bắt buộc" in error.message
                for error in result.errors
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_import_education_unknown_institution_fails():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)
            sequence = (
                await session.execute(select(EmployeeCodeSequence).where(EmployeeCodeSequence.code == "SYS1"))
            ).scalar_one()

            workbook = _make_xlsx([
                IMPORT_COLUMNS,
                _make_row(
                    id_number=TEST_ID_NUMBER_EDU_UNKNOWN_INSTITUTION,
                    sequence_code=sequence.code,
                    education_level=VALID_LEVEL,
                    institution="Trường Không Tồn Tại Xyz123",
                ),
            ])

            result = await process_import(session, workbook)
            assert result.success == 0
            assert result.failed == 1
            assert any(error.column == "Trường học" and "Không tìm thấy" in error.message for error in result.errors)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_import_education_unknown_major_fails():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)
            sequence = (
                await session.execute(select(EmployeeCodeSequence).where(EmployeeCodeSequence.code == "SYS1"))
            ).scalar_one()

            workbook = _make_xlsx([
                IMPORT_COLUMNS,
                _make_row(
                    id_number=TEST_ID_NUMBER_EDU_UNKNOWN_MAJOR,
                    sequence_code=sequence.code,
                    education_level=VALID_LEVEL,
                    institution=VALID_INSTITUTION,
                    major="Chuyên ngành Không Tồn Tại Xyz123",
                ),
            ])

            result = await process_import(session, workbook)
            assert result.success == 0
            assert result.failed == 1
            assert any(error.column == "Chuyên ngành" and "Không tìm thấy" in error.message for error in result.errors)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_import_education_unknown_level_fails():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)
            sequence = (
                await session.execute(select(EmployeeCodeSequence).where(EmployeeCodeSequence.code == "SYS1"))
            ).scalar_one()

            workbook = _make_xlsx([
                IMPORT_COLUMNS,
                _make_row(
                    id_number=TEST_ID_NUMBER_EDU_UNKNOWN_LEVEL,
                    sequence_code=sequence.code,
                    education_level="Trình độ không tồn tại xyz",
                    institution=VALID_INSTITUTION,
                ),
            ])

            result = await process_import(session, workbook)
            assert result.success == 0
            assert result.failed == 1
            assert any(
                error.column == "Trình độ học vấn" and "Không tìm thấy" in error.message
                for error in result.errors
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_import_education_invalid_graduation_year_fails():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)
            sequence = (
                await session.execute(select(EmployeeCodeSequence).where(EmployeeCodeSequence.code == "SYS1"))
            ).scalar_one()

            workbook = _make_xlsx([
                IMPORT_COLUMNS,
                _make_row(
                    id_number=TEST_ID_NUMBER_EDU_BAD_YEAR,
                    sequence_code=sequence.code,
                    education_level=VALID_LEVEL,
                    institution=VALID_INSTITUTION,
                    graduation_year="not_a_year",
                ),
            ])

            result = await process_import(session, workbook)
            assert result.success == 0
            assert result.failed == 1
            assert any(error.column == "Năm tốt nghiệp" for error in result.errors)
    finally:
        await engine.dispose()
