"""Schemas hiệu suất KPI (10.1 + 10.2)."""
from __future__ import annotations

from datetime import datetime
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
