"""Schemas cho báo cáo nhân sự (11.2)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class EmployeeListItem(BaseModel):
    id: int
    employee_code: Optional[str] = None
    full_name: str
    gender: str
    date_of_birth: Optional[date] = None
    status: str
    start_date: date
    resigned_date: Optional[date] = None
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
