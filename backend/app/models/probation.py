"""Model đánh giá thử việc nhân viên (Plan 14.2)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProbationEvaluation(SQLModel, table=True):
    """Phiếu đánh giá kết quả thử việc nhân viên."""

    __tablename__ = "probation_evaluations"

    id: Optional[int] = Field(default=None, primary_key=True)

    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    job_record_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employee_job_records.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )

    evaluation_date: date

    evaluator_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )

    hr_reviewer_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    attitude_score: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(sa.Numeric(4, 1), nullable=True),
    )
    competence_score: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(sa.Numeric(4, 1), nullable=True),
    )
    culture_score: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(sa.Numeric(4, 1), nullable=True),
    )
    kpi_score: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(sa.Numeric(4, 1), nullable=True),
    )
    overall_score: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(sa.Numeric(5, 2), nullable=True),
    )

    manager_comment: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    hr_comment: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )

    # pending | passed | failed | extended
    result: str = Field(
        default="pending",
        sa_column=Column(sa.String(20), nullable=False, server_default="pending"),
    )

    extension_days: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.SmallInteger(), nullable=True),
    )

    # draft | submitted | approved
    status: str = Field(
        default="draft",
        sa_column=Column(sa.String(20), nullable=False, server_default="draft"),
    )

    approved_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    approved_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint("employee_id", "job_record_id", name="uq_probation_eval_employee_job"),
        sa.CheckConstraint(
            "attitude_score IS NULL OR (attitude_score >= 0 AND attitude_score <= 10)",
            name="ck_attitude_score",
        ),
        sa.CheckConstraint(
            "competence_score IS NULL OR (competence_score >= 0 AND competence_score <= 10)",
            name="ck_competence_score",
        ),
        sa.CheckConstraint(
            "culture_score IS NULL OR (culture_score >= 0 AND culture_score <= 10)",
            name="ck_culture_score",
        ),
        sa.CheckConstraint(
            "kpi_score IS NULL OR (kpi_score >= 0 AND kpi_score <= 10)",
            name="ck_kpi_score",
        ),
        sa.CheckConstraint("extension_days IS NULL OR extension_days > 0", name="ck_extension_days"),
        sa.CheckConstraint(
            "result IN ('pending', 'passed', 'failed', 'extended')",
            name="ck_result",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'approved')",
            name="ck_status",
        ),
    )
