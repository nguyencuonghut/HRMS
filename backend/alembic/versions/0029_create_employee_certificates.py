"""create employee_certificates

Revision ID: 0029
Revises: 0028
Create Date: 2026-05-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_training_certificates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("certificate_name", sa.String(500), nullable=False),
        sa.Column("issuing_organization", sa.String(300), nullable=True),
        sa.Column("issued_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("related_course_id", sa.Integer(), sa.ForeignKey("training_courses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(300), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employee_training_certificates_employee_id", "employee_training_certificates", ["employee_id"])
    op.create_index("ix_employee_training_certificates_expiry_date", "employee_training_certificates", ["expiry_date"])


def downgrade() -> None:
    op.drop_index("ix_employee_training_certificates_expiry_date", table_name="employee_training_certificates")
    op.drop_index("ix_employee_training_certificates_employee_id", table_name="employee_training_certificates")
    op.drop_table("employee_training_certificates")
