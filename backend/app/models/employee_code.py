from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmployeeCodeSequence(SQLModel, table=True):
    __tablename__ = "employee_code_sequences"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=20, sa_column=Column(sa.String(20), nullable=False, unique=True, index=True))
    name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    next_value: int = Field(
        default=1,
        sa_column=Column(sa.Integer(), nullable=False, server_default="1"),
    )
    min_digits: int = Field(
        default=4,
        sa_column=Column(sa.SmallInteger(), nullable=False, server_default="4"),
    )
    is_default: bool = Field(
        default=False,
        sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        sa.Index(
            "uq_employee_code_sequences_default_active",
            sa.text("(1)"),
            unique=True,
            postgresql_where=sa.text("is_default = TRUE AND is_active = TRUE"),
        ),
    )


class EmployeeCodeSequenceRule(SQLModel, table=True):
    __tablename__ = "employee_code_sequence_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    scope_type: str = Field(max_length=20)
    department_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("departments.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    job_position_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("job_positions.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    employee_code_sequence_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employee_code_sequences.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    apply_to_descendants: bool = Field(
        default=False,
        sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    is_active: bool = Field(
        default=True,
        sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        sa.CheckConstraint(
            "scope_type IN ('department', 'job_position')",
            name="ck_employee_code_sequence_rules_scope_type",
        ),
        sa.CheckConstraint(
            "((scope_type = 'department' AND department_id IS NOT NULL AND job_position_id IS NULL) "
            "OR (scope_type = 'job_position' AND job_position_id IS NOT NULL AND department_id IS NULL))",
            name="ck_employee_code_sequence_rules_scope_target",
        ),
        sa.Index(
            "uq_employee_code_sequence_rules_department_active",
            "department_id",
            unique=True,
            postgresql_where=sa.text("scope_type = 'department' AND is_active = TRUE"),
        ),
        sa.Index(
            "uq_employee_code_sequence_rules_job_position_active",
            "job_position_id",
            unique=True,
            postgresql_where=sa.text("scope_type = 'job_position' AND is_active = TRUE"),
        ),
    )
