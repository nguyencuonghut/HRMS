"""Create education catalog tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "education_levels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("rank_no", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_education_levels_code", "education_levels", ["code"], unique=True)
    op.create_index("ix_education_levels_rank_no", "education_levels", ["rank_no"], unique=True)
    op.create_index("ix_education_levels_normalized_name", "education_levels", ["normalized_name"], unique=False)
    op.create_index("ix_education_levels_active", "education_levels", ["is_active"], unique=False)

    op.create_table(
        "educational_institutions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=100), nullable=True),
        sa.Column("institution_type", sa.String(length=50), nullable=True),
        sa.Column("country_code", sa.String(length=10), nullable=True),
        sa.Column("province_code", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_educational_institutions_code", "educational_institutions", ["code"], unique=True)
    op.create_index(
        "ix_educational_institutions_normalized_name",
        "educational_institutions",
        ["normalized_name"],
        unique=False,
    )
    op.create_index(
        "ix_educational_institutions_type_active",
        "educational_institutions",
        ["institution_type", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_educational_institutions_country_code",
        "educational_institutions",
        ["country_code"],
        unique=False,
    )
    op.create_index(
        "ix_educational_institutions_province_code",
        "educational_institutions",
        ["province_code"],
        unique=False,
    )

    op.create_table(
        "education_majors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("major_group", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_education_majors_code", "education_majors", ["code"], unique=True)
    op.create_index("ix_education_majors_normalized_name", "education_majors", ["normalized_name"], unique=False)
    op.create_index("ix_education_majors_group_active", "education_majors", ["major_group", "is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_education_majors_group_active", table_name="education_majors")
    op.drop_index("ix_education_majors_normalized_name", table_name="education_majors")
    op.drop_index("ix_education_majors_code", table_name="education_majors")
    op.drop_table("education_majors")

    op.drop_index("ix_educational_institutions_province_code", table_name="educational_institutions")
    op.drop_index("ix_educational_institutions_country_code", table_name="educational_institutions")
    op.drop_index("ix_educational_institutions_type_active", table_name="educational_institutions")
    op.drop_index("ix_educational_institutions_normalized_name", table_name="educational_institutions")
    op.drop_index("ix_educational_institutions_code", table_name="educational_institutions")
    op.drop_table("educational_institutions")

    op.drop_index("ix_education_levels_active", table_name="education_levels")
    op.drop_index("ix_education_levels_normalized_name", table_name="education_levels")
    op.drop_index("ix_education_levels_rank_no", table_name="education_levels")
    op.drop_index("ix_education_levels_code", table_name="education_levels")
    op.drop_table("education_levels")
