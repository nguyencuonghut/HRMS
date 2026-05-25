"""Schemas tuyển dụng ATS (13.1 — Kế hoạch & Yêu cầu tuyển dụng)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

JRReasonType = Literal["new", "replacement", "expansion"]
JRReasonLabels: dict[str, str] = {
    "new":         "Vị trí mới",
    "replacement": "Thay thế nhân sự",
    "expansion":   "Mở rộng",
}

JRStatus = Literal["draft", "pending_review", "approved", "in_progress", "completed", "cancelled"]
JRStatusLabels: dict[str, str] = {
    "draft":          "Nháp",
    "pending_review": "Chờ duyệt",
    "approved":       "Đã duyệt",
    "in_progress":    "Đang tuyển",
    "completed":      "Hoàn thành",
    "cancelled":      "Đã hủy",
}


# ── Headcount Plan ────────────────────────────────────────────────────────────


class HeadcountPlanCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    department_id: Optional[int] = None
    job_position_id: Optional[int] = None
    current_count: int = Field(default=0, ge=0)
    planned_count: int = Field(ge=1)
    reason: Optional[str] = None


class HeadcountPlanUpdate(BaseModel):
    current_count: Optional[int] = Field(default=None, ge=0)
    planned_count: Optional[int] = Field(default=None, ge=1)
    reason: Optional[str] = None


class HeadcountPlanRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    year: int
    department_id: Optional[int]
    department_name: Optional[str]
    job_position_id: Optional[int]
    job_position_name: Optional[str]
    current_count: int
    planned_count: int
    reason: Optional[str]
    created_by_id: Optional[int]
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime


class HeadcountPlanListPage(BaseModel):
    items: list[HeadcountPlanRead]
    total: int
    page: int
    page_size: int


# ── Job Requisition ───────────────────────────────────────────────────────────


class JobRequisitionCreate(BaseModel):
    job_position_id: int
    department_id: int
    headcount_plan_id: Optional[int] = None
    quantity: int = Field(default=1, ge=1, le=100)
    reason_type: JRReasonType
    deadline: Optional[date] = None
    salary_min: Optional[Decimal] = Field(default=None, ge=0)
    salary_max: Optional[Decimal] = Field(default=None, ge=0)
    jd_description: Optional[str] = None
    jd_requirements: Optional[str] = None
    internal_note: Optional[str] = None

    @model_validator(mode="after")
    def validate_salary_range(self) -> "JobRequisitionCreate":
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("salary_min không được lớn hơn salary_max")
        return self


class JobRequisitionUpdate(BaseModel):
    department_id: Optional[int] = None
    headcount_plan_id: Optional[int] = None
    quantity: Optional[int] = Field(default=None, ge=1, le=100)
    reason_type: Optional[JRReasonType] = None
    deadline: Optional[date] = None
    salary_min: Optional[Decimal] = Field(default=None, ge=0)
    salary_max: Optional[Decimal] = Field(default=None, ge=0)
    jd_description: Optional[str] = None
    jd_requirements: Optional[str] = None
    internal_note: Optional[str] = None


class JobRequisitionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    code: str
    job_position_id: int
    job_position_name: str
    department_id: int
    department_name: str
    headcount_plan_id: Optional[int]
    quantity: int
    quantity_remaining: int
    reason_type: str
    reason_type_label: str
    deadline: Optional[date]
    salary_min: Optional[Decimal]
    salary_max: Optional[Decimal]
    # JD đã merge: dùng override nếu có, fallback về job_position
    effective_description: Optional[str]
    effective_requirements: Optional[str]
    status: str
    status_label: str
    submitted_at: Optional[datetime]
    submitted_by_name: Optional[str]
    approved_by_id: Optional[int]
    approved_by_name: Optional[str]
    approved_at: Optional[datetime]
    rejection_note: Optional[str]
    internal_note: Optional[str]
    created_by_id: int
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime


class JobRequisitionListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    code: str
    job_position_name: str
    department_name: str
    quantity: int
    quantity_remaining: int
    reason_type: str
    reason_type_label: str
    deadline: Optional[date]
    status: str
    status_label: str
    created_at: datetime


class JobRequisitionListPage(BaseModel):
    items: list[JobRequisitionListItem]
    total: int
    page: int
    page_size: int


class RejectRequest(BaseModel):
    rejection_note: str = Field(min_length=1)


class CancelRequest(BaseModel):
    reason: Optional[str] = None


# ── Budget ────────────────────────────────────────────────────────────────────


class BudgetItemCreate(BaseModel):
    item_name: str = Field(min_length=1, max_length=200)
    estimated_amount: Optional[Decimal] = Field(default=None, ge=0)
    actual_amount: Optional[Decimal] = Field(default=None, ge=0)
    note: Optional[str] = None


class BudgetItemUpdate(BaseModel):
    item_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    estimated_amount: Optional[Decimal] = Field(default=None, ge=0)
    actual_amount: Optional[Decimal] = Field(default=None, ge=0)
    note: Optional[str] = None


class BudgetItemRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    job_requisition_id: int
    item_name: str
    estimated_amount: Optional[Decimal]
    actual_amount: Optional[Decimal]
    note: Optional[str]
    created_by_id: Optional[int]
    created_at: datetime


class BudgetSummary(BaseModel):
    items: list[BudgetItemRead]
    total_estimated: Decimal
    total_actual: Decimal
