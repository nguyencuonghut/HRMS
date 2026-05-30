"""add soft delete to org tables

Revision ID: 0051
Revises: 0050
Create Date: 2026-05-30

Thêm cột `deleted_at` (nullable DateTime) vào 3 bảng cốt lõi tổ chức:
  - departments
  - job_titles
  - job_positions

Không xóa dữ liệu cũ. Mọi record hiện tại sẽ có deleted_at = NULL (active).
Index trên deleted_at để WHERE deleted_at IS NULL chạy nhanh.
"""

from alembic import op
import sqlalchemy as sa

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("departments", "job_titles", "job_positions"):
        op.add_column(
            table,
            sa.Column(
                "deleted_at",
                sa.DateTime(timezone=False),
                nullable=True,
                comment="NULL = active; NOT NULL = soft-deleted at this timestamp",
            ),
        )
        op.create_index(
            f"ix_{table}_deleted_at",
            table,
            ["deleted_at"],
        )


def downgrade() -> None:
    for table in ("departments", "job_titles", "job_positions"):
        op.drop_index(f"ix_{table}_deleted_at", table_name=table)
        op.drop_column(table, "deleted_at")
