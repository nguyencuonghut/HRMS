"""Model hợp đồng lao động + phụ lục của nhân viên (4.1)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmployeeContract(SQLModel, table=True):
    """Hợp đồng lao động hoặc phụ lục hợp đồng của nhân viên.

    Phụ lục được lưu trong cùng bảng với parent_contract_id trỏ về HĐ gốc.
    document_kind được sao chép từ contract_category để tránh JOIN khi filter.
    """

    __tablename__ = "employee_contracts"

    id: Optional[int] = Field(default=None, primary_key=True)

    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # Phụ lục trỏ về HĐ gốc; NULL = đây là HĐ gốc
    parent_contract_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employee_contracts.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    contract_category_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("contract_categories.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )

    # Sao chép từ contract_categories.document_kind để tránh JOIN khi filter
    document_kind: str = Field(
        sa_column=Column(sa.String(30), nullable=False, index=True)
    )

    # ── Thông tin hợp đồng ────────────────────────────────────────────────
    contract_number: str = Field(
        sa_column=Column(sa.String(100), nullable=False)
    )
    signed_date:    date
    effective_from: date
    effective_to:   Optional[date] = Field(default=None)   # NULL = vô thời hạn

    insurance_salary: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(sa.Numeric(18, 2), nullable=True),
    )

    # active | expired | terminated | draft
    status: str = Field(
        default="active",
        sa_column=Column(sa.String(20), nullable=False, index=True),
    )

    # ── File scan/PDF ─────────────────────────────────────────────────────
    file_path:  Optional[str] = Field(default=None, max_length=500)
    file_name:  Optional[str] = Field(default=None, max_length=255)
    file_size:  Optional[int] = Field(default=None)
    mime_type:  Optional[str] = Field(default=None, max_length=100)

    notes: Optional[str] = Field(
        default=None, sa_column=Column(sa.Text(), nullable=True)
    )

    created_by: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        sa.UniqueConstraint("contract_number", name="uq_employee_contract_number"),
        sa.Index("ix_employee_contracts_effective_to_status", "effective_to", "status"),
    )
