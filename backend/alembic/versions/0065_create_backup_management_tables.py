"""create backup management tables

Revision ID: 0065
Revises: 0064
Create Date: 2026-07-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0065"
down_revision: Union[str, None] = "0064"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backup_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(length=50), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cron_expression", sa.String(length=100), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("source_endpoint", sa.String(length=255), nullable=True),
        sa.Column("source_bucket", sa.String(length=255), nullable=True),
        sa.Column("source_secure", sa.Boolean(), nullable=True),
        sa.Column("target_endpoint", sa.String(length=255), nullable=True),
        sa.Column("target_bucket", sa.String(length=255), nullable=False, server_default="hrms-backup"),
        sa.Column("target_prefix", sa.String(length=255), nullable=True),
        sa.Column("target_secure", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_emails", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("secret_source", sa.String(length=50), nullable=False, server_default="env"),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_validation_status", sa.String(length=50), nullable=True),
        sa.Column("last_validation_error", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_backup_configs_kind", "backup_configs", ["kind"])

    op.create_table(
        "backup_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("trigger", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("artifact_key", sa.String(length=500), nullable=True),
        sa.Column("artifact_bucket", sa.String(length=255), nullable=True),
        sa.Column("artifact_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("object_count", sa.BigInteger(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("log_excerpt", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_backup_jobs_kind", "backup_jobs", ["kind"])
    op.create_index("ix_backup_jobs_status", "backup_jobs", ["status"])
    op.create_index("ix_backup_jobs_created_at", "backup_jobs", ["created_at"])

    op.create_table(
        "restore_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("db_artifact_key", sa.String(length=500), nullable=True),
        sa.Column("object_snapshot_key", sa.String(length=500), nullable=True),
        sa.Column("mode", sa.String(length=100), nullable=False),
        sa.Column("target_db_name", sa.String(length=255), nullable=True),
        sa.Column("target_bucket", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("requested_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("confirmation_text", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_restore_requests_kind", "restore_requests", ["kind"])
    op.create_index("ix_restore_requests_status", "restore_requests", ["status"])
    op.create_index("ix_restore_requests_created_at", "restore_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_restore_requests_created_at", table_name="restore_requests")
    op.drop_index("ix_restore_requests_status", table_name="restore_requests")
    op.drop_index("ix_restore_requests_kind", table_name="restore_requests")
    op.drop_table("restore_requests")

    op.drop_index("ix_backup_jobs_created_at", table_name="backup_jobs")
    op.drop_index("ix_backup_jobs_status", table_name="backup_jobs")
    op.drop_index("ix_backup_jobs_kind", table_name="backup_jobs")
    op.drop_table("backup_jobs")

    op.drop_index("ix_backup_configs_kind", table_name="backup_configs")
    op.drop_table("backup_configs")

