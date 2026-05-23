"""Create training_courses, training_plans, training_plan_courses tables."""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_courses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("course_type", sa.String(20), nullable=False),
        sa.Column("duration_hours", sa.SmallInteger, nullable=True),
        sa.Column("organizer", sa.String(200), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("cost_per_person", sa.Numeric(15, 2), nullable=True),
        sa.Column("is_mandatory", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_training_courses_code"),
        sa.CheckConstraint("course_type IN ('noi_bo','ben_ngoai','online')", name="ck_training_courses_type"),
    )

    op.create_table(
        "training_plans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("year", sa.SmallInteger, nullable=False),
        sa.Column("quarter", sa.SmallInteger, nullable=True),
        sa.Column("department_id", sa.Integer, sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("quarter IS NULL OR (quarter BETWEEN 1 AND 4)", name="ck_training_plans_quarter"),
        sa.CheckConstraint("status IN ('draft','approved','cancelled')", name="ck_training_plans_status"),
    )

    op.create_table(
        "training_plan_courses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("plan_id", sa.Integer, sa.ForeignKey("training_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.Integer, sa.ForeignKey("training_courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("target_count", sa.SmallInteger, nullable=True),
        sa.Column("scheduled_date", sa.Date, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("plan_id", "course_id", name="uq_training_plan_courses"),
    )

    # Indexes
    op.create_index("ix_training_courses_type",   "training_courses",      ["course_type"])
    op.create_index("ix_training_courses_active",  "training_courses",      ["is_active"])
    op.create_index("ix_training_plans_year",      "training_plans",        ["year"])
    op.create_index("ix_training_plans_dept",      "training_plans",        ["department_id"])
    op.create_index("ix_training_plans_status",    "training_plans",        ["status"])
    op.create_index("ix_training_plan_courses_plan",   "training_plan_courses", ["plan_id"])
    op.create_index("ix_training_plan_courses_course", "training_plan_courses", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_training_plan_courses_course", table_name="training_plan_courses")
    op.drop_index("ix_training_plan_courses_plan",   table_name="training_plan_courses")
    op.drop_index("ix_training_plans_status",  table_name="training_plans")
    op.drop_index("ix_training_plans_dept",    table_name="training_plans")
    op.drop_index("ix_training_plans_year",    table_name="training_plans")
    op.drop_index("ix_training_courses_active", table_name="training_courses")
    op.drop_index("ix_training_courses_type",   table_name="training_courses")
    op.drop_table("training_plan_courses")
    op.drop_table("training_plans")
    op.drop_table("training_courses")
