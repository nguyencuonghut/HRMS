"""add bhxh seniority settings

Revision ID: 0054
Revises: 0053
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0054"
down_revision: Union[str, None] = "0053"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bhxh_seniority_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("raise_month", sa.SmallInteger(), nullable=False),
        sa.Column("raise_day", sa.SmallInteger(), nullable=False),
        sa.Column("years_per_grade", sa.SmallInteger(), nullable=False),
        sa.Column("first_year_cutoff_month", sa.SmallInteger(), nullable=False),
        sa.Column("first_year_cutoff_day", sa.SmallInteger(), nullable=False),
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
        sa.CheckConstraint("raise_month BETWEEN 1 AND 12", name="ck_bhxh_seniority_settings_raise_month"),
        sa.CheckConstraint("raise_day BETWEEN 1 AND 31", name="ck_bhxh_seniority_settings_raise_day"),
        sa.CheckConstraint("years_per_grade >= 1", name="ck_bhxh_seniority_settings_years_per_grade"),
        sa.CheckConstraint(
            "first_year_cutoff_month BETWEEN 1 AND 12",
            name="ck_bhxh_seniority_settings_cutoff_month",
        ),
        sa.CheckConstraint(
            "first_year_cutoff_day BETWEEN 1 AND 31",
            name="ck_bhxh_seniority_settings_cutoff_day",
        ),
    )
    op.create_index(
        "ix_bhxh_seniority_settings_effective_from",
        "bhxh_seniority_settings",
        ["effective_from"],
    )


def downgrade() -> None:
    op.drop_index("ix_bhxh_seniority_settings_effective_from", table_name="bhxh_seniority_settings")
    op.drop_table("bhxh_seniority_settings")
