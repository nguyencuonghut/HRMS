from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class InsuranceChangeEventRead(BaseModel):
    id: int
    employee_id: int

    change_type: str
    change_reason: str
    ibhxh_reason_code: str
    effective_date: date
    period_year: int
    period_month: int

    employee_name_snapshot: str
    date_of_birth_snapshot: date
    gender_snapshot: str
    nationality_code_snapshot: str
    identity_number_snapshot: Optional[str]

    contract_number_snapshot: Optional[str]
    contract_type_code_snapshot: Optional[str]
    contract_signed_date_snapshot: Optional[date]
    contract_from_snapshot: Optional[date]
    contract_to_snapshot: Optional[date]

    bhxh_code_snapshot: Optional[str]
    basis_amount: Decimal
    allowances_amount: Decimal
    bhyt_clinic_name_snapshot: Optional[str]
    bhyt_clinic_code_snapshot: Optional[str]
    policy_version_code_snapshot: Optional[str]
    employee_rate_total_snapshot: Decimal
    employer_rate_total_snapshot: Decimal
    ethnicity_bhxh_code_snapshot: Optional[str]

    old_status: Optional[str]
    new_status: str

    suggested_declaration_year: int
    suggested_declaration_month: int

    is_manual: bool
    note: Optional[str]
    created_by_id: Optional[int]
    created_at: datetime


class InsuranceChangeEventCreate(BaseModel):
    employee_id: int
    change_type: str = Field(pattern=r"^(increase|decrease)$")
    change_reason: str
    effective_date: date
    note: Optional[str] = None


class InsuranceMonthlyChangeSummary(BaseModel):
    period_year: int
    period_month: int
    increase_count: int
    decrease_count: int
    total_basis_increase: Decimal
    total_basis_decrease: Decimal


class InsuranceChangeEventListPage(BaseModel):
    items: list[InsuranceChangeEventRead]
    total: int
    page: int
    page_size: int
