from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class InsuranceContributionComponentRead(BaseModel):
    code: str
    name_vi: str
    insurance_kind: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class InsurancePolicyComponentRateInput(BaseModel):
    component_code: str
    employee_rate_percent: Decimal = Field(..., ge=0)
    employer_rate_percent: Decimal = Field(..., ge=0)
    employer_advances_employee_part: bool = False


class InsurancePolicyComponentRateRead(InsurancePolicyComponentRateInput):
    id: int
    component_name: str
    insurance_kind: str
    sort_order: int
    is_active: bool


class InsurancePolicyVersionCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    legal_basis_summary: Optional[str] = None
    effective_from: date
    company_region: int = Field(..., ge=1, le=4)
    note: Optional[str] = None
    components: list[InsurancePolicyComponentRateInput]

    @field_validator("code", "name")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Trường bắt buộc không được để trống")
        return stripped


class InsurancePolicyVersionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    legal_basis_summary: Optional[str] = None
    effective_from: Optional[date] = None
    company_region: Optional[int] = Field(None, ge=1, le=4)
    note: Optional[str] = None
    components: Optional[list[InsurancePolicyComponentRateInput]] = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Tên policy không được để trống")
        return stripped


class InsurancePolicyVersionRead(BaseModel):
    id: int
    code: str
    name: str
    legal_basis_summary: Optional[str]
    effective_from: date
    effective_to: Optional[date]
    is_active: bool
    company_region: int
    note: Optional[str]
    components: list[InsurancePolicyComponentRateRead]
    created_at: datetime
    updated_at: Optional[datetime]


class CompanyRegionHistoryItem(BaseModel):
    id: int
    region: int
    effective_from: date
    effective_to: Optional[date]
    note: Optional[str]


class CompanyRegionRead(BaseModel):
    current: Optional[CompanyRegionHistoryItem]
    history: list[CompanyRegionHistoryItem]


class CompanyRegionUpsert(BaseModel):
    region: int = Field(..., ge=1, le=4)
    effective_from: date
    note: Optional[str] = Field(None, max_length=1000)
