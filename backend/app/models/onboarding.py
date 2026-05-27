"""Models onboarding — tiếp nhận nhân viên mới (Plan 14.1)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OnboardingTask(SQLModel, table=True):
    """Template task onboarding — HR cấu hình."""

    __tablename__ = "onboarding_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(sa_column=Column(sa.String(50), nullable=False, unique=True))
    name: str = Field(sa_column=Column(sa.String(200), nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    # admin | it | training | specialty
    group: str = Field(
        sa_column=Column(sa.String(30), nullable=False, server_default="admin")
    )
    default_assignee_role: Optional[str] = Field(
        default=None, sa_column=Column(sa.String(100), nullable=True)
    )
    # số ngày kể từ start_date (0 = ngay ngày đầu)
    due_offset_days: int = Field(
        sa_column=Column(sa.SmallInteger(), nullable=False, server_default="3")
    )
    sort_order: int = Field(
        sa_column=Column(sa.SmallInteger(), nullable=False, server_default="0")
    )
    is_active: bool = Field(
        sa_column=Column(sa.Boolean(), nullable=False, server_default="true")
    )
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.Index("ix_onboarding_tasks_group", "group"),
        sa.Index("ix_onboarding_tasks_active", "is_active"),
    )


class OnboardingChecklist(SQLModel, table=True):
    """Instance checklist onboarding — mỗi nhân viên có 1 bản."""

    __tablename__ = "onboarding_checklists"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    hiring_decision_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("hiring_decisions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    buddy_user_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )
    # in_progress | completed | cancelled
    status: str = Field(
        sa_column=Column(sa.String(20), nullable=False, server_default="in_progress")
    )
    completion_pct: float = Field(
        sa_column=Column(
            sa.Numeric(5, 2), nullable=False, server_default="0.00"
        )
    )
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint("employee_id", name="uq_onboarding_checklists_employee"),
        sa.Index("ix_onboarding_checklists_status", "status"),
        sa.Index("ix_onboarding_checklists_employee", "employee_id"),
    )


class OnboardingChecklistItem(SQLModel, table=True):
    """Task instance trong một checklist."""

    __tablename__ = "onboarding_checklist_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    checklist_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("onboarding_checklists.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    task_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("onboarding_tasks.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    assignee_user_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )
    due_date: date = Field(sa_column=Column(sa.Date(), nullable=False))
    completed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(sa.DateTime(), nullable=True)
    )
    # pending | in_progress | done | skipped
    status: str = Field(
        sa_column=Column(sa.String(20), nullable=False, server_default="pending")
    )
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint(
            "checklist_id", "task_id", name="uq_onboarding_item_checklist_task"
        ),
        sa.Index("ix_onboarding_items_checklist", "checklist_id"),
        sa.Index("ix_onboarding_items_assignee", "assignee_user_id"),
        sa.Index("ix_onboarding_items_due_date", "due_date"),
        sa.Index("ix_onboarding_items_status", "status"),
    )
