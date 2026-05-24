"""Schemas đào tạo (9.1 + 9.2 + 9.3)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

COURSE_TYPES: dict[str, str] = {
    "noi_bo":    "Nội bộ",
    "ben_ngoai": "Bên ngoài",
    "online":    "Online",
}

PLAN_STATUSES: dict[str, str] = {
    "draft":     "Dự thảo",
    "approved":  "Đã duyệt",
    "cancelled": "Đã hủy",
}

CourseTypeValue = Literal["noi_bo", "ben_ngoai", "online"]
PlanStatusValue = Literal["draft", "approved", "cancelled"]


# ── Course schemas ────────────────────────────────────────────────────────────

class CourseRead(BaseModel):
    model_config = {"from_attributes": True}

    id:               int
    code:             str
    name:             str
    course_type:      str
    course_type_label: str
    duration_hours:   Optional[int]
    organizer:        Optional[str]
    description:      Optional[str]
    cost_per_person:  Optional[Decimal]
    is_mandatory:     bool
    is_active:        bool
    created_at:       datetime


class CourseCreate(BaseModel):
    code:            str            = Field(max_length=50)
    name:            str            = Field(max_length=500)
    course_type:     CourseTypeValue
    duration_hours:  Optional[int]     = Field(default=None, ge=1)
    organizer:       Optional[str]     = None
    description:     Optional[str]     = None
    cost_per_person: Optional[Decimal] = Field(default=None, ge=0)
    is_mandatory:    bool              = False


class CourseUpdate(BaseModel):
    code:            Optional[str]     = Field(default=None, max_length=50)
    name:            Optional[str]     = Field(default=None, max_length=500)
    course_type:     Optional[CourseTypeValue] = None
    duration_hours:  Optional[int]     = Field(default=None, ge=1)
    organizer:       Optional[str]     = None
    description:     Optional[str]     = None
    cost_per_person: Optional[Decimal] = Field(default=None, ge=0)
    is_mandatory:    Optional[bool]    = None
    is_active:       Optional[bool]    = None


class CourseListPage(BaseModel):
    items:     List[CourseRead]
    total:     int
    page:      int
    page_size: int


# ── Plan-course schemas ───────────────────────────────────────────────────────

class PlanCourseRead(BaseModel):
    model_config = {"from_attributes": True}

    id:               int
    plan_id:          int
    course_id:        int
    course_code:      str
    course_name:      str
    course_type_label: str
    duration_hours:   Optional[int]
    target_count:     Optional[int]
    scheduled_date:   Optional[date]
    note:             Optional[str]


class PlanCourseCreate(BaseModel):
    course_id:      int
    target_count:   Optional[int]  = Field(default=None, ge=1)
    scheduled_date: Optional[date] = None
    note:           Optional[str]  = None


class PlanCourseUpdate(BaseModel):
    target_count:   Optional[int]  = None
    scheduled_date: Optional[date] = None
    note:           Optional[str]  = None


# ── Plan schemas ──────────────────────────────────────────────────────────────

class PlanRead(BaseModel):
    model_config = {"from_attributes": True}

    id:               int
    title:            str
    year:             int
    quarter:          Optional[int]
    department_id:    Optional[int]
    department_name:  Optional[str]
    status:           str
    status_label:     str
    description:      Optional[str]
    created_by_name:  Optional[str]
    created_at:       datetime
    course_count:     int


class PlanReadDetail(PlanRead):
    courses: List[PlanCourseRead]


class PlanCreate(BaseModel):
    title:         str           = Field(max_length=500)
    year:          int           = Field(ge=2000, le=2100)
    quarter:       Optional[int] = Field(default=None, ge=1, le=4)
    department_id: Optional[int] = None
    description:   Optional[str] = None


class PlanUpdate(BaseModel):
    title:       Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None


class PlanListPage(BaseModel):
    items:     List[PlanRead]
    total:     int
    page:      int
    page_size: int


# ── Training record schemas (9.2) ─────────────────────────────────────────────

RECORD_STATUSES: dict[str, str] = {
    "chua_bat_dau":     "Chưa bắt đầu",
    "dang_hoc":         "Đang học",
    "hoan_thanh":       "Hoàn thành",
    "khong_hoan_thanh": "Không hoàn thành",
    "vang_mat":         "Vắng mặt",
}

RECORD_RESULTS: dict[str, str] = {
    "dat":      "Đạt",
    "khong_dat": "Không đạt",
}

RecordStatusValue = Literal["chua_bat_dau", "dang_hoc", "hoan_thanh", "khong_hoan_thanh", "vang_mat"]
RecordResultValue = Literal["dat", "khong_dat"]


class TrainingRecordRead(BaseModel):
    model_config = {"from_attributes": True}

    id:               int
    employee_id:      int
    employee_code:    str
    employee_name:    str
    department_name:  Optional[str]
    course_id:        int
    course_name:      str
    course_type:      str
    course_type_label: str
    plan_id:          Optional[int]
    plan_title:       Optional[str]
    status:           str
    status_label:     str
    result:           Optional[str]
    result_label:     Optional[str]
    score:            Optional[Decimal]
    start_date:       Optional[date]
    end_date:         Optional[date]
    note:             Optional[str]
    created_by_name:  Optional[str]
    created_at:       datetime


class TrainingRecordCreate(BaseModel):
    employee_id: int
    course_id:   int
    plan_id:     Optional[int]   = None
    status:      RecordStatusValue = "chua_bat_dau"
    start_date:  Optional[date]  = None
    end_date:    Optional[date]  = None
    note:        Optional[str]   = None

    @model_validator(mode="after")
    def validate_dates(self) -> "TrainingRecordCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date phải >= start_date")
        return self


class TrainingRecordUpdate(BaseModel):
    status:     Optional[RecordStatusValue] = None
    result:     Optional[RecordResultValue] = None
    score:      Optional[Decimal]           = Field(default=None, ge=0, le=100)
    start_date: Optional[date]              = None
    end_date:   Optional[date]              = None
    note:       Optional[str]               = None

    @model_validator(mode="after")
    def validate_dates(self) -> "TrainingRecordUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date phải >= start_date")
        return self


class TrainingRecordListPage(BaseModel):
    items:     List[TrainingRecordRead]
    total:     int
    page:      int
    page_size: int


class BulkAssignRequest(BaseModel):
    employee_ids:   List[int]     = Field(default=[], max_length=200)
    department_ids: List[int]     = Field(default=[])   # thay thế employee_ids — assign toàn bộ NV của các phòng ban
    plan_id:        int
    course_id:      int
    note:           Optional[str] = None

    @model_validator(mode="after")
    def validate_ids(self) -> "BulkAssignRequest":
        if not self.employee_ids and not self.department_ids:
            raise ValueError("Cần chọn ít nhất 1 nhân viên hoặc 1 phòng ban")
        if self.employee_ids and self.department_ids:
            raise ValueError("Chỉ được chọn một trong hai: employee_ids hoặc department_ids")
        return self


class BulkAssignResult(BaseModel):
    created: int
    skipped: int


# ── Certificate schemas (9.3) ─────────────────────────────────────────────────

EXPIRY_SOON_DAYS = 30

ExpiryStatusValue = Literal["valid", "expiring_soon", "expired", "no_expiry"]


def compute_expiry_status(expiry_date: Optional[date], today: date) -> str:
    if expiry_date is None:
        return "no_expiry"
    if expiry_date < today:
        return "expired"
    if expiry_date <= today + timedelta(days=EXPIRY_SOON_DAYS):
        return "expiring_soon"
    return "valid"


def compute_days_until_expiry(expiry_date: Optional[date], today: date) -> Optional[int]:
    if expiry_date is None or expiry_date < today:
        return None
    return (expiry_date - today).days


class CertificateRead(BaseModel):
    model_config = {"from_attributes": True}

    id:                   int
    employee_id:          int
    employee_code:        str
    employee_name:        str
    department_name:      Optional[str]

    certificate_name:     str
    issuing_organization: Optional[str]
    issued_date:          date
    expiry_date:          Optional[date]

    expiry_status:        str
    days_until_expiry:    Optional[int]

    related_course_id:    Optional[int]
    related_course_name:  Optional[str]

    note:                 Optional[str]
    has_file:             bool
    file_name:            Optional[str]
    file_size:            Optional[int]

    created_by_name:      Optional[str]
    created_at:           datetime


class CertificateCreate(BaseModel):
    employee_id:          int
    certificate_name:     str              = Field(min_length=1, max_length=500)
    issuing_organization: Optional[str]    = None
    issued_date:          date
    expiry_date:          Optional[date]   = None
    related_course_id:    Optional[int]    = None
    note:                 Optional[str]    = None

    @model_validator(mode="after")
    def validate_expiry_after_issued(self) -> "CertificateCreate":
        if self.expiry_date is not None and self.expiry_date <= self.issued_date:
            raise ValueError("expiry_date phải sau issued_date")
        return self


class CertificateUpdate(BaseModel):
    certificate_name:     Optional[str]    = Field(default=None, min_length=1, max_length=500)
    issuing_organization: Optional[str]    = None
    issued_date:          Optional[date]   = None
    expiry_date:          Optional[date]   = None
    related_course_id:    Optional[int]    = None
    note:                 Optional[str]    = None

    @model_validator(mode="after")
    def validate_expiry_after_issued(self) -> "CertificateUpdate":
        if (
            self.expiry_date is not None
            and self.issued_date is not None
            and self.expiry_date <= self.issued_date
        ):
            raise ValueError("expiry_date phải sau issued_date")
        return self


class CertificateListPage(BaseModel):
    items:     List[CertificateRead]
    total:     int
    page:      int
    page_size: int
