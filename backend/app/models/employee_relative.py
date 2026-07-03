from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmployeeRelative(SQLModel, table=True):
    """Người thân của nhân viên — bao gồm người liên hệ khẩn cấp."""

    __tablename__ = "employee_relatives"

    id: Optional[int] = Field(default=None, primary_key=True)

    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # ── Thông tin cơ bản ─────────────────────────────────────────────
    full_name: str = Field(max_length=200)
    # Giá trị hợp lệ: vo | chong | cha | me | con | anh | chi | em | khac
    relationship_type: str = Field(max_length=20)
    date_of_birth: Optional[date] = Field(default=None)
    occupation: Optional[str] = Field(default=None, max_length=200)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    participates_in_health_care_insurance: bool = Field(default=False)

    # ── Liên hệ khẩn cấp ─────────────────────────────────────────────
    is_emergency_contact: bool = Field(default=False)

    # ── Ghi chú & Audit ──────────────────────────────────────────────
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)
