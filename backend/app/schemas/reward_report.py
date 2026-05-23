"""Schemas báo cáo khen thưởng – kỷ luật (8.3)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.schemas.discipline import DisciplineRead
from app.schemas.reward import RewardRead


class RewardTypeStat(BaseModel):
    reward_type_id: int
    reward_type_name: str
    count: int
    total_value: Optional[Decimal]  # None if non-monetary


class DisciplineFormStat(BaseModel):
    discipline_form: str
    discipline_form_label: str
    count: int


class DepartmentRewardStat(BaseModel):
    department_id: Optional[int]
    department_name: Optional[str]
    reward_count: int
    discipline_count: int


class RewardDisciplineSummary(BaseModel):
    total_rewards: int
    total_disciplines: int
    total_reward_value: Decimal
    by_reward_type: list[RewardTypeStat]
    by_discipline_form: list[DisciplineFormStat]
    by_department: list[DepartmentRewardStat]


class RewardDisciplineReportPage(BaseModel):
    from_date: date
    to_date: date
    department_id: Optional[int]
    department_name: Optional[str]
    summary: RewardDisciplineSummary
    reward_items: list[RewardRead]
    discipline_items: list[DisciplineRead]
    total_rewards: int
    total_disciplines: int
