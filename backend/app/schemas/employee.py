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

    # Tên đơn vị hành chính được enrich sau khi query
    old_province_name: Optional[str] = None
    old_district_name: Optional[str] = None
    old_ward_name: Optional[str] = None
    new_province_name: Optional[str] = None
    new_ward_name: Optional[str] = None

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
    employee_code_sequence_id: Optional[int] = None

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
    initial_department_id: Optional[int] = None
    initial_job_title_id: Optional[int] = None
    initial_job_position_id: Optional[int] = None
    initial_job_effective_from: Optional[date] = None
    initial_probation_start_date: Optional[date] = None
    initial_probation_end_date: Optional[date] = None
    initial_official_date: Optional[date] = None
    initial_job_notes: Optional[str] = Field(None, max_length=1000)

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
    # Cảnh báo hết hạn giấy tờ
    id_expires_on: Optional[date] = None
    passport_expires_on: Optional[date] = None
    work_permit_expires_on: Optional[date] = None

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
    nationality_name: Optional[str] = None
    ethnicity_id: Optional[int]
    ethnicity_name: Optional[str] = None
    religion_id: Optional[int]
    religion_name: Optional[str] = None
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
    current_job: Optional["JobRecordRead"] = None
    relatives: list["EmployeeRelativeRead"] = []
    education_histories: list["EducationHistoryRead"] = []
    work_experiences: list["WorkExperienceRead"] = []
    skills: list["EmployeeSkillRead"] = []
    certificates: list["EmployeeCertificateRead"] = []
    languages: list["EmployeeLanguageRead"] = []

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
    current_department_id: Optional[int] = None
    current_department_name: Optional[str] = None
    current_job_position_id: Optional[int] = None
    current_job_position_name: Optional[str] = None
    current_job_title_id: Optional[int] = None
    current_job_title_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Job Records (3.2) ─────────────────────────────────────────────────────────

class DepartmentBrief(BaseModel):
    id: int
    code: str
    name: str
    display_prefix: Optional[str]


class JobTitleBrief(BaseModel):
    id: int
    code: str
    name: str


class JobPositionBrief(BaseModel):
    id: int
    code: str
    name: str


class JobRecordCreate(BaseModel):
    department_id: int
    job_title_id: Optional[int] = None
    job_position_id: Optional[int] = None
    probation_start_date: Optional[date] = None
    probation_end_date: Optional[date] = None
    official_date: Optional[date] = None
    effective_from: date
    notes: Optional[str] = None


class JobRecordUpdate(BaseModel):
    department_id: Optional[int] = None
    job_title_id: Optional[int] = None
    job_position_id: Optional[int] = None
    probation_start_date: Optional[date] = None
    probation_end_date: Optional[date] = None
    official_date: Optional[date] = None
    notes: Optional[str] = None


class JobRecordTransfer(BaseModel):
    department_id: int
    job_title_id: Optional[int] = None
    job_position_id: Optional[int] = None
    effective_from: date
    notes: Optional[str] = None


class JobRecordRead(BaseModel):
    id: int
    employee_id: int
    department_id: int
    department: DepartmentBrief
    job_title_id: Optional[int]
    job_title: Optional[JobTitleBrief]
    job_position_id: Optional[int]
    job_position: Optional[JobPositionBrief]
    probation_start_date: Optional[date]
    probation_end_date: Optional[date]
    official_date: Optional[date]
    effective_from: date
    effective_to: Optional[date]
    is_current: bool
    notes: Optional[str]
    changed_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]


# ── Relatives (3.3) ──────────────────────────────────────────────────────────

RelationshipType = Literal[
    "vo", "chong", "cha", "me", "con", "anh", "chi", "em", "khac"
]


class EmployeeRelativeRead(BaseModel):
    id: int
    employee_id: int
    full_name: str
    relationship_type: str
    date_of_birth: Optional[date]
    occupation: Optional[str]
    phone_number: Optional[str]
    participates_in_health_care_insurance: bool
    is_emergency_contact: bool
    note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RelativeCreate(BaseModel):
    full_name: str
    relationship_type: RelationshipType
    date_of_birth: Optional[date] = None
    occupation: Optional[str] = None
    phone_number: Optional[str] = None
    participates_in_health_care_insurance: bool = False
    is_emergency_contact: bool = False
    note: Optional[str] = None


class RelativeUpdate(BaseModel):
    full_name: Optional[str] = None
    relationship_type: Optional[RelationshipType] = None
    date_of_birth: Optional[date] = None
    occupation: Optional[str] = None
    phone_number: Optional[str] = None
    participates_in_health_care_insurance: Optional[bool] = None
    is_emergency_contact: Optional[bool] = None
    note: Optional[str] = None


# ── Education & Experience (3.4) ─────────────────────────────────────────────

SkillProficiencyLevel = Literal["beginner", "intermediate", "advanced", "expert"]
LanguageProficiencyLevel = Literal["native", "A1", "A2", "B1", "B2", "C1", "C2"]


class EducationHistoryCreate(BaseModel):
    institution_id: int
    major_id: Optional[int] = None
    education_level_id: int
    graduation_year: Optional[int] = None
    diploma_type: Optional[str] = Field(None, max_length=100)
    is_main_education: bool = False
    note: Optional[str] = None


class EducationHistoryUpdate(BaseModel):
    institution_id: Optional[int] = None
    major_id: Optional[int] = None
    education_level_id: Optional[int] = None
    graduation_year: Optional[int] = None
    diploma_type: Optional[str] = Field(None, max_length=100)
    is_main_education: Optional[bool] = None
    note: Optional[str] = None


class EducationHistoryRead(BaseModel):
    id: int
    employee_id: int
    institution_id: Optional[int]
    institution_name: Optional[str]
    major_id: Optional[int]
    major_name: Optional[str]
    education_level_id: int
    education_level_name: str
    graduation_year: Optional[int]
    diploma_type: Optional[str]
    is_main_education: bool
    note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class WorkExperienceCreate(BaseModel):
    company_name: str = Field(..., max_length=255)
    position_name: Optional[str] = Field(None, max_length=255)
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None


class WorkExperienceUpdate(BaseModel):
    company_name: Optional[str] = Field(None, max_length=255)
    position_name: Optional[str] = Field(None, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None


class WorkExperienceRead(BaseModel):
    id: int
    employee_id: int
    company_name: str
    position_name: Optional[str]
    start_date: date
    end_date: Optional[date]
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EmployeeSkillCreate(BaseModel):
    skill_id: int
    proficiency_level: SkillProficiencyLevel
    note: Optional[str] = None


class EmployeeSkillUpdate(BaseModel):
    proficiency_level: Optional[SkillProficiencyLevel] = None
    note: Optional[str] = None


class EmployeeSkillRead(BaseModel):
    id: int
    employee_id: int
    skill_id: int
    skill_name: str
    skill_group: Optional[str]
    proficiency_level: str
    note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EmployeeCertificateCreate(BaseModel):
    certificate_id: int
    certificate_number: Optional[str] = Field(None, max_length=100)
    issued_date: Optional[date] = None
    expires_on: Optional[date] = None
    issued_by: Optional[str] = Field(None, max_length=255)
    note: Optional[str] = None


class EmployeeCertificateUpdate(BaseModel):
    certificate_number: Optional[str] = Field(None, max_length=100)
    issued_date: Optional[date] = None
    expires_on: Optional[date] = None
    issued_by: Optional[str] = Field(None, max_length=255)
    note: Optional[str] = None


class EmployeeCertificateRead(BaseModel):
    id: int
    employee_id: int
    certificate_id: int
    certificate_name: str
    certificate_number: Optional[str]
    issued_date: Optional[date]
    expires_on: Optional[date]
    issued_by: Optional[str]
    note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EmployeeLanguageCreate(BaseModel):
    language_name: str = Field(..., max_length=100)
    proficiency_level: LanguageProficiencyLevel
    note: Optional[str] = None


class EmployeeLanguageUpdate(BaseModel):
    proficiency_level: Optional[LanguageProficiencyLevel] = None
    note: Optional[str] = None


class EmployeeLanguageRead(BaseModel):
    id: int
    employee_id: int
    language_name: str
    proficiency_level: str
    note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# Giải quyết forward references
EmployeeRead.model_rebuild()
