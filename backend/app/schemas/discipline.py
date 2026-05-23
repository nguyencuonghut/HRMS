"""Schemas kỷ luật nhân viên (8.2)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

DISCIPLINE_FORMS: dict[str, str] = {
    "khien_trach":        "Khiển trách",
    "keo_dai_nang_luong": "Kéo dài thời hạn nâng lương",
    "cach_chuc":          "Cách chức",
    "sa_thai":            "Sa thải",
}

DisciplineFormType = Literal[
    "khien_trach",
    "keo_dai_nang_luong",
    "cach_chuc",
    "sa_thai",
]

ALLOWED_FILE_EXTS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class DisciplineRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: Optional[str]
    discipline_form: str
    discipline_form_label: str
    violation_date: date
    effective_date: date
    end_date: Optional[date]
    extended_months: Optional[int]
    title: str
    description: Optional[str]
    decision_number: Optional[str]
    issued_by: Optional[str]
    note: Optional[str]
    has_file: bool
    file_name: Optional[str]
    file_size: Optional[int]
    created_by_id: Optional[int]
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class DisciplineCreate(BaseModel):
    employee_id: int
    discipline_form: DisciplineFormType
    violation_date: date
    effective_date: date
    extended_months: Optional[int] = Field(default=None, ge=1, le=12)
    title: str = Field(max_length=500)
    description: Optional[str] = None
    decision_number: Optional[str] = None
    issued_by: Optional[str] = None
    note: Optional[str] = None

    @model_validator(mode="after")
    def validate_extended_months(self) -> "DisciplineCreate":
        if self.discipline_form == "keo_dai_nang_luong":
            if self.extended_months is None:
                raise ValueError("Phải nhập số tháng kéo dài khi hình thức là 'Kéo dài nâng lương'")
        else:
            self.extended_months = None
        return self

    @model_validator(mode="after")
    def validate_dates(self) -> "DisciplineCreate":
        if self.violation_date > self.effective_date:
            raise ValueError("Ngày vi phạm không được sau ngày hiệu lực")
        return self


class DisciplineUpdate(BaseModel):
    discipline_form: Optional[DisciplineFormType] = None
    violation_date: Optional[date] = None
    effective_date: Optional[date] = None
    extended_months: Optional[int] = Field(default=None, ge=1, le=12)
    title: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None
    decision_number: Optional[str] = None
    issued_by: Optional[str] = None
    note: Optional[str] = None


class DisciplineListPage(BaseModel):
    items: list[DisciplineRead]
    total: int
    page: int
    page_size: int
