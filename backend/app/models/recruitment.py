"""Models tuyển dụng ATS (13.1 — Kế hoạch & Yêu cầu tuyển dụng)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class HeadcountPlan(SQLModel, table=True):
    """Kế hoạch nhân sự theo năm / phòng ban / vị trí (tùy chọn)."""

    __tablename__ = "headcount_plans"

    id: Optional[int] = Field(default=None, primary_key=True)
    year: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    department_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
    )
    job_position_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("job_positions.id", ondelete="SET NULL"), nullable=True),
    )
    current_count: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False, server_default="0"))
    planned_count: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    reason: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint("year", "department_id", "job_position_id", name="uq_headcount_plan_year_dept_pos"),
        sa.Index("ix_headcount_plans_year", "year"),
        sa.Index("ix_headcount_plans_department_id", "department_id"),
    )


class JobRequisition(SQLModel, table=True):
    """Yêu cầu tuyển dụng (JR) — nền tảng của toàn bộ ATS."""

    __tablename__ = "job_requisitions"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(sa_column=Column(sa.String(30), nullable=False, unique=True))
    job_position_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("job_positions.id", ondelete="RESTRICT"), nullable=False)
    )
    department_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    )
    headcount_plan_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("headcount_plans.id", ondelete="SET NULL"), nullable=True),
    )

    quantity: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False, server_default="1"))
    # Số lượng còn cần tuyển (giảm dần khi hiring_decision.convert_to_employee chạy)
    quantity_remaining: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False, server_default="1"))
    reason_type: str = Field(sa_column=Column(sa.String(20), nullable=False))
    # new | replacement | expansion

    deadline: Optional[datetime] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    salary_min: Optional[Decimal] = Field(
        default=None, sa_column=Column(sa.Numeric(15, 2), nullable=True)
    )
    salary_max: Optional[Decimal] = Field(
        default=None, sa_column=Column(sa.Numeric(15, 2), nullable=True)
    )

    # JD override — None = kế thừa từ job_position.description/requirements
    jd_description: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    jd_requirements: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    status: str = Field(sa_column=Column(sa.String(20), nullable=False, server_default="draft"))
    # draft | pending_review | approved | in_progress | completed | cancelled

    submitted_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    submitted_at: Optional[datetime] = Field(default=None, sa_column=Column(sa.DateTime(), nullable=True))

    approved_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    approved_at: Optional[datetime] = Field(default=None, sa_column=Column(sa.DateTime(), nullable=True))

    rejection_note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    internal_note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    created_by_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.Index("ix_jr_department_id", "department_id"),
        sa.Index("ix_jr_job_position_id", "job_position_id"),
        sa.Index("ix_jr_status", "status"),
        sa.Index("ix_jr_code", "code"),
    )


class RecruitmentBudgetItem(SQLModel, table=True):
    """Khoản chi phí tuyển dụng dự toán/thực tế cho một JR."""

    __tablename__ = "recruitment_budget_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_requisition_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("job_requisitions.id", ondelete="CASCADE"), nullable=False)
    )
    item_name: str = Field(sa_column=Column(sa.String(200), nullable=False))
    estimated_amount: Optional[Decimal] = Field(
        default=None, sa_column=Column(sa.Numeric(15, 2), nullable=True)
    )
    actual_amount: Optional[Decimal] = Field(
        default=None, sa_column=Column(sa.Numeric(15, 2), nullable=True)
    )
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.Index("ix_budget_items_jr_id", "job_requisition_id"),
    )
