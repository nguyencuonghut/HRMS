"""Create employee insurance profiles and compatibility backfill

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_insurance_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("bhxh_code", sa.String(length=20), nullable=True),
        sa.Column("bhyt_initial_clinic_name", sa.String(length=255), nullable=True),
        sa.Column("company_bhxh_joined_date", sa.Date(), nullable=True),
        sa.Column("participation_status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("status_effective_from", sa.Date(), nullable=True),
        sa.Column("status_note", sa.Text(), nullable=True),
        sa.Column("insurance_basis_source", sa.String(length=20), nullable=False, server_default="contract"),
        sa.Column("insurance_basis_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("insurance_policy_version_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["insurance_policy_version_id"],
            ["insurance_policy_versions.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("employee_id", name="uq_employee_insurance_profiles_employee_id"),
        sa.CheckConstraint(
            "participation_status IN ('active', 'paused', 'stopped')",
            name="ck_employee_insurance_profiles_participation_status",
        ),
        sa.CheckConstraint(
            "insurance_basis_source IN ('contract', 'computed', 'manual_fixed')",
            name="ck_employee_insurance_profiles_basis_source",
        ),
    )
    op.create_index(
        "ix_employee_insurance_profiles_employee_id",
        "employee_insurance_profiles",
        ["employee_id"],
        unique=True,
    )
    op.create_index(
        "ix_employee_insurance_profiles_participation_status",
        "employee_insurance_profiles",
        ["participation_status"],
        unique=False,
    )
    op.create_index(
        "ix_employee_insurance_profiles_company_bhxh_joined_date",
        "employee_insurance_profiles",
        ["company_bhxh_joined_date"],
        unique=False,
    )

    op.create_table(
        "employee_insurance_component_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_insurance_profile_id", sa.Integer(), nullable=False),
        sa.Column("component_code", sa.String(length=50), nullable=False),
        sa.Column("use_company_default", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("fixed_employee_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("fixed_employer_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("employer_advances_employee_part", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["employee_insurance_profile_id"],
            ["employee_insurance_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["component_code"],
            ["insurance_contribution_components.code"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "employee_insurance_profile_id",
            "component_code",
            name="uq_employee_insurance_component_override_profile_component",
        ),
        sa.CheckConstraint(
            "fixed_employee_amount IS NULL OR fixed_employee_amount >= 0",
            name="ck_employee_insurance_component_overrides_employee_non_negative",
        ),
        sa.CheckConstraint(
            "fixed_employer_amount IS NULL OR fixed_employer_amount >= 0",
            name="ck_employee_insurance_component_overrides_employer_non_negative",
        ),
        sa.CheckConstraint(
            "NOT use_company_default OR (fixed_employee_amount IS NULL AND fixed_employer_amount IS NULL)",
            name="ck_employee_insurance_component_overrides_default_vs_fixed",
        ),
    )
    op.create_index(
        "ix_employee_insurance_component_overrides_profile_id",
        "employee_insurance_component_overrides",
        ["employee_insurance_profile_id"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO employee_insurance_profiles (
                employee_id,
                bhxh_code,
                participation_status,
                insurance_basis_source,
                created_at,
                updated_at
            )
            SELECT
                employees.id,
                NULLIF(BTRIM(employees.bhxh_code), ''),
                CASE
                    WHEN employees.status = 'resigned' THEN 'stopped'
                    ELSE 'active'
                END,
                'contract',
                employees.created_at,
                employees.updated_at
            FROM employees
            ON CONFLICT (employee_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employee_insurance_component_overrides_profile_id",
        table_name="employee_insurance_component_overrides",
    )
    op.drop_table("employee_insurance_component_overrides")
    op.drop_index(
        "ix_employee_insurance_profiles_company_bhxh_joined_date",
        table_name="employee_insurance_profiles",
    )
    op.drop_index(
        "ix_employee_insurance_profiles_participation_status",
        table_name="employee_insurance_profiles",
    )
    op.drop_index(
        "ix_employee_insurance_profiles_employee_id",
        table_name="employee_insurance_profiles",
    )
    op.drop_table("employee_insurance_profiles")
