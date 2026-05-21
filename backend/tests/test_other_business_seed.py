"""Integration tests cho seed danh mục nghiệp vụ khác."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds import other_business_catalog


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _scalar(sql: str, **params) -> int:
    async with _make_session()() as s:
        return (await s.execute(text(sql), params)).scalar()


async def test_required_other_business_catalog_seed_is_idempotent():
    async with _make_session()() as session:
        await other_business_catalog.seed_required_other_business_catalog(session)
        await session.commit()
        await other_business_catalog.seed_required_other_business_catalog(session)
        await session.commit()

    assert await _scalar("SELECT COUNT(*) FROM contract_categories") == len(other_business_catalog.CONTRACT_CATEGORIES)
    assert await _scalar("SELECT COUNT(*) FROM nationalities") == len(other_business_catalog.NATIONALITIES)
    assert await _scalar("SELECT COUNT(*) FROM ethnicities") == len(other_business_catalog.ETHNICITIES)
    assert await _scalar("SELECT COUNT(*) FROM religions") == len(other_business_catalog.RELIGIONS)
    assert await _scalar("SELECT COUNT(*) FROM banks") == len(other_business_catalog.BANKS)
    assert await _scalar("SELECT COUNT(*) FROM leave_types") == len(other_business_catalog.LEAVE_TYPES)


async def test_sample_other_business_catalog_seed_is_idempotent():
    async with _make_session()() as session:
        await other_business_catalog.seed_required_other_business_catalog(session)
        await other_business_catalog.seed_sample_other_business_catalog(session)
        await session.commit()
        await other_business_catalog.seed_sample_other_business_catalog(session)
        await session.commit()

    assert await _scalar("SELECT COUNT(*) FROM skills") == 10
    assert await _scalar("SELECT COUNT(*) FROM certificates") == 5
    assert await _scalar("SELECT COUNT(*) FROM contract_templates") == 4
    assert await _scalar("SELECT COUNT(*) FROM contract_template_placeholders") == 51


async def test_domain_relevant_other_business_seed_rows_exist():
    agribank = await _scalar(
        "SELECT COUNT(*) FROM banks WHERE code = 'AGRIBANK' AND short_name = 'Agribank'"
    )
    annual_leave = await _scalar(
        "SELECT COUNT(*) FROM leave_types WHERE code = 'annual_leave' AND is_paid_leave = true"
    )
    qa_qc = await _scalar(
        "SELECT COUNT(*) FROM skills WHERE code = 'qa_qc' AND name = 'QA/QC'"
    )
    customs_certificate = await _scalar(
        "SELECT COUNT(*) FROM certificates WHERE code = 'CUSTOMS_DECLARATION' AND name = 'Chứng chỉ nghiệp vụ khai báo hải quan'"
    )
    contract_template = await _scalar(
        "SELECT COUNT(*) FROM contract_templates WHERE code = 'ld_indefinite' AND version_no = 1"
    )
    fixed_term_template = await _scalar(
        """
        SELECT COUNT(*)
        FROM contract_templates
        WHERE code = 'ld_definite_12m'
          AND version_no = 1
          AND storage_path = 'app/seeds/data/fixed_term.docx'
          AND file_checksum IS NOT NULL
        """
    )
    probation_template = await _scalar(
        """
        SELECT COUNT(*)
        FROM contract_templates
        WHERE code = 'probation_standard'
          AND version_no = 1
          AND storage_path = 'app/seeds/data/probation.docx'
          AND file_checksum IS NOT NULL
        """
    )
    employee_full_name_placeholder = await _scalar(
        """
        SELECT COUNT(*)
        FROM contract_template_placeholders p
        JOIN contract_templates t ON t.id = p.template_id
        WHERE t.code = 'ld_indefinite'
          AND t.version_no = 1
          AND p.placeholder_key = 'employee.full_name'
        """
    )

    assert agribank == 1
    assert annual_leave == 1
    assert qa_qc == 1
    assert customs_certificate == 1
    assert contract_template == 1
    assert fixed_term_template == 1
    assert probation_template == 1
    assert employee_full_name_placeholder == 1
