"""Models đào tạo (9.1 + 9.2 + 9.3)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TrainingCourse(SQLModel, table=True):
    """Danh mục khóa học đào tạo."""

    __tablename__ = "training_courses"

    id:               Optional[int]     = Field(default=None, primary_key=True)
    code:             str               = Field(sa_column=Column(sa.String(50), nullable=False, unique=True))
    name:             str               = Field(sa_column=Column(sa.String(500), nullable=False))
    course_type:      str               = Field(sa_column=Column(sa.String(20), nullable=False, index=True))
    duration_hours:   Optional[int]     = Field(default=None, sa_column=Column(sa.SmallInteger(), nullable=True))
    organizer:        Optional[str]     = Field(default=None, sa_column=Column(sa.String(200), nullable=True))
    description:      Optional[str]     = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    cost_per_person:  Optional[Decimal] = Field(default=None, sa_column=Column(sa.Numeric(15, 2), nullable=True))
    is_mandatory:     bool              = Field(sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("false")))
    is_active:        bool              = Field(sa_column=Column(sa.Boolean(), nullable=False, server_default=sa.text("true"), index=True))
    created_at:       datetime          = Field(default_factory=_utcnow)
    updated_at:       datetime          = Field(default_factory=_utcnow)


class TrainingPlan(SQLModel, table=True):
    """Kế hoạch đào tạo."""

    __tablename__ = "training_plans"

    id:             Optional[int]  = Field(default=None, primary_key=True)
    title:          str            = Field(sa_column=Column(sa.String(500), nullable=False))
    year:           int            = Field(sa_column=Column(sa.SmallInteger(), nullable=False, index=True))
    quarter:        Optional[int]  = Field(default=None, sa_column=Column(sa.SmallInteger(), nullable=True))
    department_id:  Optional[int]  = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("departments.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    description:    Optional[str]  = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    status:         str            = Field(sa_column=Column(sa.String(20), nullable=False, server_default=sa.text("'draft'"), index=True))
    created_by_id:  Optional[int]  = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at:     datetime       = Field(default_factory=_utcnow)
    updated_at:     datetime       = Field(default_factory=_utcnow)


class TrainingPlanCourse(SQLModel, table=True):
    """Khóa học trong kế hoạch đào tạo."""

    __tablename__ = "training_plan_courses"

    id:             Optional[int]  = Field(default=None, primary_key=True)
    plan_id:        int            = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("training_plans.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    course_id:      int            = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("training_courses.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    target_count:   Optional[int]  = Field(default=None, sa_column=Column(sa.SmallInteger(), nullable=True))
    scheduled_date: Optional[date] = Field(default=None)
    note:           Optional[str]  = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_at:     datetime       = Field(default_factory=_utcnow)


class EmployeeTrainingRecord(SQLModel, table=True):
    """Bản ghi đào tạo nhân viên."""

    __tablename__ = "employee_training_records"

    id:             Optional[int]     = Field(default=None, primary_key=True)
    employee_id:    int               = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    course_id:      int               = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("training_courses.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    plan_id:        Optional[int]     = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("training_plans.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        )
    )
    status:         str               = Field(
        sa_column=Column(sa.String(20), nullable=False, server_default=sa.text("'chua_bat_dau'"), index=True)
    )
    result:         Optional[str]     = Field(default=None, sa_column=Column(sa.String(20), nullable=True))
    score:          Optional[Decimal] = Field(default=None, sa_column=Column(sa.Numeric(5, 2), nullable=True))
    start_date:     Optional[date]    = Field(default=None)
    end_date:       Optional[date]    = Field(default=None)
    note:           Optional[str]     = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    source_review_id: Optional[int]  = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employee_yearly_reviews.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    created_by_id:  Optional[int]     = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )
    )
    created_at:     datetime          = Field(default_factory=_utcnow)
    updated_at:     datetime          = Field(default_factory=_utcnow)


class EmployeeTrainingCertificate(SQLModel, table=True):
    """Chứng chỉ đào tạo nhân viên (9.3)."""

    __tablename__ = "employee_training_certificates"

    id:                   Optional[int]     = Field(default=None, primary_key=True)
    employee_id:          int               = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    certificate_name:     str               = Field(sa_column=Column(sa.String(500), nullable=False))
    issuing_organization: Optional[str]     = Field(default=None, sa_column=Column(sa.String(300), nullable=True))
    issued_date:          date              = Field(sa_column=Column(sa.Date(), nullable=False))
    expiry_date:          Optional[date]    = Field(default=None, sa_column=Column(sa.Date(), nullable=True, index=True))
    related_course_id:    Optional[int]     = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("training_courses.id", ondelete="SET NULL"), nullable=True)
    )
    note:                 Optional[str]     = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    file_path:            Optional[str]     = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    file_name:            Optional[str]     = Field(default=None, sa_column=Column(sa.String(300), nullable=True))
    file_size:            Optional[int]     = Field(default=None, sa_column=Column(sa.Integer(), nullable=True))
    mime_type:            Optional[str]     = Field(default=None, sa_column=Column(sa.String(100), nullable=True))
    created_by_id:        Optional[int]     = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    )
    created_at:           datetime          = Field(default_factory=_utcnow)
    updated_at:           datetime          = Field(default_factory=_utcnow)
