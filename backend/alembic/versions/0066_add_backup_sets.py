"""add backup sets

Revision ID: 0066
Revises: 0065
Create Date: 2026-07-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0066"
down_revision: Union[str, None] = "0065"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backup_sets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trigger", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("db_job_id", sa.Integer(), nullable=True),
        sa.Column("object_job_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_backup_sets_status", "backup_sets", ["status"])
    op.create_index("ix_backup_sets_created_at", "backup_sets", ["created_at"])

    op.create_foreign_key(
        "fk_backup_sets_db_job_id_backup_jobs",
        "backup_sets",
        "backup_jobs",
        ["db_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_backup_sets_object_job_id_backup_jobs",
        "backup_sets",
        "backup_jobs",
        ["object_job_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("backup_jobs", sa.Column("backup_set_id", sa.Integer(), nullable=True))
    op.create_index("ix_backup_jobs_backup_set_id", "backup_jobs", ["backup_set_id"])
    op.create_foreign_key(
        "fk_backup_jobs_backup_set_id_backup_sets",
        "backup_jobs",
        "backup_sets",
        ["backup_set_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("restore_requests", sa.Column("backup_set_id", sa.Integer(), nullable=True))
    op.create_index("ix_restore_requests_backup_set_id", "restore_requests", ["backup_set_id"])
    op.create_foreign_key(
        "fk_restore_requests_backup_set_id_backup_sets",
        "restore_requests",
        "backup_sets",
        ["backup_set_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_restore_requests_backup_set_id_backup_sets", "restore_requests", type_="foreignkey")
    op.drop_index("ix_restore_requests_backup_set_id", table_name="restore_requests")
    op.drop_column("restore_requests", "backup_set_id")

    op.drop_constraint("fk_backup_jobs_backup_set_id_backup_sets", "backup_jobs", type_="foreignkey")
    op.drop_index("ix_backup_jobs_backup_set_id", table_name="backup_jobs")
    op.drop_column("backup_jobs", "backup_set_id")

    op.drop_constraint("fk_backup_sets_object_job_id_backup_jobs", "backup_sets", type_="foreignkey")
    op.drop_constraint("fk_backup_sets_db_job_id_backup_jobs", "backup_sets", type_="foreignkey")
    op.drop_index("ix_backup_sets_created_at", table_name="backup_sets")
    op.drop_index("ix_backup_sets_status", table_name="backup_sets")
    op.drop_table("backup_sets")
