from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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


class RegionalMinimumWageRead(BaseModel):
    id: int
    decree_number: str
    region: int
    amount: int
    effective_from: date
    effective_to: Optional[date]
    note: Optional[str]


class RegionalMinimumWageCreate(BaseModel):
    decree_number: str = Field(..., max_length=50)
    region: int = Field(..., ge=1, le=4)
    amount: int = Field(..., gt=0)
    effective_from: date
    note: Optional[str] = Field(None, max_length=2000)

    @field_validator("decree_number")
    @classmethod
    def _strip_decree_number(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Số hiệu nghị định không được để trống")
        return stripped


class RegionalMinimumWageUpdate(BaseModel):
    decree_number: Optional[str] = Field(None, max_length=50)
    amount: Optional[int] = Field(None, gt=0)
    note: Optional[str] = Field(None, max_length=2000)

    @field_validator("decree_number")
    @classmethod
    def _strip_optional_decree_number(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Số hiệu nghị định không được để trống")
        return stripped


class BhxhSenioritySettingRead(BaseModel):
    id: int
    raise_month: int
    raise_day: int
    years_per_grade: int
    first_year_cutoff_month: int
    first_year_cutoff_day: int
    effective_from: date
    effective_to: Optional[date]
    note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class BhxhSenioritySettingCreate(BaseModel):
    raise_month: int = Field(..., ge=1, le=12)
    raise_day: int = Field(..., ge=1, le=31)
    years_per_grade: int = Field(..., ge=1)
    first_year_cutoff_month: int = Field(..., ge=1, le=12)
    first_year_cutoff_day: int = Field(..., ge=1, le=31)
    effective_from: date
    note: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _validate_dates(self) -> "BhxhSenioritySettingCreate":
        date(2000, self.raise_month, self.raise_day)
        date(2000, self.first_year_cutoff_month, self.first_year_cutoff_day)
        return self


class BhxhSenioritySettingUpdate(BaseModel):
    raise_month: Optional[int] = Field(None, ge=1, le=12)
    raise_day: Optional[int] = Field(None, ge=1, le=31)
    years_per_grade: Optional[int] = Field(None, ge=1)
    first_year_cutoff_month: Optional[int] = Field(None, ge=1, le=12)
    first_year_cutoff_day: Optional[int] = Field(None, ge=1, le=31)
    note: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _validate_dates(self) -> "BhxhSenioritySettingUpdate":
        raise_month = self.raise_month if self.raise_month is not None else 1
        raise_day = self.raise_day if self.raise_day is not None else 1
        cutoff_month = self.first_year_cutoff_month if self.first_year_cutoff_month is not None else 1
        cutoff_day = self.first_year_cutoff_day if self.first_year_cutoff_day is not None else 1
        date(2000, raise_month, raise_day)
        date(2000, cutoff_month, cutoff_day)
        return self


class BhxhSenioritySettingsRead(BaseModel):
    current: Optional[BhxhSenioritySettingRead]
    history: list[BhxhSenioritySettingRead]


class SalaryScaleSummaryRead(BaseModel):
    id: int
    name: str
    effective_from: date
    effective_to: Optional[date]
    note: Optional[str]


class BhxhPositionGroupCoefficientRead(BaseModel):
    grade_no: int
    coefficient: Decimal
    promotion_months: int
    criteria: Optional[str]


class BhxhPositionGroupCoefficientInput(BaseModel):
    grade_no: int = Field(..., ge=1, le=7)
    coefficient: Decimal = Field(..., gt=0)
    promotion_months: int = Field(12, ge=1)
    criteria: Optional[str] = Field(None, max_length=2000)


class BhxhPositionGroupMemberRead(BaseModel):
    job_position_id: int
    job_position_code: str
    job_position_name: str
    department_name: Optional[str]


class BhxhPositionGroupRead(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    is_active: bool
    coefficients: list[BhxhPositionGroupCoefficientRead]
    members: list[BhxhPositionGroupMemberRead]
    created_at: datetime
    updated_at: Optional[datetime]


class BhxhPositionGroupCatalogRead(BaseModel):
    current_scale: Optional[SalaryScaleSummaryRead]
    groups: list[BhxhPositionGroupRead]


class BhxhPositionGroupCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    is_active: bool = True
    position_ids: list[int] = Field(default_factory=list)
    coefficients: list[BhxhPositionGroupCoefficientInput]

    @field_validator("code", "name")
    @classmethod
    def _strip_required_group_fields(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Trường bắt buộc không được để trống")
        return stripped

    @field_validator("position_ids")
    @classmethod
    def _dedupe_position_ids(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def _validate_coefficients(self) -> "BhxhPositionGroupCreate":
        grades = sorted(item.grade_no for item in self.coefficients)
        if grades != [1, 2, 3, 4, 5, 6, 7]:
            raise ValueError("Phải cấu hình đủ 7 bậc hệ số từ 1 đến 7")
        return self


class BhxhPositionGroupUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    is_active: Optional[bool] = None
    position_ids: Optional[list[int]] = None
    coefficients: Optional[list[BhxhPositionGroupCoefficientInput]] = None

    @field_validator("code", "name")
    @classmethod
    def _strip_optional_group_fields(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Trường bắt buộc không được để trống")
        return stripped

    @field_validator("position_ids")
    @classmethod
    def _dedupe_optional_position_ids(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        if value is None:
            return value
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def _validate_optional_coefficients(self) -> "BhxhPositionGroupUpdate":
        if self.coefficients is None:
            return self
        grades = sorted(item.grade_no for item in self.coefficients)
        if grades != [1, 2, 3, 4, 5, 6, 7]:
            raise ValueError("Phải cấu hình đủ 7 bậc hệ số từ 1 đến 7")
        return self


class InsuranceEffectiveContributionConfigRead(BaseModel):
    as_of_date: date
    company_region: CompanyRegionHistoryItem
    policy_version: InsurancePolicyVersionRead
