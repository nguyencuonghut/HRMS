"""Schemas Pydantic cho Quản lý thử việc (Plan 14.2)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ── Legal check ───────────────────────────────────────────────────────────────

class ProbationLegalCheck(BaseModel):
    is_valid: bool
    violations: List[str]
    warnings: List[str]
    probation_days: int
    probation_limit: int
    job_level: Optional[int]
    job_level_group: str


# ── Evaluation schemas ────────────────────────────────────────────────────────

class ProbationEvaluationCreate(BaseModel):
    evaluation_date: date
    evaluator_id: int
    attitude_score: Optional[Decimal] = None
    competence_score: Optional[Decimal] = None
    culture_score: Optional[Decimal] = None
    kpi_score: Optional[Decimal] = None
    result: str = "pending"
    extension_days: Optional[int] = None
    manager_comment: Optional[str] = None


class ProbationEvaluationUpdate(BaseModel):
    evaluation_date: Optional[date] = None
    evaluator_id: Optional[int] = None
    attitude_score: Optional[Decimal] = None
    competence_score: Optional[Decimal] = None
    culture_score: Optional[Decimal] = None
    kpi_score: Optional[Decimal] = None
    result: Optional[str] = None
    extension_days: Optional[int] = None
    manager_comment: Optional[str] = None
    hr_comment: Optional[str] = None
    hr_reviewer_id: Optional[int] = None


class ProbationEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: Optional[str] = None
    job_record_id: int
    evaluation_date: date
    evaluator_id: int
    evaluator_name: Optional[str] = None
    hr_reviewer_id: Optional[int] = None
    attitude_score: Optional[Decimal] = None
    competence_score: Optional[Decimal] = None
    culture_score: Optional[Decimal] = None
    kpi_score: Optional[Decimal] = None
    overall_score: Optional[Decimal] = None
    manager_comment: Optional[str] = None
    hr_comment: Optional[str] = None
    result: str
    extension_days: Optional[int] = None
    status: str
    approved_by_id: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ProbationApproveRequest(BaseModel):
    result: str
    hr_comment: Optional[str] = None
    extension_days: Optional[int] = None


# ── Detail read ───────────────────────────────────────────────────────────────

class ProbationDetailRead(BaseModel):
    employee_id: int
    employee_name: str
    employee_code: Optional[str] = None
    department_name: Optional[str] = None
    job_title_name: Optional[str] = None
    job_title_level: Optional[int] = None
    status: str
    probation_mode: str = "none"
    can_edit_evaluation: bool = False
    can_generate_contract: bool = False
    approval_triggers_workflow: bool = False
    probation_start_date: Optional[date] = None
    probation_end_date: Optional[date] = None
    official_date: Optional[date] = None
    days_remaining: Optional[int] = None
    legal_check: ProbationLegalCheck
    evaluation: Optional[ProbationEvaluationRead] = None
    contracts: list = []
