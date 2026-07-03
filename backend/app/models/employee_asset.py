from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmployeeAsset(SQLModel, table=True):
    """Tài sản cấp phát cho nhân viên."""

    __tablename__ = "employee_assets"

    id: Optional[int] = Field(default=None, primary_key=True)

    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    asset_name: str = Field(max_length=200)
    asset_type: str = Field(max_length=50)  # pc | laptop | projector | phone_sim | other
    handover_date: date = Field(nullable=False)
    return_date: Optional[date] = Field(default=None)
    status: str = Field(max_length=20, default="allocated")  # allocated | returned | lost | damaged
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)
