"""Schemas báo cáo đào tạo (9.4)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class CourseCompletionStat(BaseModel):
    course_id: int
    course_name: str
    course_type_label: str
    total_assigned: int
    completed: int
    not_completed: int
    in_progress: int
    completion_rate: float


class DepartmentTrainingStat(BaseModel):
    department_id: Optional[int]
    department_name: Optional[str]
    total_records: int
    completed: int
    completion_rate: float
    total_cost: Optional[Decimal]


class TrainingReportSummary(BaseModel):
    from_date: date
    to_date: date
    department_id: Optional[int]
    department_name: Optional[str]
    course_id: Optional[int]
    course_name: Optional[str]
    total_records: int
    total_completed: int
    total_not_completed: int
    total_in_progress: int
    total_cost: Decimal
    avg_completion_rate: float
    by_course: List[CourseCompletionStat]
    by_department: List[DepartmentTrainingStat]


class IncompleteMandatoryEmployee(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: Optional[str]
    incomplete_courses: List[str]
    incomplete_count: int
