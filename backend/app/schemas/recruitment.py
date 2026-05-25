"""Schemas tuyển dụng ATS (13.1 — Kế hoạch & Yêu cầu tuyển dụng / 13.2 — Đăng tin / 13.3 — Ứng viên)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

JRReasonType = Literal["new", "replacement", "expansion"]
JRReasonLabels: dict[str, str] = {
    "new":         "Vị trí mới",
    "replacement": "Thay thế nhân sự",
    "expansion":   "Mở rộng",
}

JRStatus = Literal["draft", "pending_review", "approved", "in_progress", "completed", "cancelled"]
JRStatusLabels: dict[str, str] = {
    "draft":          "Nháp",
    "pending_review": "Chờ duyệt",
    "approved":       "Đã duyệt",
    "in_progress":    "Đang tuyển",
    "completed":      "Hoàn thành",
    "cancelled":      "Đã hủy",
}


# ── Headcount Plan ────────────────────────────────────────────────────────────


class HeadcountPlanCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    department_id: Optional[int] = None
    job_position_id: Optional[int] = None
    current_count: int = Field(default=0, ge=0)
    planned_count: int = Field(ge=1)
    reason: Optional[str] = None


class HeadcountPlanUpdate(BaseModel):
    current_count: Optional[int] = Field(default=None, ge=0)
    planned_count: Optional[int] = Field(default=None, ge=1)
    reason: Optional[str] = None


class HeadcountPlanRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    year: int
    department_id: Optional[int]
    department_name: Optional[str]
    job_position_id: Optional[int]
    job_position_name: Optional[str]
    current_count: int
    planned_count: int
    reason: Optional[str]
    created_by_id: Optional[int]
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime


class HeadcountPlanListPage(BaseModel):
    items: list[HeadcountPlanRead]
    total: int
    page: int
    page_size: int


# ── Job Requisition ───────────────────────────────────────────────────────────


class JobRequisitionCreate(BaseModel):
    job_position_id: int
    department_id: int
    headcount_plan_id: Optional[int] = None
    quantity: int = Field(default=1, ge=1, le=100)
    reason_type: JRReasonType
    deadline: Optional[date] = None
    salary_min: Optional[Decimal] = Field(default=None, ge=0)
    salary_max: Optional[Decimal] = Field(default=None, ge=0)
    jd_description: Optional[str] = None
    jd_requirements: Optional[str] = None
    internal_note: Optional[str] = None

    @model_validator(mode="after")
    def validate_salary_range(self) -> "JobRequisitionCreate":
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("salary_min không được lớn hơn salary_max")
        return self


class JobRequisitionUpdate(BaseModel):
    department_id: Optional[int] = None
    headcount_plan_id: Optional[int] = None
    quantity: Optional[int] = Field(default=None, ge=1, le=100)
    reason_type: Optional[JRReasonType] = None
    deadline: Optional[date] = None
    salary_min: Optional[Decimal] = Field(default=None, ge=0)
    salary_max: Optional[Decimal] = Field(default=None, ge=0)
    jd_description: Optional[str] = None
    jd_requirements: Optional[str] = None
    internal_note: Optional[str] = None


class JobRequisitionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    code: str
    job_position_id: int
    job_position_name: str
    department_id: int
    department_name: str
    headcount_plan_id: Optional[int]
    quantity: int
    quantity_remaining: int
    reason_type: str
    reason_type_label: str
    deadline: Optional[date]
    salary_min: Optional[Decimal]
    salary_max: Optional[Decimal]
    # JD đã merge: dùng override nếu có, fallback về job_position
    effective_description: Optional[str]
    effective_requirements: Optional[str]
    status: str
    status_label: str
    submitted_at: Optional[datetime]
    submitted_by_name: Optional[str]
    approved_by_id: Optional[int]
    approved_by_name: Optional[str]
    approved_at: Optional[datetime]
    rejection_note: Optional[str]
    internal_note: Optional[str]
    created_by_id: int
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime


class JobRequisitionListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    code: str
    job_position_name: str
    department_name: str
    quantity: int
    quantity_remaining: int
    reason_type: str
    reason_type_label: str
    deadline: Optional[date]
    status: str
    status_label: str
    created_at: datetime


class JobRequisitionListPage(BaseModel):
    items: list[JobRequisitionListItem]
    total: int
    page: int
    page_size: int


class RejectRequest(BaseModel):
    rejection_note: str = Field(min_length=1)


class CancelRequest(BaseModel):
    reason: Optional[str] = None


# ── Budget ────────────────────────────────────────────────────────────────────


class BudgetItemCreate(BaseModel):
    item_name: str = Field(min_length=1, max_length=200)
    estimated_amount: Optional[Decimal] = Field(default=None, ge=0)
    actual_amount: Optional[Decimal] = Field(default=None, ge=0)
    note: Optional[str] = None


class BudgetItemUpdate(BaseModel):
    item_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    estimated_amount: Optional[Decimal] = Field(default=None, ge=0)
    actual_amount: Optional[Decimal] = Field(default=None, ge=0)
    note: Optional[str] = None


class BudgetItemRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    job_requisition_id: int
    item_name: str
    estimated_amount: Optional[Decimal]
    actual_amount: Optional[Decimal]
    note: Optional[str]
    created_by_id: Optional[int]
    created_at: datetime


class BudgetSummary(BaseModel):
    items: list[BudgetItemRead]
    total_estimated: Decimal
    total_actual: Decimal


# ── Recruitment Channel (13.2) ────────────────────────────────────────────────


class RecruitmentChannelCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    sort_order: int = Field(default=0, ge=0)


class RecruitmentChannelUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(default=None, ge=0)


class RecruitmentChannelRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    code: str
    name: str
    is_active: bool
    sort_order: int


# ── Job Posting (13.2) ────────────────────────────────────────────────────────

PostingStatus = Literal["draft", "active", "closed", "expired"]
PostingStatusLabels: dict[str, str] = {
    "draft":   "Nháp",
    "active":  "Đang tuyển",
    "closed":  "Đã đóng",
    "expired": "Hết hạn",
}

PostingType = Literal["internal", "external"]
PostingTypeLabels: dict[str, str] = {
    "internal": "Nội bộ",
    "external": "Bên ngoài",
}

IdentityStrength = Literal["weak", "medium", "strong"]
IdentityStrengthLabels: dict[str, str] = {
    "weak": "Định danh yếu",
    "medium": "Định danh trung bình",
    "strong": "Định danh mạnh",
}


class JobPostingCreate(BaseModel):
    job_requisition_id: int
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    work_location: Optional[str] = Field(default=None, max_length=300)
    deadline: Optional[date] = None
    salary_display: Optional[str] = Field(default=None, max_length=100)
    posting_type: PostingType = "external"
    channels: List[int] = Field(default_factory=list)
    note: Optional[str] = None


class JobPostingUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, min_length=1)
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    work_location: Optional[str] = Field(default=None, max_length=300)
    deadline: Optional[date] = None
    salary_display: Optional[str] = Field(default=None, max_length=100)
    posting_type: Optional[PostingType] = None
    channels: Optional[List[int]] = None
    note: Optional[str] = None


class JobPostingRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    job_requisition_id: int
    job_requisition_code: str
    job_position_name: str
    department_name: str
    title: str
    description: str
    requirements: Optional[str]
    benefits: Optional[str]
    work_location: Optional[str]
    deadline: Optional[date]
    salary_display: Optional[str]
    posting_type: str
    posting_type_label: str
    channels: List[RecruitmentChannelRead]
    status: str
    status_label: str
    opened_at: Optional[datetime]
    closed_at: Optional[datetime]
    candidate_count: int
    note: Optional[str]
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime


class JobPostingListPage(BaseModel):
    items: List[JobPostingRead]
    total: int
    page: int
    page_size: int


class LanguageValidationRequest(BaseModel):
    text: str


class LanguageValidationResult(BaseModel):
    warnings: List[str]


# ── Candidates (13.3) ─────────────────────────────────────────────────────────

CandidateGender = Literal["male", "female", "other"]
CandidateGenderLabels: dict[str, str] = {"male": "Nam", "female": "Nữ", "other": "Khác"}

AttachmentType = Literal["cv", "degree", "id_card", "photo", "other"]
AttachmentTypeLabels: dict[str, str] = {
    "cv": "CV / Hồ sơ",
    "degree": "Bằng cấp / Chứng chỉ",
    "id_card": "CCCD / Hộ chiếu",
    "photo": "Ảnh",
    "other": "Khác",
}

ProficiencyLevel = Literal["beginner", "intermediate", "advanced", "expert"]
ApplicationStage = Literal["new", "screening", "test", "interview", "offer", "hired", "rejected", "withdrawn"]


class CandidateEducationCreate(BaseModel):
    education_level_id: Optional[int] = None
    institution_name: Optional[str] = Field(default=None, max_length=300)
    major_name: Optional[str] = Field(default=None, max_length=300)
    graduation_year: Optional[int] = Field(default=None, ge=1950, le=2100)
    is_main: bool = False
    note: Optional[str] = None


class CandidateEducationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    candidate_id: int
    education_level_id: Optional[int]
    education_level_name: Optional[str]
    institution_name: Optional[str]
    major_name: Optional[str]
    graduation_year: Optional[int]
    is_main: bool
    note: Optional[str]


class CandidateWorkExpCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=300)
    position_name: Optional[str] = Field(default=None, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    sort_order: int = 0


class CandidateWorkExpRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    candidate_id: int
    company_name: str
    position_name: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    description: Optional[str]
    sort_order: int


class CandidateSkillCreate(BaseModel):
    skill_name: str = Field(min_length=1, max_length=200)
    proficiency_level: Optional[ProficiencyLevel] = None


class CandidateSkillRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    candidate_id: int
    skill_name: str
    proficiency_level: Optional[str]


class CandidateAttachmentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    candidate_id: int
    attachment_type: str
    attachment_type_label: str
    file_name: str
    file_size: Optional[int]
    mime_type: Optional[str]
    note: Optional[str]
    uploaded_at: datetime
    download_url: str


class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    last_name: Optional[str] = Field(default=None, max_length=100)
    first_name: Optional[str] = Field(default=None, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[CandidateGender] = None
    nationality_id: Optional[int] = None
    raw_nationality_text: Optional[str] = Field(
        default=None,
        max_length=100,
        validation_alias=AliasChoices("raw_nationality_text", "nationality"),
    )
    ethnicity_id: Optional[int] = None
    religion_id: Optional[int] = None
    id_number: Optional[str] = Field(default=None, max_length=30)
    id_issued_on: Optional[date] = None
    id_issued_by: Optional[str] = Field(default=None, max_length=200)
    id_expires_on: Optional[date] = None
    passport_number: Optional[str] = Field(default=None, max_length=50)
    passport_issued_on: Optional[date] = None
    passport_expires_on: Optional[date] = None
    work_permit_number: Optional[str] = Field(default=None, max_length=50)
    work_permit_issued_on: Optional[date] = None
    work_permit_expires_on: Optional[date] = None
    phone_number: Optional[str] = Field(
        default=None,
        max_length=20,
        validation_alias=AliasChoices("phone_number", "phone"),
    )
    personal_email: Optional[str] = Field(
        default=None,
        max_length=200,
        validation_alias=AliasChoices("personal_email", "email"),
    )
    personal_tax_code: Optional[str] = Field(default=None, max_length=20)
    bhxh_code: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = None
    current_company: Optional[str] = Field(default=None, max_length=200)
    current_position: Optional[str] = Field(default=None, max_length=200)
    expected_salary: Optional[Decimal] = None
    source_channel_id: Optional[int] = None
    source_note: Optional[str] = None
    internal_note: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    @field_validator(
        "full_name",
        "last_name",
        "first_name",
        "raw_nationality_text",
        "id_number",
        "id_issued_by",
        "passport_number",
        "work_permit_number",
        "phone_number",
        "personal_email",
        "personal_tax_code",
        "bhxh_code",
        "current_company",
        "current_position",
        "source_note",
        "internal_note",
        mode="before",
    )
    @classmethod
    def strip_string_fields(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_identity_anchor(self) -> "CandidateCreate":
        if any((self.personal_email, self.phone_number, self.id_number, self.passport_number)):
            return self
        raise ValueError(
            "Cần nhập ít nhất một thông tin định danh: email cá nhân, số điện thoại, CCCD/CMND hoặc hộ chiếu"
        )


class CandidateUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    last_name: Optional[str] = Field(default=None, max_length=100)
    first_name: Optional[str] = Field(default=None, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[CandidateGender] = None
    nationality_id: Optional[int] = None
    raw_nationality_text: Optional[str] = Field(
        default=None,
        max_length=100,
        validation_alias=AliasChoices("raw_nationality_text", "nationality"),
    )
    ethnicity_id: Optional[int] = None
    religion_id: Optional[int] = None
    id_number: Optional[str] = Field(default=None, max_length=30)
    id_issued_on: Optional[date] = None
    id_issued_by: Optional[str] = Field(default=None, max_length=200)
    id_expires_on: Optional[date] = None
    passport_number: Optional[str] = Field(default=None, max_length=50)
    passport_issued_on: Optional[date] = None
    passport_expires_on: Optional[date] = None
    work_permit_number: Optional[str] = Field(default=None, max_length=50)
    work_permit_issued_on: Optional[date] = None
    work_permit_expires_on: Optional[date] = None
    phone_number: Optional[str] = Field(
        default=None,
        max_length=20,
        validation_alias=AliasChoices("phone_number", "phone"),
    )
    personal_email: Optional[str] = Field(
        default=None,
        max_length=200,
        validation_alias=AliasChoices("personal_email", "email"),
    )
    personal_tax_code: Optional[str] = Field(default=None, max_length=20)
    bhxh_code: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = None
    current_company: Optional[str] = Field(default=None, max_length=200)
    current_position: Optional[str] = Field(default=None, max_length=200)
    expected_salary: Optional[Decimal] = None
    source_channel_id: Optional[int] = None
    source_note: Optional[str] = None
    internal_note: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator(
        "full_name",
        "last_name",
        "first_name",
        "raw_nationality_text",
        "id_number",
        "id_issued_by",
        "passport_number",
        "work_permit_number",
        "phone_number",
        "personal_email",
        "personal_tax_code",
        "bhxh_code",
        "current_company",
        "current_position",
        "source_note",
        "internal_note",
        mode="before",
    )
    @classmethod
    def strip_string_fields(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CandidateRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    full_name: str
    last_name: Optional[str]
    first_name: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[str]
    gender_label: Optional[str]
    nationality_id: Optional[int]
    nationality_name: Optional[str]
    raw_nationality_text: Optional[str]
    ethnicity_id: Optional[int]
    ethnicity_name: Optional[str]
    religion_id: Optional[int]
    religion_name: Optional[str]
    id_number: Optional[str]
    id_issued_on: Optional[date]
    id_issued_by: Optional[str]
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
    address: Optional[str]
    current_company: Optional[str]
    current_position: Optional[str]
    expected_salary: Optional[Decimal]
    source_channel_id: Optional[int]
    source_channel_name: Optional[str]
    source_note: Optional[str]
    internal_note: Optional[str]
    tags: List[str]
    is_active: bool
    educations: List[CandidateEducationRead]
    work_experiences: List[CandidateWorkExpRead]
    skills: List[CandidateSkillRead]
    attachments: List[CandidateAttachmentRead]
    active_applications: int
    identity_strength: IdentityStrength
    identity_strength_label: str
    conversion_ready: bool
    conversion_missing_fields: List[str]
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime


class CandidateListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    full_name: str
    phone_number: Optional[str]
    personal_email: Optional[str]
    current_position: Optional[str]
    current_company: Optional[str]
    nationality_name: Optional[str]
    source_channel_name: Optional[str]
    active_applications: int
    identity_strength: IdentityStrength
    identity_strength_label: str
    created_at: datetime


class CandidateListPage(BaseModel):
    items: List[CandidateListItem]
    total: int
    page: int
    page_size: int


DuplicateMatchLevel = Literal["exact", "possible"]
CandidateDuplicateReasonLabels: dict[str, str] = {
    "same_id_number": "Trùng số CCCD / CMND",
    "same_passport_number": "Trùng số hộ chiếu",
    "same_personal_email": "Trùng email cá nhân",
    "same_phone_number": "Trùng số điện thoại",
    "same_full_name_and_date_of_birth": "Trùng họ tên và ngày sinh",
    "same_full_name": "Trùng họ tên",
}


class CandidateDuplicateCheck(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    date_of_birth: Optional[date] = None
    id_number: Optional[str] = Field(default=None, max_length=30)
    passport_number: Optional[str] = Field(default=None, max_length=50)
    phone_number: Optional[str] = Field(
        default=None,
        max_length=20,
        validation_alias=AliasChoices("phone_number", "phone"),
    )
    personal_email: Optional[str] = Field(
        default=None,
        max_length=200,
        validation_alias=AliasChoices("personal_email", "email"),
    )
    exclude_candidate_id: Optional[int] = None

    @field_validator(
        "full_name",
        "id_number",
        "passport_number",
        "phone_number",
        "personal_email",
        mode="before",
    )
    @classmethod
    def strip_duplicate_check_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CandidateDuplicateMatch(BaseModel):
    candidate_id: int
    full_name: str
    date_of_birth: Optional[date]
    id_number: Optional[str]
    passport_number: Optional[str]
    phone_number: Optional[str]
    personal_email: Optional[str]
    current_company: Optional[str]
    current_position: Optional[str]
    match_level: DuplicateMatchLevel
    reason_codes: List[str]
    reason_labels: List[str]


class CandidateDuplicateCheckResult(BaseModel):
    exact_matches: List[CandidateDuplicateMatch]
    possible_matches: List[CandidateDuplicateMatch]


class ApplicationCreate(BaseModel):
    job_requisition_id: int
    applied_date: date = Field(default_factory=date.today)
    source_channel_id: Optional[int] = None
    internal_note: Optional[str] = None


class ApplicationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    candidate_id: int
    candidate_name: str
    job_requisition_id: int
    job_requisition_code: str
    job_position_name: str
    department_name: str
    applied_date: date
    source_channel_name: Optional[str]
    current_stage: str
    rejection_reason: Optional[str]
    internal_note: Optional[str]
    created_at: datetime
    updated_at: datetime


class ApplicationListPage(BaseModel):
    items: List[ApplicationRead]
    total: int
    page: int
    page_size: int


class ImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: List[str]
