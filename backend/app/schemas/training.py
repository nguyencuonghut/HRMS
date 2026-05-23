"""Schemas đào tạo (9.1)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

COURSE_TYPES: dict[str, str] = {
    "noi_bo":    "Nội bộ",
    "ben_ngoai": "Bên ngoài",
    "online":    "Online",
}

PLAN_STATUSES: dict[str, str] = {
    "draft":     "Dự thảo",
    "approved":  "Đã duyệt",
    "cancelled": "Đã hủy",
}

CourseTypeValue = Literal["noi_bo", "ben_ngoai", "online"]
PlanStatusValue = Literal["draft", "approved", "cancelled"]


# ── Course schemas ────────────────────────────────────────────────────────────

class CourseRead(BaseModel):
    model_config = {"from_attributes": True}

    id:               int
    code:             str
    name:             str
    course_type:      str
    course_type_label: str
    duration_hours:   Optional[int]
    organizer:        Optional[str]
    description:      Optional[str]
    cost_per_person:  Optional[Decimal]
    is_mandatory:     bool
    is_active:        bool
    created_at:       datetime


class CourseCreate(BaseModel):
    code:            str            = Field(max_length=50)
    name:            str            = Field(max_length=500)
    course_type:     CourseTypeValue
    duration_hours:  Optional[int]     = Field(default=None, ge=1)
    organizer:       Optional[str]     = None
    description:     Optional[str]     = None
    cost_per_person: Optional[Decimal] = Field(default=None, ge=0)
    is_mandatory:    bool              = False


class CourseUpdate(BaseModel):
    code:            Optional[str]     = Field(default=None, max_length=50)
    name:            Optional[str]     = Field(default=None, max_length=500)
    course_type:     Optional[CourseTypeValue] = None
    duration_hours:  Optional[int]     = Field(default=None, ge=1)
    organizer:       Optional[str]     = None
    description:     Optional[str]     = None
    cost_per_person: Optional[Decimal] = Field(default=None, ge=0)
    is_mandatory:    Optional[bool]    = None
    is_active:       Optional[bool]    = None


class CourseListPage(BaseModel):
    items:     List[CourseRead]
    total:     int
    page:      int
    page_size: int


# ── Plan-course schemas ───────────────────────────────────────────────────────

class PlanCourseRead(BaseModel):
    model_config = {"from_attributes": True}

    id:               int
    plan_id:          int
    course_id:        int
    course_code:      str
    course_name:      str
    course_type_label: str
    duration_hours:   Optional[int]
    target_count:     Optional[int]
    scheduled_date:   Optional[date]
    note:             Optional[str]


class PlanCourseCreate(BaseModel):
    course_id:      int
    target_count:   Optional[int]  = Field(default=None, ge=1)
    scheduled_date: Optional[date] = None
    note:           Optional[str]  = None


class PlanCourseUpdate(BaseModel):
    target_count:   Optional[int]  = None
    scheduled_date: Optional[date] = None
    note:           Optional[str]  = None


# ── Plan schemas ──────────────────────────────────────────────────────────────

class PlanRead(BaseModel):
    model_config = {"from_attributes": True}

    id:               int
    title:            str
    year:             int
    quarter:          Optional[int]
    department_id:    Optional[int]
    department_name:  Optional[str]
    status:           str
    status_label:     str
    description:      Optional[str]
    created_by_name:  Optional[str]
    created_at:       datetime
    course_count:     int


class PlanReadDetail(PlanRead):
    courses: List[PlanCourseRead]


class PlanCreate(BaseModel):
    title:         str           = Field(max_length=500)
    year:          int           = Field(ge=2000, le=2100)
    quarter:       Optional[int] = Field(default=None, ge=1, le=4)
    department_id: Optional[int] = None
    description:   Optional[str] = None


class PlanUpdate(BaseModel):
    title:       Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None


class PlanListPage(BaseModel):
    items:     List[PlanRead]
    total:     int
    page:      int
    page_size: int
