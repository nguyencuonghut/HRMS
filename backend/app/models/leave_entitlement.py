from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LeaveEntitlement(SQLModel, table=True):
    """Số ngày phép của nhân viên theo loại và năm."""

    __tablename__ = "leave_entitlements"

    id:            Optional[int] = Field(default=None, primary_key=True)
    employee_id:   int           = Field(foreign_key="employees.id")
    leave_type_id: int           = Field(foreign_key="leave_types.id")
    year:          int

    # Số ngày được cấp trong năm (tính thâm niên cho annual_leave)
    allocated_days: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(sa.Numeric(5, 1), nullable=False, server_default="0"),
    )
    # Số ngày chuyển từ năm trước (0 nếu loại phép không cho carryover)
    carryover_days: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(sa.Numeric(5, 1), nullable=False, server_default="0"),
    )
    # Ngày hết hạn carryover (null nếu carryover_allowed=False trên LeaveType)
    carryover_expires: Optional[date] = Field(default=None)

    # Số ngày đã dùng — cập nhật bởi module 5.3
    used_days: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(sa.Numeric(5, 1), nullable=False, server_default="0"),
    )

    note:          Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at:    datetime      = Field(default_factory=_utcnow)
    updated_at:    Optional[datetime] = Field(default=None)
