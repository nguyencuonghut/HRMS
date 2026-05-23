from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.utcnow()


class BhxhSalaryAdjustment(SQLModel, table=True):
    """Quyết định điều chỉnh mức lương BHXH — immutable audit trail."""

    __tablename__ = "bhxh_salary_adjustments"

    id: Optional[int] = Field(default=None, primary_key=True)

    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    decision_number: Optional[str] = Field(default=None, max_length=100)
    old_basis_amount: Decimal = Field(
        sa_column=Column(sa.Numeric(18, 2), nullable=False)
    )
    new_basis_amount: Decimal = Field(
        sa_column=Column(sa.Numeric(18, 2), nullable=False)
    )
    effective_date: date = Field(
        sa_column=Column(sa.Date(), nullable=False, index=True)
    )
    reason: str = Field(sa_column=Column(sa.Text(), nullable=False))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(
            sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
    )
    insurance_change_event_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("insurance_change_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    __table_args__ = (
        sa.CheckConstraint(
            "old_basis_amount > 0 AND new_basis_amount > 0",
            name="ck_bsa_amounts_positive",
        ),
        sa.CheckConstraint(
            "old_basis_amount != new_basis_amount",
            name="ck_bsa_amounts_different",
        ),
        sa.Index("ix_bsa_created_at", "created_at"),
    )
