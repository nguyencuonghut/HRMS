"""replace unique code constraints with partial unique indexes for soft delete

Revision ID: 0052
Revises: 0051
Create Date: 2026-05-30

Thay thế UNIQUE constraint trên cột `code` của 3 bảng bằng
partial unique index: UNIQUE WHERE deleted_at IS NULL.

Điều này cho phép:
  - Code cũ (đã soft-delete) không chặn việc tạo mới với cùng code
  - Code mới (active) vẫn bị enforce unique
"""

from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None

_TABLES = ["departments", "job_titles", "job_positions"]


def upgrade() -> None:
    for table in _TABLES:
        # Drop constraint unique + index cũ (không có điều kiện)
        op.drop_constraint(f"uq_{table}_code", table, type_="unique")
        op.drop_index(f"ix_{table}_code", table_name=table)

        # Tạo partial unique index: unique chỉ trong số records CHƯA bị xóa mềm
        op.execute(
            f"CREATE UNIQUE INDEX uq_{table}_code_active "
            f"ON {table} (code) WHERE deleted_at IS NULL"
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_index(f"uq_{table}_code_active", table_name=table)

        # Restore unique constraint (có thể fail nếu có duplicate codes trong soft-deleted rows)
        op.create_index(f"ix_{table}_code", table, ["code"], unique=True)
        op.create_unique_constraint(f"uq_{table}_code", table, ["code"])
