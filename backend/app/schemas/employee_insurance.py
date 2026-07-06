from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class InsuranceContributionComponentSnapshot(BaseModel):
    component_code: str
    component_name: str
    insurance_kind: str
    sort_order: int
    calc_mode: str  # company_policy | fixed_amount
    employee_rate_percent: Optional[Decimal]
    employer_rate_percent: Optional[Decimal]
    fixed_employee_amount: Optional[Decimal]
    fixed_employer_amount: Optional[Decimal]
    employer_advances_employee_part: bool
    employee_amount: Optional[Decimal]
    employer_amount: Optional[Decimal]


class EmployeeInsuranceListItem(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: Optional[str]
    job_title_name: Optional[str]

    bhxh_code: Optional[str]
    health_care_insurance_code: Optional[str]
    health_care_family_participation: Optional[bool]
    accident_insurance_code: Optional[str]
    bhyt_initial_clinic_name: Optional[str]
    bhyt_initial_clinic_code: Optional[str] = None
    company_bhxh_joined_date: Optional[date]
    participation_status: str

    insurance_basis_amount: Optional[Decimal]
    insurance_basis_source: str
    policy_version_id: Optional[int]
    policy_version_name: Optional[str]
    effective_regulation_code: Optional[str]
    company_region: Optional[int]
    has_component_overrides: bool
    employer_pays_on_behalf: bool

    contract_id: Optional[int]
    contract_number: Optional[str]
    insurance_salary_grade_no: Optional[int] = None
    contributions: list[InsuranceContributionComponentSnapshot] = []


class EmployeeInsuranceListPage(BaseModel):
    items: list[EmployeeInsuranceListItem]
    total: int
    page: int
    page_size: int


class EmployeeInsuranceComponentOverrideInput(BaseModel):
    component_code: str
    use_company_default: bool = True
    fixed_employee_amount: Optional[Decimal] = Field(None, ge=0)
    fixed_employer_amount: Optional[Decimal] = Field(None, ge=0)
    employer_advances_employee_part: Optional[bool] = None

    @model_validator(mode="after")
    def _validate_fixed_vs_default(self) -> "EmployeeInsuranceComponentOverrideInput":
        if self.use_company_default:
            if self.fixed_employee_amount is not None or self.fixed_employer_amount is not None:
                raise ValueError("use_company_default=True thì không được nhập fixed amounts")
        else:
            if self.fixed_employee_amount is None and self.fixed_employer_amount is None:
                raise ValueError("use_company_default=False thì phải nhập ít nhất một fixed amount")
        return self


class EmployeeInsuranceProfileBase(BaseModel):
    bhxh_code: Optional[str] = Field(None, max_length=20)
    health_care_insurance_code: Optional[str] = Field(None, max_length=50)
    health_care_family_participation: Optional[bool] = None
    accident_insurance_code: Optional[str] = Field(None, max_length=50)
    bhyt_initial_clinic_name: Optional[str] = Field(None, max_length=255)
    bhyt_initial_clinic_code: Optional[str] = Field(None, max_length=20)
    company_bhxh_joined_date: Optional[date] = None
    participation_status: Literal["active", "paused", "stopped"] = "active"
    status_effective_from: Optional[date] = None
    status_note: Optional[str] = Field(None, max_length=2000)
    insurance_basis_source: Literal["contract", "computed", "manual_fixed"] = "contract"
    insurance_basis_amount: Optional[Decimal] = None

    @model_validator(mode="after")
    def _validate_stopped_status(self) -> "EmployeeInsuranceProfileBase":
        if self.participation_status == "stopped" and self.status_effective_from is None:
            raise ValueError("status_effective_from bắt buộc khi participation_status = stopped")
        if self.insurance_basis_source == "manual_fixed" and self.insurance_basis_amount is None:
            raise ValueError("insurance_basis_amount bắt buộc khi insurance_basis_source = manual_fixed")
        return self


class EmployeeInsuranceProfileUpdate(EmployeeInsuranceProfileBase):
    component_overrides: list[EmployeeInsuranceComponentOverrideInput] = []


class EmployeeInsuranceProfileRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: Optional[str]
    job_title_name: Optional[str]

    bhxh_code: Optional[str]
    health_care_insurance_code: Optional[str]
    health_care_family_participation: Optional[bool]
    accident_insurance_code: Optional[str]
    bhyt_initial_clinic_name: Optional[str]
    bhyt_initial_clinic_code: Optional[str]
    company_bhxh_joined_date: Optional[date]
    participation_status: str
    status_effective_from: Optional[date]
    status_note: Optional[str]

    insurance_basis_source: str
    insurance_basis_amount: Optional[Decimal]
    policy_version_id: Optional[int]
    policy_version_name: Optional[str]
    effective_regulation_code: Optional[str]
    company_region: Optional[int]
    has_component_overrides: bool
    employer_pays_on_behalf: bool

    contract_id: Optional[int]
    contract_number: Optional[str]
    insurance_salary_grade_no: Optional[int] = None
    contributions: list[InsuranceContributionComponentSnapshot] = []

    created_at: datetime
    updated_at: Optional[datetime]
