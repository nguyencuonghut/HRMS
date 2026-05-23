"""Schemas Pydantic cho module Khen thưởng (8.1)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

# ── Allowed file types ────────────────────────────────────────────────────────
ALLOWED_FILE_EXTS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# ── RewardType ────────────────────────────────────────────────────────────────


class RewardTypeRead(BaseModel):
    id: int
    code: str
    name: str
    is_monetary: bool
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class RewardTypeCreate(BaseModel):
    code: str = Field(max_length=50)
    name: str = Field(max_length=200)
    is_monetary: bool = False
    sort_order: int = 0


class RewardTypeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    is_monetary: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


# ── EmployeeReward ────────────────────────────────────────────────────────────


class RewardRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: Optional[str]
    reward_type_id: int
    reward_type_name: str
    reward_type_is_monetary: bool
    title: str
    description: Optional[str]
    reward_date: date
    decision_number: Optional[str]
    issued_by: Optional[str]
    value: Optional[Decimal]
    note: Optional[str]
    has_file: bool
    file_name: Optional[str]
    file_size: Optional[int]
    created_by_id: Optional[int]
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RewardCreate(BaseModel):
    employee_id: int
    reward_type_id: int
    title: str = Field(max_length=500)
    description: Optional[str] = None
    reward_date: date
    decision_number: Optional[str] = Field(default=None, max_length=100)
    issued_by: Optional[str] = Field(default=None, max_length=200)
    value: Optional[Decimal] = Field(default=None, ge=0)
    note: Optional[str] = None


class RewardUpdate(BaseModel):
    reward_type_id: Optional[int] = None
    title: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None
    reward_date: Optional[date] = None
    decision_number: Optional[str] = Field(default=None, max_length=100)
    issued_by: Optional[str] = Field(default=None, max_length=200)
    value: Optional[Decimal] = Field(default=None, ge=0)
    note: Optional[str] = None


class RewardListPage(BaseModel):
    items: list[RewardRead]
    total: int
    page: int
    page_size: int
