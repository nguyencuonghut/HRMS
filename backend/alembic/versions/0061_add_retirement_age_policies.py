"""add retirement age policies

Revision ID: 0061
Revises: 0060
Create Date: 2026-06-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0061"
down_revision: Union[str, None] = "0060"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "retirement_age_policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("legal_basis_summary", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_retirement_age_policies_effective_from",
        "retirement_age_policies",
        ["effective_from"],
        unique=False,
    )

    op.create_table(
        "retirement_age_policy_thresholds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("gender", sa.String(length=10), nullable=False),
        sa.Column("applicable_year", sa.SmallInteger(), nullable=False),
        sa.Column("age_years", sa.SmallInteger(), nullable=False),
        sa.Column("age_months", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["retirement_age_policies.id"],
            name="fk_retirement_age_policy_thresholds_policy",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "policy_id",
            "gender",
            "applicable_year",
            name="uq_retirement_age_policy_thresholds",
        ),
        sa.CheckConstraint(
            "gender IN ('male', 'female')",
            name="ck_retirement_age_policy_thresholds_gender",
        ),
        sa.CheckConstraint(
            "applicable_year >= 1900",
            name="ck_retirement_age_policy_thresholds_year",
        ),
        sa.CheckConstraint(
            "age_years >= 0",
            name="ck_retirement_age_policy_thresholds_age_years",
        ),
        sa.CheckConstraint(
            "age_months BETWEEN 0 AND 11",
            name="ck_retirement_age_policy_thresholds_age_months",
        ),
    )
    op.create_index(
        "ix_retirement_age_policy_thresholds_lookup",
        "retirement_age_policy_thresholds",
        ["policy_id", "gender", "applicable_year"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retirement_age_policy_thresholds_lookup",
        table_name="retirement_age_policy_thresholds",
    )
    op.drop_table("retirement_age_policy_thresholds")
    op.drop_index(
        "ix_retirement_age_policies_effective_from",
        table_name="retirement_age_policies",
    )
    op.drop_table("retirement_age_policies")
