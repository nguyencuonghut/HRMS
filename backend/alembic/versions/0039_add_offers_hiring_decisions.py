"""add offers and hiring_decisions tables.

Revision ID: 0039
Revises: 0038
Create Date: 2026-05-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("job_requisition_id", sa.Integer(), nullable=False),
        sa.Column("job_position_id", sa.Integer(), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("proposed_start_date", sa.Date(), nullable=False),
        sa.Column("probation_salary", sa.Numeric(15, 2), nullable=False),
        sa.Column("official_salary", sa.Numeric(15, 2), nullable=False),
        sa.Column("probation_days", sa.SmallInteger(), nullable=False),
        sa.Column("benefits_note", sa.Text(), nullable=True),
        sa.Column("offer_file_path", sa.String(500), nullable=True),
        sa.Column("offer_file_name", sa.String(300), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("negotiation_note", sa.Text(), nullable=True),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["application_id"], ["candidate_applications.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_requisition_id"], ["job_requisitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_position_id"], ["job_positions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_offers_application", "offers", ["application_id"])
    op.create_index("ix_offers_status", "offers", ["status"])

    op.create_table(
        "hiring_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("job_requisition_id", sa.Integer(), nullable=False),
        sa.Column("decision_number", sa.String(50), nullable=True),
        sa.Column("signed_date", sa.Date(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("job_position_id", sa.Integer(), nullable=False),
        sa.Column("job_title_id", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("probation_salary", sa.Numeric(15, 2), nullable=False),
        sa.Column("official_salary", sa.Numeric(15, 2), nullable=False),
        sa.Column("probation_days", sa.SmallInteger(), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(300), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_requisition_id"], ["job_requisitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_position_id"], ["job_positions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_title_id"], ["job_titles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("offer_id", name="uq_hiring_decision_offer"),
    )
    op.create_index("ix_hiring_decisions_offer", "hiring_decisions", ["offer_id"])
    op.create_index("ix_hiring_decisions_employee", "hiring_decisions", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_hiring_decisions_employee", table_name="hiring_decisions")
    op.drop_index("ix_hiring_decisions_offer", table_name="hiring_decisions")
    op.drop_table("hiring_decisions")

    op.drop_index("ix_offers_status", table_name="offers")
    op.drop_index("ix_offers_application", table_name="offers")
    op.drop_table("offers")
