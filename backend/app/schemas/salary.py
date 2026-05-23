from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class SalaryEmployeeRow(BaseModel):
    employee_id: int
    employee_code: str
    full_name: str
    department_id: Optional[int]
    department_name: Optional[str]
    position_title: Optional[str]
    insurance_basis_amount: Optional[Decimal]
    insurance_basis_source: Optional[str]       # 'contract' | 'manual_fixed' | 'computed'
    participation_status: Optional[str]          # 'active' | 'paused' | 'stopped'
    active_contract_insurance_salary: Optional[Decimal]
    has_discrepancy: bool


class SalaryEmployeeListPage(BaseModel):
    items: list[SalaryEmployeeRow]
    total: int
    page: int
    page_size: int


class SalaryBhxhBasisDetail(BaseModel):
    employee_id: int
    employee_code: str
    full_name: str
    department_name: Optional[str]
    position_title: Optional[str]
    insurance_basis_amount: Optional[Decimal]
    insurance_basis_source: Optional[str]
    participation_status: Optional[str]
    active_contract_id: Optional[int]
    active_contract_type: Optional[str]
    active_contract_insurance_salary: Optional[Decimal]
    active_contract_effective_from: Optional[date]
    has_discrepancy: bool


class BhxhSalaryHistoryItem(BaseModel):
    effective_date: date
    basis_amount: Decimal
    source_type: str                # 'contract' | 'manual_adjustment'
    note: Optional[str]             # loại hợp đồng hoặc lý do điều chỉnh
    decision_number: Optional[str]  # chỉ manual_adjustment
    old_basis_amount: Optional[Decimal]
    created_by_name: Optional[str]


# ── Adjustment schemas ────────────────────────────────────────────────────────

class BhxhSalaryAdjustmentCreate(BaseModel):
    employee_id: int
    new_basis_amount: Decimal = Field(gt=0)
    effective_date: date
    reason: str = Field(min_length=5, max_length=500)
    decision_number: Optional[str] = Field(default=None, max_length=100)

    @field_validator("new_basis_amount")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Mức lương BHXH phải > 0")
        return v


class BhxhSalaryAdjustmentRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: Optional[str]
    decision_number: Optional[str]
    old_basis_amount: Decimal
    new_basis_amount: Decimal
    change_direction: Literal["increase", "decrease"]
    change_amount: Decimal
    change_pct: float
    effective_date: date
    reason: str
    created_by_id: Optional[int]
    created_by_name: Optional[str]
    created_at: datetime
    insurance_change_event_id: Optional[int]


class BhxhSalaryAdjustmentListPage(BaseModel):
    items: list[BhxhSalaryAdjustmentRead]
    total: int
    page: int
    page_size: int


# ── Salary summary schemas ────────────────────────────────────────────────────

class SalarySummaryRates(BaseModel):
    bhxh_employee_rate: Decimal
    bhyt_employee_rate: Decimal
    bhtn_employee_rate: Decimal
    bhxh_employer_rate: Decimal
    bhyt_employer_rate: Decimal
    bhtn_employer_rate: Decimal


class SalarySummaryRow(BaseModel):
    stt: int
    employee_id: int
    employee_code: str
    full_name: str
    department_name: Optional[str]
    basis_amount: Decimal

    bhxh_employee: Decimal
    bhyt_employee: Decimal
    bhtn_employee: Decimal
    total_employee: Decimal

    bhxh_employer: Decimal
    bhyt_employer: Decimal
    bhtn_employer: Decimal
    total_employer: Decimal

    grand_total: Decimal


class SalarySummaryTotals(BaseModel):
    total_employees: int
    sum_basis: Decimal
    sum_bhxh_employee: Decimal
    sum_bhyt_employee: Decimal
    sum_bhtn_employee: Decimal
    sum_total_employee: Decimal
    sum_bhxh_employer: Decimal
    sum_bhyt_employer: Decimal
    sum_bhtn_employer: Decimal
    sum_total_employer: Decimal
    sum_grand_total: Decimal


class SalarySummaryPage(BaseModel):
    year: int
    month: int
    rates: SalarySummaryRates
    items: list[SalarySummaryRow]
    totals: SalarySummaryTotals
    total: int
    page: int
    page_size: int
