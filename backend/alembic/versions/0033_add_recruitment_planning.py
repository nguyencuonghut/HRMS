"""add recruitment planning tables (headcount_plans, job_requisitions, recruitment_budget_items).

Revision ID: 0033
Revises: 0032
Create Date: 2026-05-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "headcount_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column(
            "department_id",
            sa.Integer(),
            sa.ForeignKey("departments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "job_position_id",
            sa.Integer(),
            sa.ForeignKey("job_positions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("current_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("planned_count", sa.SmallInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("year", "department_id", "job_position_id", name="uq_headcount_plan_year_dept_pos"),
    )
    op.create_index("ix_headcount_plans_year", "headcount_plans", ["year"])
    op.create_index("ix_headcount_plans_department_id", "headcount_plans", ["department_id"])

    op.create_table(
        "job_requisitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column(
            "job_position_id",
            sa.Integer(),
            sa.ForeignKey("job_positions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "department_id",
            sa.Integer(),
            sa.ForeignKey("departments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "headcount_plan_id",
            sa.Integer(),
            sa.ForeignKey("headcount_plans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("quantity", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("quantity_remaining", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("reason_type", sa.String(20), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("salary_min", sa.Numeric(15, 2), nullable=True),
        sa.Column("salary_max", sa.Numeric(15, 2), nullable=True),
        sa.Column("jd_description", sa.Text(), nullable=True),
        sa.Column("jd_requirements", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "submitted_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "approved_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_note", sa.Text(), nullable=True),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_jr_department_id", "job_requisitions", ["department_id"])
    op.create_index("ix_jr_job_position_id", "job_requisitions", ["job_position_id"])
    op.create_index("ix_jr_status", "job_requisitions", ["status"])
    op.create_index("ix_jr_code", "job_requisitions", ["code"])

    op.create_table(
        "recruitment_budget_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_requisition_id",
            sa.Integer(),
            sa.ForeignKey("job_requisitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("estimated_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("actual_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_budget_items_jr_id", "recruitment_budget_items", ["job_requisition_id"])


def downgrade() -> None:
    op.drop_index("ix_budget_items_jr_id", table_name="recruitment_budget_items")
    op.drop_table("recruitment_budget_items")

    op.drop_index("ix_jr_code", table_name="job_requisitions")
    op.drop_index("ix_jr_status", table_name="job_requisitions")
    op.drop_index("ix_jr_job_position_id", table_name="job_requisitions")
    op.drop_index("ix_jr_department_id", table_name="job_requisitions")
    op.drop_table("job_requisitions")

    op.drop_index("ix_headcount_plans_department_id", table_name="headcount_plans")
    op.drop_index("ix_headcount_plans_year", table_name="headcount_plans")
    op.drop_table("headcount_plans")
