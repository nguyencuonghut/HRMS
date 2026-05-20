"""Create shared insurance foundation tables

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "insurance_contribution_components",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name_vi", sa.String(length=255), nullable=False),
        sa.Column("insurance_kind", sa.String(length=30), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("code"),
    )

    op.create_table(
        "insurance_policy_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("legal_basis_summary", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("company_region", sa.SmallInteger(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("company_region BETWEEN 1 AND 4", name="ck_insurance_policy_versions_company_region"),
    )
    op.create_index("ix_insurance_policy_versions_code", "insurance_policy_versions", ["code"], unique=True)
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_insurance_policy_versions_active
            ON insurance_policy_versions ((1))
            WHERE is_active = TRUE
            """
        )
    )

    op.create_table(
        "insurance_policy_component_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_version_id", sa.Integer(), nullable=False),
        sa.Column("component_code", sa.String(length=50), nullable=False),
        sa.Column("employee_rate_percent", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("employer_rate_percent", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("employer_advances_employee_part", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["insurance_policy_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["component_code"], ["insurance_contribution_components.code"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "policy_version_id",
            "component_code",
            name="uq_insurance_policy_component_rates_policy_component",
        ),
        sa.CheckConstraint("employee_rate_percent >= 0", name="ck_insurance_policy_component_rates_employee_non_negative"),
        sa.CheckConstraint("employer_rate_percent >= 0", name="ck_insurance_policy_component_rates_employer_non_negative"),
    )
    op.create_index(
        "ix_insurance_policy_component_rates_policy_version_id",
        "insurance_policy_component_rates",
        ["policy_version_id"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id,
                       effective_from,
                       ROW_NUMBER() OVER (
                           ORDER BY effective_from DESC, id DESC
                       ) AS rn
                FROM company_bhxh_region
                WHERE effective_to IS NULL
            )
            UPDATE company_bhxh_region AS target
            SET effective_to = ranked.effective_from
            FROM ranked
            WHERE target.id = ranked.id
              AND ranked.rn > 1
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_company_bhxh_region_active
            ON company_bhxh_region ((1))
            WHERE effective_to IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO insurance_contribution_components (code, name_vi, insurance_kind, sort_order, is_active)
            VALUES
              ('RETIREMENT_SURVIVOR', 'BHXH - Hưu trí và Tử tuất', 'bhxh', 10, TRUE),
              ('SICKNESS_MATERNITY', 'BHXH - Ốm đau và Thai sản', 'bhxh', 20, TRUE),
              ('OCC_ACCIDENT_DISEASE', 'BHTNLĐ-BNN - Tai nạn lao động và Bệnh nghề nghiệp', 'bhxh', 30, TRUE),
              ('HEALTH', 'BHYT - Y tế', 'bhyt', 40, TRUE),
              ('UNEMPLOYMENT', 'BHTN - Thất nghiệp', 'bhtn', 50, TRUE)
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO insurance_policy_versions (
                code, name, legal_basis_summary, effective_from, effective_to, is_active, company_region, note
            )
            VALUES (
                'VN_STANDARD_2026_01_01',
                'Mặc định theo quy định đang áp dụng',
                'Seed mặc định theo bộ tỷ lệ BHXH/BHYT/BHTN đang dùng tại thời điểm triển khai; cần rà soát khi pháp luật thay đổi.',
                DATE '2026-01-01',
                NULL,
                TRUE,
                COALESCE((SELECT region FROM company_bhxh_region WHERE effective_to IS NULL ORDER BY effective_from DESC, id DESC LIMIT 1), 3),
                'Seed mặc định Slice 0'
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO insurance_policy_component_rates (
                policy_version_id, component_code, employee_rate_percent, employer_rate_percent, employer_advances_employee_part, is_active
            )
            SELECT policy.id, component.code,
                   CASE component.code
                     WHEN 'RETIREMENT_SURVIVOR' THEN 8.0
                     WHEN 'HEALTH' THEN 1.5
                     WHEN 'UNEMPLOYMENT' THEN 1.0
                     ELSE 0.0
                   END,
                   CASE component.code
                     WHEN 'RETIREMENT_SURVIVOR' THEN 14.0
                     WHEN 'SICKNESS_MATERNITY' THEN 3.0
                     WHEN 'OCC_ACCIDENT_DISEASE' THEN 0.5
                     WHEN 'HEALTH' THEN 3.0
                     WHEN 'UNEMPLOYMENT' THEN 1.0
                     ELSE 0.0
                   END,
                   FALSE,
                   TRUE
            FROM insurance_policy_versions policy
            JOIN insurance_contribution_components component ON 1 = 1
            WHERE policy.code = 'VN_STANDARD_2026_01_01'
            """
        )
    )


def downgrade() -> None:
    op.drop_index("uq_company_bhxh_region_active", table_name="company_bhxh_region")
    op.drop_index("ix_insurance_policy_component_rates_policy_version_id", table_name="insurance_policy_component_rates")
    op.drop_table("insurance_policy_component_rates")
    op.drop_index("uq_insurance_policy_versions_active", table_name="insurance_policy_versions")
    op.drop_index("ix_insurance_policy_versions_code", table_name="insurance_policy_versions")
    op.drop_table("insurance_policy_versions")
    op.drop_table("insurance_contribution_components")
