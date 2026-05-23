"""Model kỷ luật nhân viên (8.2)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmployeeDiscipline(SQLModel, table=True):
    """Quyết định kỷ luật của nhân viên."""

    __tablename__ = "employee_disciplines"

    id:          Optional[int] = Field(default=None, primary_key=True)
    employee_id: int           = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    discipline_form: str  = Field(sa_column=Column(sa.String(50), nullable=False))
    violation_date:  date = Field()
    effective_date:  date = Field()
    end_date:        Optional[date]  = Field(default=None)
    extended_months: Optional[int]   = Field(default=None, sa_column=Column(sa.SmallInteger(), nullable=True))

    title:           str           = Field(sa_column=Column(sa.String(500), nullable=False))
    description:     Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    decision_number: Optional[str] = Field(default=None, sa_column=Column(sa.String(100), nullable=True))
    issued_by:       Optional[str] = Field(default=None, sa_column=Column(sa.String(200), nullable=True))
    note:            Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    file_path:  Optional[str] = Field(default=None, sa_column=Column(sa.String(500), nullable=True))
    file_name:  Optional[str] = Field(default=None, sa_column=Column(sa.String(255), nullable=True))
    file_size:  Optional[int] = Field(default=None)
    mime_type:  Optional[str] = Field(default=None, sa_column=Column(sa.String(100), nullable=True))

    created_by_id: Optional[int]      = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    created_at:    datetime           = Field(default_factory=_utcnow)
    updated_at:    Optional[datetime] = Field(default=None)
