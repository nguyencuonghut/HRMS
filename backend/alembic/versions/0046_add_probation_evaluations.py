"""add probation evaluations

Revision ID: 0046
Revises: 0045
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "probation_evaluations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_record_id", sa.Integer, sa.ForeignKey("employee_job_records.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evaluation_date", sa.Date, nullable=False),
        sa.Column("evaluator_id", sa.Integer, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("hr_reviewer_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("attitude_score", sa.Numeric(4, 1), nullable=True),
        sa.Column("competence_score", sa.Numeric(4, 1), nullable=True),
        sa.Column("culture_score", sa.Numeric(4, 1), nullable=True),
        sa.Column("kpi_score", sa.Numeric(4, 1), nullable=True),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("manager_comment", sa.Text, nullable=True),
        sa.Column("hr_comment", sa.Text, nullable=True),
        sa.Column("result", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("extension_days", sa.SmallInteger, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("approved_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("employee_id", "job_record_id", name="uq_probation_eval_employee_job"),
        sa.CheckConstraint("attitude_score IS NULL OR (attitude_score >= 0 AND attitude_score <= 10)", name="ck_attitude_score"),
        sa.CheckConstraint("competence_score IS NULL OR (competence_score >= 0 AND competence_score <= 10)", name="ck_competence_score"),
        sa.CheckConstraint("culture_score IS NULL OR (culture_score >= 0 AND culture_score <= 10)", name="ck_culture_score"),
        sa.CheckConstraint("kpi_score IS NULL OR (kpi_score >= 0 AND kpi_score <= 10)", name="ck_kpi_score"),
        sa.CheckConstraint("extension_days IS NULL OR extension_days > 0", name="ck_extension_days"),
        sa.CheckConstraint("result IN ('pending', 'passed', 'failed', 'extended')", name="ck_result"),
        sa.CheckConstraint("status IN ('draft', 'submitted', 'approved')", name="ck_status"),
    )
    op.create_index("ix_probation_eval_employee", "probation_evaluations", ["employee_id"])
    op.create_index("ix_probation_eval_status", "probation_evaluations", ["status"])
    op.create_index("ix_probation_eval_result", "probation_evaluations", ["result"])


def downgrade() -> None:
    op.drop_table("probation_evaluations")
