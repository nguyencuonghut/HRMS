"""Integration tests cho seed danh mục học vấn."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds import education_catalog


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _scalar(sql: str, **params) -> int:
    async with _make_session()() as s:
        return (await s.execute(text(sql), params)).scalar()


async def test_required_education_levels_seed_is_idempotent():
    async with _make_session()() as session:
        await education_catalog.seed_required_education_catalog(session)
        await session.commit()
        await education_catalog.seed_required_education_catalog(session)
        await session.commit()

    count = await _scalar("SELECT COUNT(*) FROM education_levels")
    assert count == 8


async def test_sample_education_catalog_seed_is_idempotent():
    async with _make_session()() as session:
        await education_catalog.seed_sample_education_catalog(session)
        await session.commit()
        await education_catalog.seed_sample_education_catalog(session)
        await session.commit()

    institutions = await _scalar("SELECT COUNT(*) FROM educational_institutions")
    majors = await _scalar("SELECT COUNT(*) FROM education_majors")
    assert institutions == 12
    assert majors == 22


async def test_domain_relevant_education_seed_rows_exist():
    feed_major = await _scalar(
        "SELECT COUNT(*) FROM education_majors WHERE code = 'feed_nutrition' AND name = 'Dinh dưỡng và thức ăn chăn nuôi'"
    )
    veterinary_major = await _scalar(
        "SELECT COUNT(*) FROM education_majors WHERE code = 'veterinary_medicine' AND name = 'Thú y'"
    )
    xnk_major = await _scalar(
        "SELECT COUNT(*) FROM education_majors WHERE code = 'import_export' AND name = 'Xuất nhập khẩu'"
    )
    vnua = await _scalar(
        "SELECT COUNT(*) FROM educational_institutions WHERE code = 'VNUA' AND name = 'Học viện Nông nghiệp Việt Nam'"
    )
    vnuf = await _scalar(
        "SELECT COUNT(*) FROM educational_institutions WHERE code = 'VNUF' AND name = 'Trường Đại học Lâm nghiệp'"
    )
    ntu = await _scalar(
        "SELECT COUNT(*) FROM educational_institutions WHERE code = 'NTU' AND name = 'Trường Đại học Nha Trang'"
    )

    assert feed_major == 1
    assert veterinary_major == 1
    assert xnk_major == 1
    assert vnua == 1
    assert vnuf == 1
    assert ntu == 1
