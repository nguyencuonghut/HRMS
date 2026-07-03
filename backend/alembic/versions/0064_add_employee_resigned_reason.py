"""add employee resigned reason fields

Revision ID: 0064
Revises: 0063
Create Date: 2026-07-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0064"
down_revision: Union[str, None] = "0063"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("resigned_reason_type", sa.String(length=50), nullable=True))
    op.add_column("employees", sa.Column("resigned_reason_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "resigned_reason_note")
    op.drop_column("employees", "resigned_reason_type")
