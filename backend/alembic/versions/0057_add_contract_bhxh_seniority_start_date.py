"""add contract bhxh seniority start date

Revision ID: 0057
Revises: 0056
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "employee_contracts",
        sa.Column("bhxh_seniority_start_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("employee_contracts", "bhxh_seniority_start_date")
