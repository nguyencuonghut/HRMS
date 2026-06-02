"""add document checklists

Revision ID: 0040
Revises: 0039
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_checklist_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("has_expiry", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("applies_to", sa.String(30), nullable=False, server_default="all"),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_document_checklist_type_code"),
    )

    op.create_table(
        "employee_document_checklists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("document_type_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="not_submitted"),
        sa.Column("submitted_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("waived_reason", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(300), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_checklist_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "document_type_id", name="uq_emp_doc_type"),
    )
    op.create_index("ix_emp_doc_checklist_employee", "employee_document_checklists", ["employee_id"])
    op.create_index("ix_emp_doc_checklist_status", "employee_document_checklists", ["status"])
    op.create_index(
        "ix_emp_doc_checklist_expiry",
        "employee_document_checklists",
        ["expires_at"],
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )

    # Danh mục mặc định chuyển sang app.seeds.document_checklist_types
    # để tách schema migration khỏi business catalog data.


def downgrade() -> None:
    op.drop_table("employee_document_checklists")
    op.drop_table("document_checklist_types")
