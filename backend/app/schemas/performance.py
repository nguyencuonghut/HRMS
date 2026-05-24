"""Schemas hiệu suất KPI (10.1 + 10.2 + 10.3 + 10.4)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


# ── KPI Tháng (10.1) ─────────────────────────────────────────────────────────

class KpiMonthlyRead(BaseModel):
    model_config = {"from_attributes": True}

    id:               int
    employee_id:      int
    employee_code:    str
    employee_name:    str
    department_name:  Optional[str]
    year:             int
    month:            int
    score:            Decimal
    note:             Optional[str]
    created_by_name:  Optional[str]
    created_at:       datetime
    updated_at:       datetime


class KpiMonthlyCreate(BaseModel):
    employee_id:  int
    year:         int     = Field(ge=2000, le=2100)
    month:        int     = Field(ge=1, le=12)
    score:        Decimal = Field(ge=0, le=100)
    note:         Optional[str] = None


class KpiMonthlyUpdate(BaseModel):
    score:  Optional[Decimal] = Field(default=None, ge=0, le=100)
    note:   Optional[str]     = None


class KpiMonthlyListPage(BaseModel):
    items:     List[KpiMonthlyRead]
    total:     int
    page:      int
    page_size: int


class KpiImportResult(BaseModel):
    created:  int
    updated:  int
    skipped:  int
    errors:   List[str]


# ── Đánh giá cuối năm (10.2) ─────────────────────────────────────────────────

RatingValue = str   # "xuat_sac" | "tot" | "dat" | "can_cai_thien"


class MonthlyScore(BaseModel):
    month: int
    score: Decimal


class YearlyKpiSummary(BaseModel):
    employee_id:      int
    employee_code:    str
    employee_name:    str
    department_name:  Optional[str]
    year:             int
    monthly_scores:   List[MonthlyScore]
    months_count:     int
    avg_score:        Optional[Decimal]
    has_discipline:   bool
    suggested_rating: Optional[str]
    has_review:       bool
    review_id:        Optional[int]


class YearlyReviewRead(BaseModel):
    id:               int
    employee_id:      int
    employee_code:    str
    employee_name:    str
    department_name:  Optional[str]
    year:             int
    months_count:     int
    avg_score:        Optional[Decimal]
    rating:           str
    rating_label:     str
    review_note:      Optional[str]
    created_by_name:  Optional[str]
    created_at:       datetime
    updated_at:       datetime


class YearlyReviewCreate(BaseModel):
    employee_id:  int
    year:         int           = Field(ge=2000, le=2100)
    rating:       RatingValue
    review_note:  Optional[str] = None


class YearlyReviewUpdate(BaseModel):
    rating:       Optional[RatingValue] = None
    review_note:  Optional[str]         = None


class YearlyReviewListPage(BaseModel):
    items:     List[YearlyReviewRead]
    total:     int
    page:      int
    page_size: int


# ── Liên kết kết quả đánh giá (10.3) ─────────────────────────────────────────

class RewardFromReviewRequest(BaseModel):
    reward_type_id: int
    decision_date:  date
    amount:         Optional[Decimal] = None
    note:           Optional[str]     = None


class TrainingFromReviewRequest(BaseModel):
    course_id: int
    plan_id:   Optional[int] = None
    note:      Optional[str] = None


# ── Báo cáo hiệu suất (10.4) ─────────────────────────────────────────────────

class RatingCount(BaseModel):
    rating:       str
    rating_label: str
    count:        int
    percentage:   float


class RatingDistributionReport(BaseModel):
    year:             int
    total_reviewed:   int
    total_employees:  int
    coverage_rate:    float
    distribution:     List[RatingCount]


class DepartmentKpiStat(BaseModel):
    department_id:    Optional[int]
    department_name:  Optional[str]
    employee_count:   int
    avg_score:        Optional[Decimal]
    min_score:        Optional[Decimal]
    max_score:        Optional[Decimal]
    months_data_count: int


class MonthlyPoint(BaseModel):
    month:          int
    avg_score:      Optional[Decimal]
    employee_count: int


class MonthlyKpiTrend(BaseModel):
    year:            int
    department_id:   Optional[int]
    department_name: Optional[str]
    points:          List[MonthlyPoint]
