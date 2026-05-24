"""Models hiệu suất KPI (10.1 + 10.2)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmployeeKpiMonthly(SQLModel, table=True):
    """Điểm KPI tháng của nhân viên (10.1)."""

    __tablename__ = "employee_kpi_monthly"

    id:             Optional[int]     = Field(default=None, primary_key=True)
    employee_id:    int               = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    year:           int               = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    month:          int               = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    score:          Decimal           = Field(sa_column=Column(sa.Numeric(5, 2), nullable=False))
    note:           Optional[str]     = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id:  Optional[int]     = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    )
    created_at:     datetime          = Field(default_factory=_utcnow)
    updated_at:     datetime          = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint("employee_id", "year", "month", name="uq_employee_kpi_year_month"),
        sa.Index("ix_employee_kpi_monthly_year_month", "year", "month"),
    )


class EmployeeYearlyReview(SQLModel, table=True):
    """Đánh giá cuối năm của nhân viên (10.2). avg_score tính on-the-fly từ KPI tháng."""

    __tablename__ = "employee_yearly_reviews"

    id:             Optional[int]     = Field(default=None, primary_key=True)
    employee_id:    int               = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    year:           int               = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    rating:         str               = Field(sa_column=Column(sa.String(20), nullable=False))
    review_note:    Optional[str]     = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id:  Optional[int]     = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    )
    created_at:     datetime          = Field(default_factory=_utcnow)
    updated_at:     datetime          = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint("employee_id", "year", name="uq_employee_yearly_review_year"),
        sa.Index("ix_employee_yearly_reviews_year", "year"),
    )
