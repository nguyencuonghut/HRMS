from __future__ import annotations

import io

import openpyxl
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.catalog import EducationMajor, EducationalInstitution
from app.seeds.education_catalog import _normalize
from app.services.education_catalog_import_service import (
    INSTITUTION_COLUMNS,
    MAJOR_COLUMNS,
    process_institution_import,
    process_major_import,
)

TEST_INSTITUTION_CODE = "TESTINST001"
TEST_INSTITUTION_NAME = "Đại học Kiểm thử Import"
TEST_INSTITUTION_NAME_NO_CODE = "Cao đẳng Kiểm thử Import Không Mã"

TEST_MAJOR_CODE = "TESTMAJ001"
TEST_MAJOR_NAME = "Chuyên ngành Kiểm thử Import"
TEST_MAJOR_NAME_NO_CODE = "Chuyên ngành Kiểm thử Import Không Mã"


def _make_engine_and_sessionmaker():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def _make_xlsx(columns: list[str], rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(columns)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def _cleanup(session: AsyncSession) -> None:
    await session.execute(
        delete(EducationalInstitution).where(
            EducationalInstitution.code.in_([TEST_INSTITUTION_CODE])
            | EducationalInstitution.normalized_name.in_(
                [_normalize(TEST_INSTITUTION_NAME), _normalize(TEST_INSTITUTION_NAME_NO_CODE)]
            )
        )
    )
    await session.execute(
        delete(EducationMajor).where(
            EducationMajor.code.in_([TEST_MAJOR_CODE])
            | EducationMajor.normalized_name.in_([_normalize(TEST_MAJOR_NAME), _normalize(TEST_MAJOR_NAME_NO_CODE)])
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_institution_import_creates_then_upserts_by_code():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)

            workbook = _make_xlsx(
                INSTITUTION_COLUMNS,
                [[TEST_INSTITUTION_CODE, TEST_INSTITUTION_NAME, "DHKT", "university", "VN", "", "1"]],
            )
            result = await process_institution_import(session, workbook)
            await session.commit()
            assert result.success == 1, result.errors
            first_id = result.created_ids[0]

            row = (
                await session.execute(select(EducationalInstitution).where(EducationalInstitution.id == first_id))
            ).scalar_one()
            assert row.short_name == "DHKT"
            assert row.institution_type == "university"

            # Import lại cùng mã, đổi tên viết tắt -> phải update record cũ, không tạo mới
            workbook2 = _make_xlsx(
                INSTITUTION_COLUMNS,
                [[TEST_INSTITUTION_CODE, TEST_INSTITUTION_NAME, "DHKT2", "college", "VN", "", "1"]],
            )
            result2 = await process_institution_import(session, workbook2)
            await session.commit()
            assert result2.success == 1, result2.errors
            assert result2.created_ids[0] == first_id

            row2 = (
                await session.execute(select(EducationalInstitution).where(EducationalInstitution.id == first_id))
            ).scalar_one()
            assert row2.short_name == "DHKT2"
            assert row2.institution_type == "college"

            await _cleanup(session)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_institution_import_upserts_by_name_when_no_code():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)

            workbook = _make_xlsx(
                INSTITUTION_COLUMNS,
                [["", TEST_INSTITUTION_NAME_NO_CODE, "", "", "", "", "1"]],
            )
            result = await process_institution_import(session, workbook)
            await session.commit()
            assert result.success == 1, result.errors
            first_id = result.created_ids[0]

            # Import lại cùng tên (không mã) -> phải nhận diện qua tên và update, không tạo trùng
            workbook2 = _make_xlsx(
                INSTITUTION_COLUMNS,
                [["", TEST_INSTITUTION_NAME_NO_CODE, "CDKT", "", "", "", "0"]],
            )
            result2 = await process_institution_import(session, workbook2)
            await session.commit()
            assert result2.success == 1, result2.errors
            assert result2.created_ids[0] == first_id

            row = (
                await session.execute(select(EducationalInstitution).where(EducationalInstitution.id == first_id))
            ).scalar_one()
            assert row.short_name == "CDKT"
            assert row.is_active is False

            await _cleanup(session)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_institution_import_validates_required_name_and_type():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)

            workbook = _make_xlsx(
                INSTITUTION_COLUMNS,
                [
                    ["", "", "", "", "", "", "1"],
                    ["", "Trường hợp lệ để loại hình sai", "", "khong_ton_tai", "", "", "1"],
                ],
            )
            result = await process_institution_import(session, workbook)
            assert result.total == 2
            assert result.failed == 2
            assert result.success == 0
            assert any(e.column == "Tên trường" and "bắt buộc" in e.message for e in result.errors)
            assert any(e.column == "Loại hình" for e in result.errors)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_major_import_creates_then_upserts_by_code():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)

            workbook = _make_xlsx(MAJOR_COLUMNS, [[TEST_MAJOR_CODE, TEST_MAJOR_NAME, "Kỹ thuật", "1"]])
            result = await process_major_import(session, workbook)
            await session.commit()
            assert result.success == 1, result.errors
            first_id = result.created_ids[0]

            workbook2 = _make_xlsx(MAJOR_COLUMNS, [[TEST_MAJOR_CODE, TEST_MAJOR_NAME, "Kinh tế", "1"]])
            result2 = await process_major_import(session, workbook2)
            await session.commit()
            assert result2.success == 1, result2.errors
            assert result2.created_ids[0] == first_id

            row = (await session.execute(select(EducationMajor).where(EducationMajor.id == first_id))).scalar_one()
            assert row.major_group == "Kinh tế"

            await _cleanup(session)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_major_import_upserts_by_name_when_no_code():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)

            workbook = _make_xlsx(MAJOR_COLUMNS, [["", TEST_MAJOR_NAME_NO_CODE, "", "1"]])
            result = await process_major_import(session, workbook)
            await session.commit()
            assert result.success == 1, result.errors
            first_id = result.created_ids[0]

            workbook2 = _make_xlsx(MAJOR_COLUMNS, [["", TEST_MAJOR_NAME_NO_CODE, "Nhóm mới", "0"]])
            result2 = await process_major_import(session, workbook2)
            await session.commit()
            assert result2.success == 1, result2.errors
            assert result2.created_ids[0] == first_id

            row = (await session.execute(select(EducationMajor).where(EducationMajor.id == first_id))).scalar_one()
            assert row.major_group == "Nhóm mới"
            assert row.is_active is False

            await _cleanup(session)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_major_import_validates_required_name():
    engine, session_factory = _make_engine_and_sessionmaker()
    try:
        async with session_factory() as session:
            await _cleanup(session)

            workbook = _make_xlsx(MAJOR_COLUMNS, [["", "", "", "1"]])
            result = await process_major_import(session, workbook)
            assert result.total == 1
            assert result.failed == 1
            assert result.success == 0
            assert any(e.column == "Tên chuyên ngành" and "bắt buộc" in e.message for e in result.errors)
    finally:
        await engine.dispose()
