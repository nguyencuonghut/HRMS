"""VNPT compat: add bhxh_code to ethnicities, create bhyt_clinics, add ethnicity snapshot

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Gap 1: thêm bhxh_code vào ethnicities (mã 2 chữ số VNPT) ─────────
    op.add_column(
        "ethnicities",
        sa.Column("bhxh_code", sa.String(length=10), nullable=True),
    )
    op.create_unique_constraint("uq_ethnicities_bhxh_code", "ethnicities", ["bhxh_code"])

    # ── Gap 3: bảng danh mục bệnh viện KCB ───────────────────────────────
    op.create_table(
        "bhyt_clinics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("province_code", sa.String(length=10), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_bhyt_clinics_code"),
    )
    op.create_index("ix_bhyt_clinics_code", "bhyt_clinics", ["code"])
    op.create_index("ix_bhyt_clinics_province_code", "bhyt_clinics", ["province_code"])

    # ── Gap 4: thêm ethnicity snapshot vào insurance_change_events ────────
    op.add_column(
        "insurance_change_events",
        sa.Column("ethnicity_bhxh_code_snapshot", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("insurance_change_events", "ethnicity_bhxh_code_snapshot")

    op.drop_index("ix_bhyt_clinics_province_code", table_name="bhyt_clinics")
    op.drop_index("ix_bhyt_clinics_code", table_name="bhyt_clinics")
    op.drop_table("bhyt_clinics")

    op.drop_constraint("uq_ethnicities_bhxh_code", "ethnicities", type_="unique")
    op.drop_column("ethnicities", "bhxh_code")
