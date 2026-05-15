"""Create employee_job_records table

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_job_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),

        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),

        # ── Đơn vị tổ chức ───────────────────────────────────────────────
        sa.Column(
            "department_id",
            sa.Integer(),
            sa.ForeignKey("departments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "job_title_id",
            sa.Integer(),
            sa.ForeignKey("job_titles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "job_position_id",
            sa.Integer(),
            sa.ForeignKey("job_positions.id", ondelete="SET NULL"),
            nullable=True,
        ),

        # ── Mốc thời gian nhân sự ────────────────────────────────────────
        sa.Column("probation_start_date", sa.Date(), nullable=True),
        sa.Column("probation_end_date", sa.Date(), nullable=True),
        sa.Column("official_date", sa.Date(), nullable=True),

        # ── Hiệu lực bản ghi ─────────────────────────────────────────────
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="TRUE"),

        # ── Ghi chú & Audit ──────────────────────────────────────────────
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "changed_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Index tìm kiếm nhanh theo employee và department
    op.create_index("ix_job_records_employee_id", "employee_job_records", ["employee_id"])
    op.create_index("ix_job_records_department_id", "employee_job_records", ["department_id"])

    # Partial unique index: mỗi nhân viên tối đa 1 bản ghi is_current=TRUE.
    # Không thể tạo qua UniqueConstraint thông thường vì cần WHERE clause.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_job_record_current
        ON employee_job_records (employee_id)
        WHERE (is_current = TRUE)
        """
    )


def downgrade() -> None:
    op.drop_index("uq_job_record_current", table_name="employee_job_records")
    op.drop_index("ix_job_records_department_id", table_name="employee_job_records")
    op.drop_index("ix_job_records_employee_id", table_name="employee_job_records")
    op.drop_table("employee_job_records")
