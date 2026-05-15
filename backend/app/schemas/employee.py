from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.services.administrative_import_service import normalize_text

GenderType = Literal["male", "female", "other"]
StatusType = Literal["probation", "official", "long_leave", "resigned"]
AddressType = Literal["permanent", "contact"]


# ── Address ──────────────────────────────────────────────────────────────────

class EmployeeAddressWrite(BaseModel):
    address_type: AddressType
    new_province_unit_id: Optional[int] = None
    new_district_unit_id: Optional[int] = None
    new_ward_unit_id: Optional[int] = None
    new_address_line: Optional[str] = Field(None, max_length=500)
    old_province_unit_id: Optional[int] = None
    old_district_unit_id: Optional[int] = None
    old_ward_unit_id: Optional[int] = None
    old_address_line: Optional[str] = Field(None, max_length=500)
    full_address_text: Optional[str] = Field(None, max_length=1000)


class EmployeeAddressRead(BaseModel):
    id: int
    employee_id: int
    address_type: str
    new_province_unit_id: Optional[int]
    new_district_unit_id: Optional[int]
    new_ward_unit_id: Optional[int]
    new_address_line: Optional[str]
    old_province_unit_id: Optional[int]
    old_district_unit_id: Optional[int]
    old_ward_unit_id: Optional[int]
    old_address_line: Optional[str]
    full_address_text: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Bank Account ──────────────────────────────────────────────────────────────

class EmployeeBankAccountWrite(BaseModel):
    bank_id: int
    account_number: str = Field(..., max_length=50)
    account_name: str = Field(..., max_length=200)
    branch_name: Optional[str] = Field(None, max_length=200)
    is_primary: bool = False
    note: Optional[str] = None

    @field_validator("account_number", "account_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class EmployeeBankAccountRead(BaseModel):
    id: int
    employee_id: int
    bank_id: int
    account_number: str
    account_name: str
    branch_name: Optional[str]
    is_primary: bool
    is_active: bool
    note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Employee Create / Update ──────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    # Nếu truyền employee_seq → dùng khi import; để None → hệ thống tự sinh
    employee_seq: Optional[int] = None

    full_name: str = Field(..., max_length=200)
    last_name: str = Field(..., max_length=100)
    first_name: str = Field(..., max_length=100)

    date_of_birth: date
    gender: GenderType
    nationality_id: int
    ethnicity_id: Optional[int] = None
    religion_id: Optional[int] = None

    id_number: str = Field(..., max_length=20)
    id_issued_on: date
    id_issued_by: str = Field(..., max_length=200)
    id_expires_on: Optional[date] = None

    passport_number: Optional[str] = Field(None, max_length=50)
    passport_issued_on: Optional[date] = None
    passport_expires_on: Optional[date] = None

    work_permit_number: Optional[str] = Field(None, max_length=50)
    work_permit_issued_on: Optional[date] = None
    work_permit_expires_on: Optional[date] = None

    phone_number: Optional[str] = Field(None, max_length=20)
    personal_email: Optional[str] = Field(None, max_length=200)
    personal_tax_code: Optional[str] = Field(None, max_length=20)
    bhxh_code: Optional[str] = Field(None, max_length=20)

    status: StatusType = "probation"
    start_date: date
    resigned_date: Optional[date] = None

    user_id: Optional[int] = None

    @field_validator("full_name", "last_name", "first_name", "id_issued_by")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("id_number")
    @classmethod
    def _strip_id(cls, v: str) -> str:
        return v.strip()


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=200)
    last_name: Optional[str] = Field(None, max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)

    date_of_birth: Optional[date] = None
    gender: Optional[GenderType] = None
    nationality_id: Optional[int] = None
    ethnicity_id: Optional[int] = None
    religion_id: Optional[int] = None

    id_number: Optional[str] = Field(None, max_length=20)
    id_issued_on: Optional[date] = None
    id_issued_by: Optional[str] = Field(None, max_length=200)
    id_expires_on: Optional[date] = None

    passport_number: Optional[str] = Field(None, max_length=50)
    passport_issued_on: Optional[date] = None
    passport_expires_on: Optional[date] = None

    work_permit_number: Optional[str] = Field(None, max_length=50)
    work_permit_issued_on: Optional[date] = None
    work_permit_expires_on: Optional[date] = None

    phone_number: Optional[str] = Field(None, max_length=20)
    personal_email: Optional[str] = Field(None, max_length=200)
    personal_tax_code: Optional[str] = Field(None, max_length=20)
    bhxh_code: Optional[str] = Field(None, max_length=20)

    avatar_path: Optional[str] = Field(None, max_length=500)

    status: Optional[StatusType] = None
    start_date: Optional[date] = None
    resigned_date: Optional[date] = None

    user_id: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("full_name", "last_name", "first_name", "id_issued_by")
    @classmethod
    def _strip(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


# ── Read schemas ──────────────────────────────────────────────────────────────

class EmployeeListItem(BaseModel):
    """Dùng cho danh sách — không kèm sub-resources."""
    id: int
    employee_seq: int
    display_code: str
    full_name: str
    date_of_birth: date
    gender: str
    nationality_id: int
    ethnicity_id: Optional[int]
    id_number: str
    phone_number: Optional[str]
    personal_email: Optional[str]
    status: str
    start_date: date
    resigned_date: Optional[date]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EmployeeRead(BaseModel):
    """Chi tiết đầy đủ — kèm addresses và bank_accounts."""
    id: int
    employee_seq: int
    display_code: str
    full_name: str
    last_name: str
    first_name: str
    date_of_birth: date
    gender: str
    nationality_id: int
    ethnicity_id: Optional[int]
    religion_id: Optional[int]
    id_number: str
    id_issued_on: date
    id_issued_by: str
    id_expires_on: Optional[date]
    passport_number: Optional[str]
    passport_issued_on: Optional[date]
    passport_expires_on: Optional[date]
    work_permit_number: Optional[str]
    work_permit_issued_on: Optional[date]
    work_permit_expires_on: Optional[date]
    phone_number: Optional[str]
    personal_email: Optional[str]
    personal_tax_code: Optional[str]
    bhxh_code: Optional[str]
    avatar_path: Optional[str]
    status: str
    start_date: date
    resigned_date: Optional[date]
    user_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    addresses: list[EmployeeAddressRead] = []
    bank_accounts: list[EmployeeBankAccountRead] = []

    model_config = {"from_attributes": True}


class EmployeeListPage(BaseModel):
    items: list[EmployeeListItem]
    total: int
    page: int
    page_size: int


# ── Lookup ────────────────────────────────────────────────────────────────────

class EmployeeLookupItem(BaseModel):
    id: int
    employee_seq: int
    display_code: str
    full_name: str
    status: str

    model_config = {"from_attributes": True}
