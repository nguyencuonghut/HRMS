"""Create employee_training_records table."""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_training_records",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "employee_id",
            sa.Integer,
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.Integer,
            sa.ForeignKey("training_courses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.Integer,
            sa.ForeignKey("training_plans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="chua_bat_dau"),
        sa.Column("result", sa.String(20), nullable=True),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('chua_bat_dau','dang_hoc','hoan_thanh','khong_hoan_thanh','vang_mat')",
            name="ck_emp_training_records_status",
        ),
        sa.CheckConstraint(
            "result IN ('dat','khong_dat') OR result IS NULL",
            name="ck_emp_training_records_result",
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100 OR score IS NULL",
            name="ck_emp_training_records_score",
        ),
        sa.CheckConstraint(
            "end_date >= start_date OR start_date IS NULL OR end_date IS NULL",
            name="ck_emp_training_records_dates",
        ),
    )

    op.create_index("ix_emp_training_records_employee", "employee_training_records", ["employee_id"])
    op.create_index("ix_emp_training_records_course",   "employee_training_records", ["course_id"])
    op.create_index("ix_emp_training_records_plan",     "employee_training_records", ["plan_id"])
    op.create_index("ix_emp_training_records_status",   "employee_training_records", ["status"])
    op.create_index("ix_emp_training_records_end_date", "employee_training_records", ["end_date"])
    op.create_index(
        "ix_emp_training_records_emp_course",
        "employee_training_records",
        ["employee_id", "course_id"],
    )
    op.execute(
        "CREATE INDEX ix_emp_training_records_completed "
        "ON employee_training_records (employee_id, end_date) "
        "WHERE status = 'hoan_thanh'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_emp_training_records_completed")
    op.drop_index("ix_emp_training_records_emp_course", table_name="employee_training_records")
    op.drop_index("ix_emp_training_records_end_date",   table_name="employee_training_records")
    op.drop_index("ix_emp_training_records_status",     table_name="employee_training_records")
    op.drop_index("ix_emp_training_records_plan",       table_name="employee_training_records")
    op.drop_index("ix_emp_training_records_course",     table_name="employee_training_records")
    op.drop_index("ix_emp_training_records_employee",   table_name="employee_training_records")
    op.drop_table("employee_training_records")
