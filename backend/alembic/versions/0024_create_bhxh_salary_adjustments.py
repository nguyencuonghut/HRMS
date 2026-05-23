"""Create bhxh_salary_adjustments table

Revision ID: 0024
Revises: 0023
Create Date: 2026-05-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bhxh_salary_adjustments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("decision_number", sa.String(length=100), nullable=True),
        sa.Column("old_basis_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("new_basis_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("insurance_change_event_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["insurance_change_event_id"], ["insurance_change_events.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "old_basis_amount > 0 AND new_basis_amount > 0",
            name="ck_bsa_amounts_positive",
        ),
        sa.CheckConstraint(
            "old_basis_amount != new_basis_amount",
            name="ck_bsa_amounts_different",
        ),
    )
    op.create_index("ix_bsa_employee_id", "bhxh_salary_adjustments", ["employee_id"])
    op.create_index("ix_bsa_effective_date", "bhxh_salary_adjustments", ["effective_date"])
    op.create_index("ix_bsa_created_at", "bhxh_salary_adjustments", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_bsa_created_at", table_name="bhxh_salary_adjustments")
    op.drop_index("ix_bsa_effective_date", table_name="bhxh_salary_adjustments")
    op.drop_index("ix_bsa_employee_id", table_name="bhxh_salary_adjustments")
    op.drop_table("bhxh_salary_adjustments")
