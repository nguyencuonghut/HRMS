from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class InsuranceContributionComponent(SQLModel, table=True):
    __tablename__ = "insurance_contribution_components"

    code: str = Field(primary_key=True, max_length=50)
    name_vi: str = Field(max_length=255)
    insurance_kind: str = Field(max_length=30)
    sort_order: int = Field(
        sa_column=Column(sa.Integer(), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


class InsurancePolicyVersion(SQLModel, table=True):
    __tablename__ = "insurance_policy_versions"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=50,
        sa_column=Column(sa.String(50), nullable=False, unique=True, index=True),
    )
    name: str = Field(max_length=255)
    legal_basis_summary: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    effective_from: date = Field(sa_column=Column(sa.Date(), nullable=False))
    effective_to: Optional[date] = Field(
        default=None,
        sa_column=Column(sa.Date(), nullable=True),
    )
    is_active: bool = Field(
        default=False,
        sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    company_region: int = Field(
        sa_column=Column(sa.SmallInteger(), nullable=False),
    )
    note: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        sa.Index(
            "uq_insurance_policy_versions_active",
            sa.text("(1)"),
            unique=True,
            postgresql_where=sa.text("is_active = TRUE"),
        ),
    )


class InsurancePolicyComponentRate(SQLModel, table=True):
    __tablename__ = "insurance_policy_component_rates"

    id: Optional[int] = Field(default=None, primary_key=True)
    policy_version_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("insurance_policy_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    component_code: str = Field(
        sa_column=Column(
            sa.String(50),
            sa.ForeignKey("insurance_contribution_components.code", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    employee_rate_percent: float = Field(
        default=0,
        sa_column=Column(sa.Numeric(8, 4), nullable=False, server_default="0"),
    )
    employer_rate_percent: float = Field(
        default=0,
        sa_column=Column(sa.Numeric(8, 4), nullable=False, server_default="0"),
    )
    employer_advances_employee_part: bool = Field(
        default=False,
        sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "policy_version_id",
            "component_code",
            name="uq_insurance_policy_component_rates_policy_component",
        ),
    )


class InsuranceChangeEvent(SQLModel, table=True):
    """Sổ cái biến động tăng/giảm BHXH — self-contained snapshot.

    Mọi thông tin nhân viên, hợp đồng, tỷ lệ đóng tại thời điểm biến động
    được snapshot vào đây để export D02-TS / iBHXH XML bất kỳ lúc nào mà
    không cần JOIN vào các bảng live (có thể đã thay đổi).
    """

    __tablename__ = "insurance_change_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )

    # ── Thông tin biến động ────────────────────────────────────────────────
    change_type: str = Field(max_length=10)       # 'increase' | 'decrease'
    change_reason: str = Field(max_length=50)     # xem bảng mã lý do trong plan 6.3
    ibhxh_reason_code: str = Field(max_length=5)  # 'T-01'..'T-05' | 'G-01'..'G-07'
    effective_date: date = Field(sa_column=Column(sa.Date(), nullable=False, index=True))
    period_year: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    period_month: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))

    # ── Snapshot nhân viên tại thời điểm biến động ────────────────────────
    employee_name_snapshot: str = Field(max_length=255)
    date_of_birth_snapshot: date = Field(sa_column=Column(sa.Date(), nullable=False))
    gender_snapshot: str = Field(max_length=10)
    nationality_code_snapshot: str = Field(
        max_length=10,
        sa_column=Column(sa.String(10), nullable=False, server_default="VN"),
    )
    identity_number_snapshot: Optional[str] = Field(default=None, max_length=25)

    # ── Snapshot hợp đồng tại thời điểm biến động ────────────────────────
    contract_number_snapshot: Optional[str] = Field(default=None, max_length=100)
    contract_type_code_snapshot: Optional[str] = Field(default=None, max_length=5)
    contract_signed_date_snapshot: Optional[date] = Field(
        default=None, sa_column=Column(sa.Date(), nullable=True)
    )
    contract_from_snapshot: Optional[date] = Field(
        default=None, sa_column=Column(sa.Date(), nullable=True)
    )
    contract_to_snapshot: Optional[date] = Field(
        default=None, sa_column=Column(sa.Date(), nullable=True)
    )

    # ── Snapshot bảo hiểm tại thời điểm biến động ────────────────────────
    bhxh_code_snapshot: Optional[str] = Field(default=None, max_length=20)
    basis_amount: Decimal = Field(sa_column=Column(sa.Numeric(18, 2), nullable=False))
    allowances_amount: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(sa.Numeric(18, 2), nullable=False, server_default="0"),
    )
    bhyt_clinic_name_snapshot: Optional[str] = Field(default=None, max_length=255)
    bhyt_clinic_code_snapshot: Optional[str] = Field(default=None, max_length=20)
    policy_version_code_snapshot: Optional[str] = Field(default=None, max_length=50)
    employee_rate_total_snapshot: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(sa.Numeric(8, 4), nullable=False, server_default="0"),
    )
    employer_rate_total_snapshot: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(sa.Numeric(8, 4), nullable=False, server_default="0"),
    )

    # ── Snapshot bổ sung (Slice 4a — VNPT compat) ────────────────────────
    ethnicity_bhxh_code_snapshot: Optional[str] = Field(default=None, max_length=10)

    # ── Trạng thái cũ / mới ───────────────────────────────────────────────
    old_status: Optional[str] = Field(default=None, max_length=20)
    new_status: str = Field(max_length=20)

    # ── Tháng kê khai gợi ý (6.4 dùng làm default cho declared_month) ────
    suggested_declaration_year: int = Field(
        sa_column=Column(sa.SmallInteger(), nullable=False)
    )
    suggested_declaration_month: int = Field(
        sa_column=Column(sa.SmallInteger(), nullable=False)
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    is_manual: bool = Field(
        default=False,
        sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.CheckConstraint(
            "change_type IN ('increase', 'decrease')",
            name="ck_ice_change_type",
        ),
        sa.CheckConstraint(
            "change_reason IN ("
            "'new_hire', 'return_from_leave', 'transfer_in', 'contract_renewal', "
            "'resignation', 'contract_end', 'dismissal', "
            "'unpaid_leave', 'maternity_no_contribution', 'long_term_sick', 'transfer_out', "
            "'manual_correction'"
            ")",
            name="ck_ice_change_reason",
        ),
        sa.CheckConstraint("period_month BETWEEN 1 AND 12", name="ck_ice_period_month"),
        sa.CheckConstraint(
            "suggested_declaration_month BETWEEN 1 AND 12",
            name="ck_ice_suggested_month",
        ),
        sa.CheckConstraint("basis_amount > 0", name="ck_ice_basis_positive"),
        sa.CheckConstraint("allowances_amount >= 0", name="ck_ice_allowances_non_negative"),
        sa.Index("ix_ice_period", "period_year", "period_month"),
        sa.Index(
            "ix_ice_suggested_declaration",
            "suggested_declaration_year",
            "suggested_declaration_month",
        ),
        sa.Index("ix_ice_change_type", "change_type"),
        sa.Index("ix_ice_ibhxh_code", "ibhxh_reason_code"),
    )
