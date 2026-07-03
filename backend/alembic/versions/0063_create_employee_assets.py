"""create employee assets table

Revision ID: 0063
Revises: 0062
Create Date: 2026-07-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0063"
down_revision: Union[str, None] = "0062"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("asset_name", sa.String(length=200), nullable=False),
        sa.Column("asset_type", sa.String(length=50), nullable=False),
        sa.Column("handover_date", sa.Date(), nullable=False),
        sa.Column("return_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="allocated"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name="fk_employee_assets_employee",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_employee_assets_employee_id",
        "employee_assets",
        ["employee_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_employee_assets_employee_id", table_name="employee_assets")
    op.drop_table("employee_assets")
