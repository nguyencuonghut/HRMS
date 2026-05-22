from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class InsurancePeriodReportCreate(BaseModel):
    period_year: int = Field(..., ge=2000, le=2100)
    period_month: int = Field(..., ge=1, le=12)
    submission_type: Literal["initial", "supplement", "correction"] = "initial"
    note: Optional[str] = None


class InsurancePeriodReportUpdate(BaseModel):
    note: Optional[str] = None


class InsurancePeriodReportRead(BaseModel):
    id: int
    period_year: int
    period_month: int
    submission_type: Literal["initial", "supplement", "correction"]
    status: Literal["draft", "pending_review", "approved", "rejected"]
    prepared_by_id: Optional[int]
    prepared_at: Optional[datetime]
    reviewed_by_id: Optional[int]
    reviewed_at: Optional[datetime]
    review_note: Optional[str]
    note: Optional[str]
    line_item_count: int
    adjusted_count: int
    missing_clinic_code_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InsurancePeriodReportListPage(BaseModel):
    items: list[InsurancePeriodReportRead]
    total: int
    page: int
    page_size: int


class InsuranceReportLineItemRead(BaseModel):
    id: int
    report_id: int
    event_id: int
    employee_name: str
    employee_code: str
    bhxh_code: Optional[str]
    change_type: Literal["increase", "decrease"]
    change_reason: str
    effective_date: date
    basis_amount: Decimal
    bhyt_clinic_code: Optional[str]
    suggested_year: int
    suggested_month: int
    declared_year: int
    declared_month: int
    is_adjusted: bool
    adjustment_note: Optional[str]
    sort_order: int

    model_config = {"from_attributes": True}


class InsurancePeriodReportDetail(InsurancePeriodReportRead):
    line_items: list[InsuranceReportLineItemRead]


class InsuranceReportLineItemCreate(BaseModel):
    event_id: int
    declared_year: Optional[int] = Field(default=None, ge=2000, le=2100)
    declared_month: Optional[int] = Field(default=None, ge=1, le=12)


class InsuranceReportLineItemUpdate(BaseModel):
    declared_year: int = Field(..., ge=2000, le=2100)
    declared_month: int = Field(..., ge=1, le=12)
    adjustment_note: str = Field(..., min_length=1)

    @field_validator("adjustment_note")
    @classmethod
    def _strip_note(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Lý do điều chỉnh không được để trống")
        return stripped


class ApproveBody(BaseModel):
    note: Optional[str] = None


class RejectBody(BaseModel):
    review_note: str = Field(..., min_length=1)

    @field_validator("review_note")
    @classmethod
    def _strip_note(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Lý do từ chối không được để trống")
        return stripped
