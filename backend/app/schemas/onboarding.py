"""Schemas Pydantic cho Onboarding Checklist (Plan 14.1)."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ── Task templates ────────────────────────────────────────────────────────────

class OnboardingTaskRead(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    group: str
    default_assignee_role: Optional[str]
    due_offset_days: int
    sort_order: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OnboardingTaskCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    group: str  # admin | it | training | specialty
    default_assignee_role: Optional[str] = None
    due_offset_days: int = 3
    sort_order: int = 0


class OnboardingTaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    group: Optional[str] = None
    default_assignee_role: Optional[str] = None
    due_offset_days: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


# ── Checklist items ───────────────────────────────────────────────────────────

class OnboardingChecklistItemRead(BaseModel):
    id: int
    checklist_id: int
    task_id: int
    task_code: str
    task_name: str
    task_group: str
    assignee_user_id: Optional[int]
    assignee_name: Optional[str]
    due_date: date
    completed_at: Optional[datetime]
    status: str  # pending | in_progress | done | skipped
    note: Optional[str]
    is_overdue: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OnboardingChecklistItemUpdate(BaseModel):
    status: str  # pending | in_progress | done | skipped
    assignee_user_id: Optional[int] = None
    note: Optional[str] = None


# ── Checklist ─────────────────────────────────────────────────────────────────

class OnboardingChecklistRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    department_name: Optional[str]
    start_date: date
    hiring_decision_id: Optional[int]
    buddy_user_id: Optional[int]
    buddy_name: Optional[str]
    status: str  # in_progress | completed | cancelled
    completion_pct: float
    items: List[OnboardingChecklistItemRead]
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OnboardingChecklistCreate(BaseModel):
    employee_id: int
    hiring_decision_id: Optional[int] = None
    buddy_user_id: Optional[int] = None


class OnboardingChecklistUpdate(BaseModel):
    buddy_user_id: Optional[int] = None
    status: Optional[str] = None  # chỉ cho cancel


class OnboardingChecklistListItem(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    department_name: Optional[str]
    start_date: date
    buddy_name: Optional[str]
    status: str
    completion_pct: float
    total_items: int
    done_items: int
    overdue_items: int
    days_since_start: int

    model_config = ConfigDict(from_attributes=True)


class OnboardingChecklistPage(BaseModel):
    items: List[OnboardingChecklistListItem]
    total: int
    page: int
    page_size: int
