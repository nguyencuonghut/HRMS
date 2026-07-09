from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds import bootstrap, required, rbac, sample
from app.seeds.control_branch_sample import seed_control_branch_employee_domain_data
from app.services import dashboard_service


CONTROL_EMAILS = [
    "taquocminh.ks@gmail.com",
    "nguyenthilan.ksnb@gmail.com",
    "phamduchoa.ksnb@gmail.com",
    "leminhtrang.it@gmail.com",
    "vuhoangson.it@gmail.com",
]


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def test_sample_seed_adds_full_control_branch_cross_module_data():
    async with _make_session()() as session:
        await required.run(session)
        await bootstrap.run(session)
        await rbac.run(session, include_users=True)
        await sample.run(session)
        await session.commit()

    async with _make_session()() as session:
        email_params = {f"email_{index}": email for index, email in enumerate(CONTROL_EMAILS, start=1)}
        in_clause = ", ".join(f":email_{index}" for index in range(1, len(CONTROL_EMAILS) + 1))
        employee_ids = (
            await session.execute(
                text(
                    f"""
                    SELECT id
                    FROM employees
                    WHERE personal_email IN ({in_clause})
                    ORDER BY employee_seq
                    """
                ),
                email_params,
            )
        ).scalars().all()
        assert len(employee_ids) == 5

        counts = {
            "contracts": (
                await session.execute(
                    text("SELECT COUNT(*) FROM employee_contracts WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
            "leave_entitlements": (
                await session.execute(
                    text("SELECT COUNT(*) FROM leave_entitlements WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
            "leave_records": (
                await session.execute(
                    text("SELECT COUNT(*) FROM leave_records WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
            "insurance_profiles": (
                await session.execute(
                    text("SELECT COUNT(*) FROM employee_insurance_profiles WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
            "insurance_changes": (
                await session.execute(
                    text("SELECT COUNT(*) FROM insurance_change_events WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
            "rewards": (
                await session.execute(
                    text("SELECT COUNT(*) FROM employee_rewards WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
            "disciplines": (
                await session.execute(
                    text("SELECT COUNT(*) FROM employee_disciplines WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
            "training_records": (
                await session.execute(
                    text("SELECT COUNT(*) FROM employee_training_records WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
            "training_certificates": (
                await session.execute(
                    text("SELECT COUNT(*) FROM employee_training_certificates WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
            "kpi_monthly": (
                await session.execute(
                    text("SELECT COUNT(*) FROM employee_kpi_monthly WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
            "yearly_reviews": (
                await session.execute(
                    text("SELECT COUNT(*) FROM employee_yearly_reviews WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
            "hiring_decisions": (
                await session.execute(
                    text("SELECT COUNT(*) FROM hiring_decisions WHERE employee_id = ANY(:employee_ids)"),
                    {"employee_ids": employee_ids},
                )
            ).scalar_one(),
        }

        assert counts["contracts"] >= 5
        assert counts["leave_entitlements"] >= 5
        assert counts["leave_records"] >= 5
        assert counts["insurance_profiles"] == 5
        assert counts["insurance_changes"] >= 5
        assert counts["rewards"] >= 5
        assert counts["disciplines"] >= 5
        assert counts["training_records"] >= 5
        assert counts["training_certificates"] >= 5
        assert counts["kpi_monthly"] >= 15
        assert counts["yearly_reviews"] >= 5
        assert counts["hiring_decisions"] >= 5


async def test_control_branch_seed_supports_dashboard_residence_and_contract_mix():
    async with _make_session()() as session:
        await required.run(session)
        await bootstrap.run(session)
        await rbac.run(session, include_users=True)
        await sample.run(session)
        counts = await seed_control_branch_employee_domain_data(session)
        await session.commit()

        assert counts["contracts"] >= 0
        assert counts["employee_addresses"] >= 0

    async with _make_session()() as session:
        residence_rows = (
            await session.execute(
                text(
                    """
                    SELECT
                        SUM(
                            CASE
                                WHEN ea.new_province_unit_id IS NOT NULL
                                  OR ea.new_ward_unit_id IS NOT NULL
                                  OR ea.full_address_text ILIKE '%Ninh Bình%'
                                THEN 1 ELSE 0
                            END
                        ) AS in_province_count,
                        SUM(
                            CASE
                                WHEN ea.full_address_text ILIKE '%Hà Nội%'
                                  OR ea.full_address_text ILIKE '%Đắk Lắk%'
                                THEN 1 ELSE 0
                            END
                        ) AS out_province_count
                    FROM employee_addresses ea
                    JOIN employees e ON e.id = ea.employee_id
                    WHERE e.personal_email IN (
                        :email_1, :email_2, :email_3, :email_4, :email_5
                    )
                      AND ea.address_type = 'permanent'
                    """
                ),
                {
                    "email_1": CONTROL_EMAILS[0],
                    "email_2": CONTROL_EMAILS[1],
                    "email_3": CONTROL_EMAILS[2],
                    "email_4": CONTROL_EMAILS[3],
                    "email_5": CONTROL_EMAILS[4],
                },
            )
        ).one()

        contract_rows = (
            await session.execute(
                text(
                    """
                    SELECT cc.legal_contract_type, COUNT(*) AS count
                    FROM employee_contracts ec
                    JOIN employees e ON e.id = ec.employee_id
                    JOIN contract_categories cc ON cc.id = ec.contract_category_id
                    WHERE e.personal_email IN (
                        :email_1, :email_2, :email_3, :email_4, :email_5
                    )
                      AND ec.parent_contract_id IS NULL
                      AND ec.document_kind = 'labor_contract'
                      AND ec.status = 'active'
                    GROUP BY cc.legal_contract_type
                    """
                ),
                {
                    "email_1": CONTROL_EMAILS[0],
                    "email_2": CONTROL_EMAILS[1],
                    "email_3": CONTROL_EMAILS[2],
                    "email_4": CONTROL_EMAILS[3],
                    "email_5": CONTROL_EMAILS[4],
                },
            )
        ).all()

        contract_counts = {row[0]: row[1] for row in contract_rows}

        assert residence_rows[0] >= 3
        assert residence_rows[1] >= 2
        assert contract_counts["indefinite_term"] >= 3
        assert contract_counts["definite_term"] >= 2


async def test_sample_seed_adds_current_year_personnel_changes_for_dashboard_trend():
    report_year = date.today().year

    async with _make_session()() as session:
        await required.run(session)
        await bootstrap.run(session)
        await rbac.run(session, include_users=True)
        await sample.run(session)
        await session.commit()

    async with _make_session()() as session:
        trend = await dashboard_service.get_monthly_trend(session, year=report_year)
        hires_by_month = {item.month: item.new_hires for item in trend.monthly}
        resigned_by_month = {item.month: item.resigned_count for item in trend.monthly}

        assert hires_by_month[1] >= 1
        assert hires_by_month[3] >= 3
        assert hires_by_month[4] >= 1
        assert hires_by_month[6] >= 2
        assert hires_by_month[9] >= 1
        assert hires_by_month[11] >= 1

        assert resigned_by_month[2] >= 1
        assert resigned_by_month[5] >= 2
        assert resigned_by_month[8] >= 1
        assert resigned_by_month[12] >= 1

        assert max(hires_by_month.values()) >= 3
        assert max(resigned_by_month.values()) >= 2
