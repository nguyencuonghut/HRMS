"""Add rule fields to leave_types

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leave_types", sa.Column("count_public_holidays",  sa.Boolean(),  nullable=False, server_default="true"))
    op.add_column("leave_types", sa.Column("max_days_per_year",       sa.Integer(),  nullable=True))
    op.add_column("leave_types", sa.Column("max_consecutive_days",    sa.Integer(),  nullable=True))
    op.add_column("leave_types", sa.Column("min_advance_days",        sa.Integer(),  nullable=False, server_default="0"))
    op.add_column("leave_types", sa.Column("carryover_allowed",       sa.Boolean(),  nullable=False, server_default="false"))
    op.add_column("leave_types", sa.Column("carryover_cutoff_month",  sa.Integer(),  nullable=False, server_default="3"))


def downgrade() -> None:
    op.drop_column("leave_types", "carryover_cutoff_month")
    op.drop_column("leave_types", "carryover_allowed")
    op.drop_column("leave_types", "min_advance_days")
    op.drop_column("leave_types", "max_consecutive_days")
    op.drop_column("leave_types", "max_days_per_year")
    op.drop_column("leave_types", "count_public_holidays")
