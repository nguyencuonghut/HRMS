from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class ActiveProbationRow(BaseModel):
    employee_id: int
    employee_name: str
    employee_code: str
    department_id: Optional[int]
    department_name: Optional[str]
    probation_start_date: Optional[date]
    probation_end_date: Optional[date]
    days_remaining: Optional[int]
    urgency: str  # normal | warning | critical
    onboarding_status: Optional[str]
    completion_pct: Optional[float]
    evaluation_result: str  # not_started | pending | passed | failed | extended


class ActiveProbationReport(BaseModel):
    items: List[ActiveProbationRow]
    total: int


class ProbationHistoryRow(BaseModel):
    employee_id: int
    employee_name: str
    employee_code: str
    employee_status: str          # probation | official | resigned | terminated | ...
    department_id: Optional[int]
    department_name: Optional[str]
    probation_start_date: Optional[date]
    probation_end_date: Optional[date]
    days_remaining: Optional[int] # None nếu không còn đang thử việc
    onboarding_status: Optional[str]
    completion_pct: Optional[float]
    evaluation_result: str        # not_started | pending | passed | failed | extended
    evaluation_status: Optional[str]  # draft | submitted | approved | None


class ProbationHistoryReport(BaseModel):
    period_start: Optional[date]   # None nếu không filter
    period_end: Optional[date]     # None nếu không filter
    items: List[ProbationHistoryRow]
    total: int
    page: int
    page_size: int


class ChecklistCompletionRow(BaseModel):
    department_id: int
    department_name: str
    total_checklists: int
    completed_count: int
    completion_rate: float  # 0-100%
    avg_completion_pct: float  # 0-100% average progress


class ChecklistCompletionReport(BaseModel):
    period_start: date
    period_end: date
    items: List[ChecklistCompletionRow]


class ProbationPassRateStat(BaseModel):
    group_id: Optional[int]
    group_name: str
    passed: int
    failed: int
    extended: int
    total_decided: int
    pass_rate: Optional[float]  # None if total=0


class MonthlyProbationTrend(BaseModel):
    year: int
    month: int
    passed: int
    failed: int
    extended: int
    total: int


class ProbationPassRateReport(BaseModel):
    period_start: date
    period_end: date
    overall: ProbationPassRateStat
    by_department: List[ProbationPassRateStat]
    by_position: List[ProbationPassRateStat]
    monthly_trend: List[MonthlyProbationTrend]


class FailureKeywordCount(BaseModel):
    keyword: str
    count: int
    pct: float


class FailureCommentItem(BaseModel):
    employee_id: int
    employee_name: str
    evaluation_date: date
    manager_comment: Optional[str]


class FailureReasonReport(BaseModel):
    total_failed: int
    reasons: List[FailureKeywordCount]
    raw_comments: List[FailureCommentItem]
