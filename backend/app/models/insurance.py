from __future__ import annotations

from datetime import date, datetime, timezone
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
