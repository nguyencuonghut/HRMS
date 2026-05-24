"""create employee_yearly_reviews table.

Revision ID: 0031
Revises: 0030
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_yearly_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("rating", sa.String(20), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("employee_id", "year", name="uq_employee_yearly_review_year"),
    )
    op.create_index("ix_employee_yearly_reviews_employee_id", "employee_yearly_reviews", ["employee_id"])
    op.create_index("ix_employee_yearly_reviews_year", "employee_yearly_reviews", ["year"])


def downgrade() -> None:
    op.drop_index("ix_employee_yearly_reviews_year", table_name="employee_yearly_reviews")
    op.drop_index("ix_employee_yearly_reviews_employee_id", table_name="employee_yearly_reviews")
    op.drop_table("employee_yearly_reviews")
