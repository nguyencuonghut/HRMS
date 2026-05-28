"""Schemas Pydantic cho Báo cáo Hợp đồng (11.5)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict


# ── KPI Summary ───────────────────────────────────────────────────────────────

class ContractSummaryOut(BaseModel):
    total_active: int
    expiring_0_30: int      # 0–30 ngày
    expiring_31_60: int     # 31–60 ngày
    expiring_61_90: int     # 61–90 ngày
    already_expired: int    # effective_to < today, status active/expired
    renewal_rate: float     # phần trăm, làm tròn 1 chữ số thập phân
    as_of_date: date


# ── Danh sách sắp hết hạn ─────────────────────────────────────────────────────

UrgencyTier = Literal["CRITICAL", "WARNING", "NOTICE"]


class ContractExpiringRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contract_id: int
    contract_number: str
    employee_id: int
    employee_code: str
    employee_name: str
    department_id: Optional[int]
    department_name: Optional[str]
    category_name: str           # tên loại HĐ từ ContractCategory.name
    business_group: str          # probation | standard | ...
    effective_from: date
    effective_to: date
    days_remaining: int
    urgency: UrgencyTier
    signed_date: date
    insurance_salary: Optional[Decimal]


class ContractExpiringPage(BaseModel):
    items: list[ContractExpiringRow]
    total: int
    page: int
    page_size: int
    days_ahead: int


# ── Breakdown theo loại ────────────────────────────────────────────────────────

class ContractTypeBreakdown(BaseModel):
    category_id: int
    category_name: str
    business_group: str
    legal_contract_type: Optional[str]
    total: int
    active: int
    expired: int
    terminated: int
    percentage: float            # % trên tổng HĐ gốc


class ContractByTypeOut(BaseModel):
    items: list[ContractTypeBreakdown]
    total_contracts: int         # tổng HĐ gốc (không phụ lục)
    department_id: Optional[int]
    year: Optional[int]


# ── Dự báo hết hạn ────────────────────────────────────────────────────────────

class ForecastMonthItem(BaseModel):
    year_month: str              # "2025-06"
    expiring_count: int


class ContractForecastOut(BaseModel):
    months: list[ForecastMonthItem]
    months_ahead: int
    total_expiring: int


# ── Lịch sử nhân viên ─────────────────────────────────────────────────────────

class ContractHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contract_id: int
    contract_number: str
    category_name: str
    document_kind: str           # labor_contract | contract_appendix
    is_appendix: bool            # parent_contract_id IS NOT NULL
    parent_contract_id: Optional[int]
    effective_from: date
    effective_to: Optional[date]
    signed_date: date
    status: str
    insurance_salary: Optional[Decimal]
    file_name: Optional[str]


class ContractHistoryOut(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    items: list[ContractHistoryItem]
    total: int
