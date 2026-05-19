from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LeaveRecord(SQLModel, table=True):
    """Ghi nhận nghỉ phép của nhân viên."""

    __tablename__ = "leave_records"

    id:             Optional[int] = Field(default=None, primary_key=True)
    employee_id:    int           = Field(foreign_key="employees.id")
    leave_type_id:  int           = Field(foreign_key="leave_types.id")
    entitlement_id: Optional[int] = Field(default=None, foreign_key="leave_entitlements.id")

    start_date:  date = Field()
    end_date:    date = Field()
    start_half:  Optional[str] = Field(default=None, sa_column=Column(sa.String(2), nullable=True))
    end_half:    Optional[str] = Field(default=None, sa_column=Column(sa.String(2), nullable=True))

    total_days: Decimal = Field(
        sa_column=Column(sa.Numeric(5, 1), nullable=False),
    )

    reason:        Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    status:        str           = Field(default="active", sa_column=Column(sa.String(20), nullable=False, server_default="active"))
    cancel_reason: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    note:          Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    created_by_id: Optional[int]      = Field(default=None, foreign_key="users.id")
    created_at:    datetime           = Field(default_factory=_utcnow)
    updated_at:    Optional[datetime] = Field(default=None)
