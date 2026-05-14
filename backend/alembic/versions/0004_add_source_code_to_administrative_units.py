"""Add source_code to administrative_units

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "administrative_units",
        sa.Column("source_code", sa.String(length=20), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE administrative_units
            SET source_code = code
            WHERE source_code IS NULL
            """
        )
    )
    op.create_index(
        "ix_admin_units_source_code",
        "administrative_units",
        ["source_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_admin_units_source_code", table_name="administrative_units")
    op.drop_column("administrative_units", "source_code")
