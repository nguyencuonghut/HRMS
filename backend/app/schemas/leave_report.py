from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class EmployeeSummaryRow(BaseModel):
    employee_id:      int
    employee_code:    str
    employee_name:    str
    department_name:  Optional[str]
    leave_type_id:    int
    leave_type_name:  str
    leave_type_code:  str
    allocated_days:   float
    carryover_days:   float
    carryover_expires: Optional[date]
    used_days:        float
    remaining_days:   float
    record_count:     int


class EmployeeSummaryReport(BaseModel):
    year:      int
    items:     list[EmployeeSummaryRow]
    total:     int
    page:      int
    page_size: int


class DepartmentSummaryRow(BaseModel):
    department_id:         Optional[int]
    department_name:       Optional[str]
    leave_type_id:         int
    leave_type_name:       str
    employee_count:        int
    total_records:         int
    total_days_taken:      float
    avg_days_per_employee: float


class DepartmentSummaryReport(BaseModel):
    year:       int
    month_from: Optional[int]
    month_to:   Optional[int]
    items:      list[DepartmentSummaryRow]


class YearEndRow(BaseModel):
    employee_id:     int
    employee_code:   str
    employee_name:   str
    department_name: Optional[str]
    leave_type_name: str
    leave_type_code: str
    allocated_days:  float
    carryover_days:  float
    used_days:       float
    remaining_days:  float
    will_carry:      float


class YearEndReport(BaseModel):
    year:      int
    items:     list[YearEndRow]
    total:     int
    page:      int
    page_size: int
