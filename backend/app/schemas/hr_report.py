"""Schemas cho báo cáo nhân sự (11.2)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EmployeeListItem(BaseModel):
    id: int
    employee_code: Optional[str] = None
    full_name: str
    gender: str
    date_of_birth: Optional[date] = None
    status: str
    start_date: date
    resigned_date: Optional[date] = None
    resigned_reason_type: Optional[str] = None
    resigned_reason_note: Optional[str] = None
    is_active: bool
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    job_title_name: Optional[str] = None
    contract_category_name: Optional[str] = None
    document_kind: Optional[str] = None
    tenure_years: int

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    items: list[EmployeeListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class MovementPeriodRow(BaseModel):
    period_label: str
    period_start: date
    period_end: date
    hired_count: int
    resigned_count: int
    transfer_count: int
    net_change: int


class MovementReportResponse(BaseModel):
    group_by: str
    start_date: date
    end_date: date
    rows: list[MovementPeriodRow]
    total_hired: int
    total_resigned: int
    total_transfers: int


class TenureGroupDetail(BaseModel):
    id: int
    full_name: str
    department_name: Optional[str] = None
    start_date: date
    tenure_years: int


class TenureGroup(BaseModel):
    group_key: str
    group_label: str
    headcount: int
    percentage: float
    avg_tenure_years: float
    employees: list[TenureGroupDetail]


class TenureReportResponse(BaseModel):
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    total_active: int
    avg_tenure_years: float
    groups: list[TenureGroup]


class JobTitleHeadcount(BaseModel):
    job_title_id: Optional[int] = None
    job_title_name: Optional[str] = None
    job_level: Optional[int] = None
    headcount: int


class DepartmentNode(BaseModel):
    department_id: int
    department_name: str
    parent_id: Optional[int] = None
    total_headcount: int
    direct_headcount: int
    by_job_title: list[JobTitleHeadcount]
    children: list["DepartmentNode"] = Field(default_factory=list)


DepartmentNode.model_rebuild()


class OrgStructureResponse(BaseModel):
    total_headcount: int
    department_count: int
    tree: list[DepartmentNode]


class RetirementAgeThresholdRead(BaseModel):
    id: int
    gender: str
    applicable_year: int
    age_years: int
    age_months: int


class RetirementAgeThresholdInput(BaseModel):
    gender: str
    applicable_year: int = Field(..., ge=1900)
    age_years: int = Field(..., ge=0)
    age_months: int = Field(..., ge=0, le=11)

    @field_validator("gender")
    @classmethod
    def _validate_gender(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"male", "female"}:
            raise ValueError("Giới tính phải là male hoặc female")
        return normalized


class RetirementAgePolicyRead(BaseModel):
    id: int
    name: str
    legal_basis_summary: Optional[str]
    effective_from: date
    effective_to: Optional[date]
    note: Optional[str]
    thresholds: list[RetirementAgeThresholdRead]
    created_at: datetime
    updated_at: Optional[datetime]


class RetirementAgePolicyCreate(BaseModel):
    name: str = Field(..., max_length=255)
    legal_basis_summary: Optional[str] = Field(None, max_length=4000)
    effective_from: date
    note: Optional[str] = Field(None, max_length=4000)
    thresholds: list[RetirementAgeThresholdInput]

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Tên policy không được để trống")
        return stripped


class RetirementAgePolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    legal_basis_summary: Optional[str] = Field(None, max_length=4000)
    note: Optional[str] = Field(None, max_length=4000)
    thresholds: Optional[list[RetirementAgeThresholdInput]] = None

    @field_validator("name")
    @classmethod
    def _strip_optional_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Tên policy không được để trống")
        return stripped


class RetirementAgePoliciesRead(BaseModel):
    current: Optional[RetirementAgePolicyRead]
    history: list[RetirementAgePolicyRead]


class OlderWorkerListItem(BaseModel):
    id: int
    employee_code: Optional[str] = None
    full_name: str
    gender: str
    date_of_birth: date
    start_date: date
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    job_title_name: Optional[str] = None
    retirement_age_years: int
    retirement_age_months: int
    retirement_date: date
    age_years: int
    age_months: int
    months_beyond_retirement: int


class OlderWorkerSummary(BaseModel):
    total: int
    male_count: int
    female_count: int


class OlderWorkerReportResponse(BaseModel):
    year: int
    month: int
    as_of_date: date
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    gender: Optional[str] = None
    policy_id: int
    policy_name: str
    legal_basis_summary: Optional[str] = None
    male_threshold_label: Optional[str] = None
    female_threshold_label: Optional[str] = None
    summary: OlderWorkerSummary
    items: list[OlderWorkerListItem]
