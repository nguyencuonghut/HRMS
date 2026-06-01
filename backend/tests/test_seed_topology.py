"""Regression tests cho topology seeder production."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds import bootstrap, education_catalog, rbac, required


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _scalar(sql: str, **params) -> int:
    async with _make_session()() as s:
        return (await s.execute(text(sql), params)).scalar()


async def test_required_and_bootstrap_do_not_seed_sample_catalogs():
    tracked = {
        "skills": "SELECT COUNT(*) FROM skills",
        "certificates": "SELECT COUNT(*) FROM certificates",
        "contract_templates": "SELECT COUNT(*) FROM contract_templates",
        "contract_template_placeholders": "SELECT COUNT(*) FROM contract_template_placeholders",
    }
    before = {key: await _scalar(sql) for key, sql in tracked.items()}

    async with _make_session()() as session:
        await required.run(session)
        await bootstrap.run(session)
        await session.commit()

    after = {key: await _scalar(sql) for key, sql in tracked.items()}
    assert after == before


async def test_required_education_seed_does_not_seed_sample_education_catalogs():
    tracked = {
        "educational_institutions": "SELECT COUNT(*) FROM educational_institutions",
        "education_majors": "SELECT COUNT(*) FROM education_majors",
    }
    before = {key: await _scalar(sql) for key, sql in tracked.items()}

    async with _make_session()() as session:
        await education_catalog.seed_required_education_catalog(session)
        await session.commit()

    after = {key: await _scalar(sql) for key, sql in tracked.items()}
    assert after == before


async def test_rbac_core_does_not_seed_local_users():
    sql = """
        SELECT COUNT(*) FROM users
        WHERE email IN (
            'admin@hrms.local',
            'hrmanager@hrms.local',
            'hrofficer@hrms.local',
            'linemanager@hrms.local',
            'finance@hrms.local'
        )
    """
    before = await _scalar(sql)

    async with _make_session()() as session:
        await rbac.run(session, include_users=False)
        await session.commit()

    after = await _scalar(sql)
    assert after == before
