from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


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
