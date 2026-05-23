"""Models khen thưởng nhân viên (8.1)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RewardType(SQLModel, table=True):
    """Danh mục loại khen thưởng — do HR quản lý."""

    __tablename__ = "reward_types"

    id:          Optional[int] = Field(default=None, primary_key=True)
    code:        str           = Field(sa_column=Column(sa.String(50), nullable=False, unique=True))
    name:        str           = Field(sa_column=Column(sa.String(200), nullable=False))
    is_monetary: bool          = Field(default=False)
    sort_order:  int           = Field(default=0)
    is_active:   bool          = Field(default=True)
    created_at:  datetime      = Field(default_factory=_utcnow)


class EmployeeReward(SQLModel, table=True):
    """Quyết định khen thưởng của nhân viên."""

    __tablename__ = "employee_rewards"

    id:             Optional[int] = Field(default=None, primary_key=True)
    employee_id:    int           = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    reward_type_id: int           = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("reward_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    )

    title:           str            = Field(sa_column=Column(sa.String(500), nullable=False))
    description:     Optional[str]  = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    reward_date:     date           = Field()
    decision_number: Optional[str]  = Field(default=None, sa_column=Column(sa.String(100), nullable=True))
    issued_by:       Optional[str]  = Field(default=None, sa_column=Column(sa.String(200), nullable=True))
    value:           Optional[Decimal] = Field(
        default=None, sa_column=Column(sa.Numeric(18, 2), nullable=True)
    )
    note:            Optional[str]  = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    # File đính kèm (MinIO)
    file_path:  Optional[str] = Field(default=None, sa_column=Column(sa.String(500), nullable=True))
    file_name:  Optional[str] = Field(default=None, sa_column=Column(sa.String(255), nullable=True))
    file_size:  Optional[int] = Field(default=None)
    mime_type:  Optional[str] = Field(default=None, sa_column=Column(sa.String(100), nullable=True))

    created_by_id: Optional[int]      = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    )
    created_at:    datetime           = Field(default_factory=_utcnow)
    updated_at:    Optional[datetime] = Field(default=None)
