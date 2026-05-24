"""Add source_review_id to employee_rewards and employee_training_records.

Revision ID: 0032
Revises: 0031
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "employee_rewards",
        sa.Column(
            "source_review_id",
            sa.Integer(),
            sa.ForeignKey("employee_yearly_reviews.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_employee_rewards_source_review_id",
        "employee_rewards",
        ["source_review_id"],
    )

    op.add_column(
        "employee_training_records",
        sa.Column(
            "source_review_id",
            sa.Integer(),
            sa.ForeignKey("employee_yearly_reviews.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_employee_training_records_source_review_id",
        "employee_training_records",
        ["source_review_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_employee_training_records_source_review_id", table_name="employee_training_records")
    op.drop_column("employee_training_records", "source_review_id")

    op.drop_index("ix_employee_rewards_source_review_id", table_name="employee_rewards")
    op.drop_column("employee_rewards", "source_review_id")
