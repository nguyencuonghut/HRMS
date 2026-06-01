"""Schemas Pydantic cho Báo cáo Bảo hiểm (11.4)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class InsuranceDashboardKPI(BaseModel):
    """KPI tổng quan tháng/năm được chọn."""
    year: int
    month: Optional[int]
    department_id: Optional[int]

    # Tham gia BHXH
    participating_count: int            # đang active
    total_active_employees: int         # tổng nhân viên đang làm
    participation_rate: float           # %

    # Quỹ lương
    total_basis_amount: Decimal         # VND

    # Biến động tháng
    increased_count: int
    decreased_count: int
    net_change: int                     # increased - decreased


class MonthlyChangePoint(BaseModel):
    month: int                          # 1–12
    increased: int
    decreased: int
    net: int


class InsuranceMonthlyChangesResponse(BaseModel):
    year: int
    department_id: Optional[int]
    data: list[MonthlyChangePoint]      # 12 phần tử


class PayrollFundPoint(BaseModel):
    month: int
    added_amount: Decimal               # từ tăng trong tháng
    removed_amount: Decimal             # từ giảm trong tháng
    snapshot_amount: Optional[Decimal]  # tổng quỹ hiện tại (chỉ tháng hiện tại)


class InsurancePayrollFundResponse(BaseModel):
    year: int
    department_id: Optional[int]
    data: list[PayrollFundPoint]


class NonParticipantRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    employee_code: str
    full_name: str
    department_name: str
    participation_status: Optional[str]     # 'paused' | 'stopped' | None (chưa có profile)
    status_effective_from: Optional[date]
    status_note: Optional[str]
    company_bhxh_joined_date: Optional[date]


class InsuranceNonParticipantsResponse(BaseModel):
    items: list[NonParticipantRow]
    total: int
    page: int
    page_size: int


class DepartmentBreakdownRow(BaseModel):
    department_id: int
    department_name: str
    participating_count: int
    total_count: int
    participation_rate: float           # %
    total_basis_amount: Optional[Decimal]


class InsuranceDepartmentBreakdownResponse(BaseModel):
    year: int
    month: Optional[int]
    items: list[DepartmentBreakdownRow]


class EmployeeHistoryPoint(BaseModel):
    effective_date: date
    change_type: str                    # 'increase' | 'decrease'
    change_reason: str
    basis_amount: Optional[Decimal]
    participation_status_after: Optional[str]


class InsuranceEmployeeHistoryResponse(BaseModel):
    employee_id: int
    full_name: str
    current_participation_status: Optional[str]
    current_basis_amount: Optional[Decimal]
    history: list[EmployeeHistoryPoint]
