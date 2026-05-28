"""Schemas Pydantic cho Leave Analytics (11.3)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel


# ── KPI + Trend ────────────────────────────────────────────────────────────────

class MonthlyTrendPoint(BaseModel):
    month: int              # 1–12
    total_days: float
    total_records: int
    employee_count: int


class LeaveAnalyticsSummary(BaseModel):
    year: int
    department_id: int | None

    total_days_ytd: float       # Tổng ngày nghỉ YTD
    avg_usage_rate: float       # % sử dụng phép bình quân (0–100)
    employees_not_taken: int    # Số NV chưa dùng phép năm nào
    days_expiring_30d: float    # Ngày tồn sắp hết hạn trong 30 ngày

    monthly_trend: list[MonthlyTrendPoint]  # Luôn 12 phần tử


# ── Thống kê theo loại phép ───────────────────────────────────────────────────

class LeaveTypeStatRow(BaseModel):
    leave_type_id: int
    leave_type_name: str
    color_tag: str | None
    record_count: int
    total_days: float
    unique_employees: int
    percentage: float           # % tổng ngày trong tập kết quả


class LeaveByTypeReport(BaseModel):
    year: int
    department_id: int | None
    items: list[LeaveTypeStatRow]
    grand_total_days: float


# ── Monthly Heatmap ───────────────────────────────────────────────────────────

class HeatmapDeptRow(BaseModel):
    dept_id: int | None
    dept_name: str | None
    monthly_days: dict[int, float]   # key: 1–12, value: tổng ngày nghỉ
    annual_total: float


class MonthlyHeatmapReport(BaseModel):
    year: int
    departments: list[HeatmapDeptRow]
    company_monthly: dict[int, float]   # key: 1–12


# ── Top Employees ─────────────────────────────────────────────────────────────

class TopEmployeeRow(BaseModel):
    rank: int
    employee_id: int
    employee_code: str
    employee_name: str
    dept_name: str | None
    total_days_taken: float
    record_count: int
    total_entitled: float       # allocated + carryover
    usage_rate: float           # total_days_taken / total_entitled * 100


class TopEmployeesReport(BaseModel):
    year: int
    department_id: int | None
    items: list[TopEmployeeRow]


# ── Expiring Balance ──────────────────────────────────────────────────────────

class ExpiringBalanceRow(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    dept_name: str | None
    leave_type_name: str
    carryover_days: float
    remaining_days: float
    carryover_expires: date
    days_until_expire: int      # số ngày còn lại trước khi hết hạn


class ExpiringBalanceReport(BaseModel):
    expire_days: int            # ngưỡng filter (30/60/90)
    year: int
    department_id: int | None
    items: list[ExpiringBalanceRow]
    total_expiring_days: float  # tổng ngày sắp bị mất


# ── Department Comparison ─────────────────────────────────────────────────────

class DeptComparisonRow(BaseModel):
    dept_id: int | None
    dept_name: str | None
    employee_count: int
    total_days_taken: float
    avg_days_per_employee: float
    allocated_total: float
    usage_rate: float           # total_days_taken / allocated_total * 100


class DeptComparisonReport(BaseModel):
    year: int
    items: list[DeptComparisonRow]
