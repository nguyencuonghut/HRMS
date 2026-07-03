from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmployeeInsuranceProfile(SQLModel, table=True):
    __tablename__ = "employee_insurance_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        )
    )
    bhxh_code: Optional[str] = Field(default=None, max_length=20)
    health_care_insurance_code: Optional[str] = Field(default=None, max_length=50)
    health_care_family_participation: Optional[bool] = Field(default=None)
    accident_insurance_code: Optional[str] = Field(default=None, max_length=50)
    bhyt_initial_clinic_name: Optional[str] = Field(default=None, max_length=255)
    bhyt_initial_clinic_code: Optional[str] = Field(default=None, max_length=20)
    company_bhxh_joined_date: Optional[date] = Field(default=None)
    participation_status: str = Field(
        default="active",
        sa_column=Column(sa.String(20), nullable=False, server_default="active"),
    )
    status_effective_from: Optional[date] = Field(default=None)
    status_note: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    insurance_basis_source: str = Field(
        default="contract",
        sa_column=Column(sa.String(20), nullable=False, server_default="contract"),
    )
    insurance_basis_amount: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(sa.Numeric(18, 2), nullable=True),
    )
    insurance_policy_version_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("insurance_policy_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        sa.CheckConstraint(
            "participation_status IN ('active', 'paused', 'stopped')",
            name="ck_employee_insurance_profiles_participation_status",
        ),
        sa.CheckConstraint(
            "insurance_basis_source IN ('contract', 'computed', 'manual_fixed')",
            name="ck_employee_insurance_profiles_basis_source",
        ),
    )


class EmployeeInsuranceComponentOverride(SQLModel, table=True):
    __tablename__ = "employee_insurance_component_overrides"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_insurance_profile_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employee_insurance_profiles.id", ondelete="CASCADE"),
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
    use_company_default: bool = Field(
        default=True,
        sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    fixed_employee_amount: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(sa.Numeric(18, 2), nullable=True),
    )
    fixed_employer_amount: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(sa.Numeric(18, 2), nullable=True),
    )
    employer_advances_employee_part: Optional[bool] = Field(
        default=None,
        sa_column=Column(sa.Boolean(), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        sa.UniqueConstraint(
            "employee_insurance_profile_id",
            "component_code",
            name="uq_employee_insurance_component_override_profile_component",
        ),
        sa.CheckConstraint(
            "fixed_employee_amount IS NULL OR fixed_employee_amount >= 0",
            name="ck_employee_insurance_component_overrides_employee_non_negative",
        ),
        sa.CheckConstraint(
            "fixed_employer_amount IS NULL OR fixed_employer_amount >= 0",
            name="ck_employee_insurance_component_overrides_employer_non_negative",
        ),
        sa.CheckConstraint(
            "NOT use_company_default OR (fixed_employee_amount IS NULL AND fixed_employer_amount IS NULL)",
            name="ck_employee_insurance_component_overrides_default_vs_fixed",
        ),
    )
