"""create employee_kpi_monthly

Revision ID: 0030
Revises: 0029
Create Date: 2026-05-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_kpi_monthly",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("month", sa.SmallInteger(), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "year", "month", name="uq_employee_kpi_year_month"),
    )
    op.create_index("ix_employee_kpi_monthly_employee_id", "employee_kpi_monthly", ["employee_id"])
    op.create_index("ix_employee_kpi_monthly_year_month", "employee_kpi_monthly", ["year", "month"])


def downgrade() -> None:
    op.drop_index("ix_employee_kpi_monthly_year_month", table_name="employee_kpi_monthly")
    op.drop_index("ix_employee_kpi_monthly_employee_id", table_name="employee_kpi_monthly")
    op.drop_table("employee_kpi_monthly")
