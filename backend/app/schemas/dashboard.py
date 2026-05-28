"""Schemas cho dashboard tổng quan nhân sự (11.1)."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    total_headcount: int
    new_hires_this_month: int
    resigned_this_month: int
    headcount_start_of_month: int
    turnover_rate: float
    as_of_date: date


class HeadcountByDeptItem(BaseModel):
    department_id: int
    department_name: str
    parent_department_id: Optional[int] = None
    headcount: int
    direct_headcount: int
    child_department_count: int


class MonthlyTrendItem(BaseModel):
    month: int = Field(ge=1, le=12)
    new_hires: int
    resigned_count: int
    net_change: int


class MonthlyTrendReport(BaseModel):
    year: int
    department_id: Optional[int]
    monthly: List[MonthlyTrendItem]


class GenderItem(BaseModel):
    label: str
    count: int
    percentage: float


class StructureGroupItem(BaseModel):
    label: str
    count: int


class StructureReport(BaseModel):
    gender: List[GenderItem]
    age_group: List[StructureGroupItem]
    education_level: List[StructureGroupItem]
    tenure_group: List[StructureGroupItem]
