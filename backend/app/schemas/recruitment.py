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
PipelineStageType = Literal["screening", "test", "interview", "final"]
StageResultValue = Literal["pass", "fail", "hold", "pending"]
InterviewFormat = Literal["in_person", "online", "phone"]
InterviewSessionStatus = Literal["scheduled", "completed", "cancelled", "rescheduled"]
QuestionDifficulty = Literal["easy", "medium", "hard"]


class CandidateEducationCreate(BaseModel):
    institution_id: int
    major_id: Optional[int] = None
    education_level_id: int
    graduation_year: Optional[int] = Field(default=None, ge=1950, le=2100)
    diploma_type: Optional[str] = Field(default=None, max_length=100)
    is_main_education: bool = False
    note: Optional[str] = None


class CandidateEducationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    candidate_id: int
    institution_id: Optional[int]
    institution_name: Optional[str]
    major_id: Optional[int]
    major_name: Optional[str]
    education_level_id: Optional[int]
    education_level_name: Optional[str]
    graduation_year: Optional[int]
    diploma_type: Optional[str]
    is_main_education: bool
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
    skill_id: int
    proficiency_level: Optional[ProficiencyLevel] = None
    note: Optional[str] = None


class CandidateSkillRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    candidate_id: int
    skill_id: Optional[int]
    skill_name: str
    skill_group: Optional[str]
    proficiency_level: Optional[str]
    note: Optional[str]


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


class PipelineStageTemplateItemInput(BaseModel):
    stage_order: int = Field(ge=1, le=50)
    stage_name: str = Field(min_length=1, max_length=100)
    stage_type: PipelineStageType
    is_required: bool = True


class PipelineStageTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    job_position_id: Optional[int] = None
    is_default: bool = False
    items: List[PipelineStageTemplateItemInput] = Field(min_length=1)


class PipelineStageTemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    job_position_id: Optional[int] = None
    is_default: Optional[bool] = None
    items: Optional[List[PipelineStageTemplateItemInput]] = None


class PipelineStageTemplateItemRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    template_id: int
    stage_order: int
    stage_name: str
    stage_type: str
    is_required: bool


class PipelineStageTemplateRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    job_position_id: Optional[int]
    is_default: bool
    items: List[PipelineStageTemplateItemRead]
    created_at: datetime


class PipelineStageCreate(BaseModel):
    stage_order: int = Field(ge=1, le=50)
    stage_name: str = Field(min_length=1, max_length=100)
    stage_type: PipelineStageType
    is_active: bool = True


class PipelineStageUpdate(BaseModel):
    stage_order: Optional[int] = Field(default=None, ge=1, le=50)
    stage_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    stage_type: Optional[PipelineStageType] = None
    is_active: Optional[bool] = None


class PipelineSetupRequest(BaseModel):
    template_id: Optional[int] = None
    stages: Optional[List[PipelineStageCreate]] = None

    @model_validator(mode="after")
    def validate_source(self) -> "PipelineSetupRequest":
        has_template = self.template_id is not None
        has_stages = bool(self.stages)
        if has_template == has_stages:
            raise ValueError("Cần truyền đúng một trong hai: template_id hoặc stages")
        return self


class PipelineStageRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    job_requisition_id: int
    stage_order: int
    stage_name: str
    stage_type: str
    is_active: bool
    application_count: int


class AdvanceApplicationRequest(BaseModel):
    stage_id: int
    result: StageResultValue
    notes: Optional[str] = None
    score: Optional[Decimal] = None
    rejection_reason: Optional[str] = None


class HoldApplicationRequest(BaseModel):
    stage_id: int
    notes: Optional[str] = None


class StageResultUpsert(BaseModel):
    result: Optional[StageResultValue] = None
    score: Optional[Decimal] = None
    notes: Optional[str] = None
    test_file_path: Optional[str] = Field(default=None, max_length=500)
    test_file_name: Optional[str] = Field(default=None, max_length=300)
    test_score_raw: Optional[Decimal] = None
    test_pass_threshold: Optional[Decimal] = None


class CandidateStageResultRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    application_id: int
    stage_id: int
    stage_name: str
    stage_type: str
    result: Optional[str]
    score: Optional[Decimal]
    notes: Optional[str]
    test_file_path: Optional[str]
    test_file_name: Optional[str]
    test_score_raw: Optional[Decimal]
    test_pass_threshold: Optional[Decimal]
    evaluated_by_id: Optional[int]
    evaluated_by_name: Optional[str]
    evaluated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class KanbanCard(BaseModel):
    application_id: int
    candidate_id: int
    candidate_name: str
    applied_date: date
    source_channel: Optional[str]
    last_result: Optional[str]


class KanbanStage(BaseModel):
    stage: PipelineStageRead
    applications: List[KanbanCard]


class KanbanBoard(BaseModel):
    job_requisition_id: int
    stages: List[KanbanStage]


class InterviewPanelistRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    user_name: Optional[str]
    criteria_scores: Optional[List[dict]]
    overall_score: Optional[Decimal]
    result: Optional[str]
    private_notes: Optional[str]
    submitted_at: Optional[datetime]


class InterviewSessionCreate(BaseModel):
    stage_id: int
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=480)
    format: InterviewFormat = "in_person"
    location: Optional[str] = Field(default=None, max_length=300)
    note: Optional[str] = None
    panelist_user_ids: List[int] = Field(min_length=1)


class InterviewSessionUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=15, le=480)
    format: Optional[InterviewFormat] = None
    location: Optional[str] = Field(default=None, max_length=300)
    note: Optional[str] = None
    panelist_user_ids: Optional[List[int]] = None


class InterviewSessionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    application_id: int
    stage_id: int
    stage_name: str
    stage_type: str
    scheduled_at: datetime
    duration_minutes: int
    format: str
    location: Optional[str]
    note: Optional[str]
    status: str
    completed_at: Optional[datetime]
    cancel_reason: Optional[str]
    created_by_id: Optional[int]
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    panelists: List[InterviewPanelistRead]


class InterviewCancelRequest(BaseModel):
    cancel_reason: Optional[str] = None


class ScoreCriterionInput(BaseModel):
    criterion: str = Field(min_length=1, max_length=200)
    score: Decimal
    max_score: Decimal = Field(default=5)


class PanelistScoreSubmit(BaseModel):
    criteria_scores: List[ScoreCriterionInput] = Field(default_factory=list)
    overall_score: Optional[Decimal] = None
    result: StageResultValue
    private_notes: Optional[str] = None


class InterviewQuestionCreate(BaseModel):
    question_text: str = Field(min_length=1)
    category: Optional[str] = Field(default=None, max_length=100)
    difficulty: Optional[QuestionDifficulty] = None
    job_position_id: Optional[int] = None
    stage_type: Optional[PipelineStageType] = None
    is_active: bool = True


class InterviewQuestionUpdate(BaseModel):
    question_text: Optional[str] = Field(default=None, min_length=1)
    category: Optional[str] = Field(default=None, max_length=100)
    difficulty: Optional[QuestionDifficulty] = None
    job_position_id: Optional[int] = None
    stage_type: Optional[PipelineStageType] = None
    is_active: Optional[bool] = None


class InterviewQuestionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    question_text: str
    category: Optional[str]
    difficulty: Optional[str]
    job_position_id: Optional[int]
    stage_type: Optional[str]
    is_active: bool
    created_by_id: Optional[int]
    created_at: datetime


class ScorecardCriterionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    job_position_id: Optional[int] = None
    stage_type: Optional[PipelineStageType] = None
    max_score: int = Field(default=5, ge=1, le=10)
    sort_order: int = Field(default=0, ge=0, le=1000)
    is_active: bool = True


class ScorecardCriterionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    job_position_id: Optional[int] = None
    stage_type: Optional[PipelineStageType] = None
    max_score: Optional[int] = Field(default=None, ge=1, le=10)
    sort_order: Optional[int] = Field(default=None, ge=0, le=1000)
    is_active: Optional[bool] = None


class ScorecardCriterionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    job_position_id: Optional[int]
    stage_type: Optional[str]
    max_score: int
    sort_order: int
    is_active: bool


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
