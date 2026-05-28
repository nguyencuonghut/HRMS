"""add export tables

Revision ID: 0047
Revises: 0046
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_type", sa.String(length=100), nullable=False),
        sa.Column("format", sa.String(length=10), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_export_jobs_user_id", "export_jobs", ["user_id"])
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"])
    op.create_index("ix_export_jobs_created_at", "export_jobs", ["created_at"])

    op.create_table(
        "report_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("report_type", sa.String(length=100), nullable=False),
        sa.Column("format", sa.String(length=10), nullable=False, server_default="xlsx"),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "name", name="uq_report_templates_user_name"),
    )
    op.create_index("ix_report_templates_user_id", "report_templates", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_report_templates_user_id", table_name="report_templates")
    op.drop_table("report_templates")
    op.drop_index("ix_export_jobs_created_at", table_name="export_jobs")
    op.drop_index("ix_export_jobs_status", table_name="export_jobs")
    op.drop_index("ix_export_jobs_user_id", table_name="export_jobs")
    op.drop_table("export_jobs")
