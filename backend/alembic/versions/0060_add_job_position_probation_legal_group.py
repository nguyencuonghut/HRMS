"""add job position probation legal group

Revision ID: 0060
Revises: 0059
Create Date: 2026-06-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0060"
down_revision: Union[str, None] = "0059"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_positions",
        sa.Column("probation_legal_group", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_job_positions_probation_legal_group",
        "job_positions",
        ["probation_legal_group"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_positions_probation_legal_group", table_name="job_positions")
    op.drop_column("job_positions", "probation_legal_group")
