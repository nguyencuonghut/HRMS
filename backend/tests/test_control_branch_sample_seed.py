from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds import bootstrap, required, rbac, sample


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
