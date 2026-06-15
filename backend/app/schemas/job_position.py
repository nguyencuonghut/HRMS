from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.services.probation_rules import (
    get_probation_legal_group_label,
    get_probation_limit,
    normalize_probation_legal_group,
)


class JobPositionCreate(BaseModel):
    code:               str           = Field(..., max_length=20,  description="Mã vị trí (tự động viết hoa)")
    name:               str           = Field(..., max_length=200, description="Tên vị trí")
    department_id:      int           = Field(..., description="ID phòng/ban")
    job_title_id:       Optional[int] = Field(None, description="ID chức danh (tùy chọn)")
    default_grade:      int           = Field(1, ge=1, description="Bậc mặc định khi tuyển dụng")
    bhxh_allowance:     int           = Field(0, ge=0, description="Phụ cấp tính BHXH (VND)")
    non_bhxh_allowance: int           = Field(0, ge=0, description="Phụ cấp không tính BHXH (VND)")
    description:        Optional[str] = Field(None, description="Mô tả công việc")
    requirements:       Optional[str] = Field(None, description="Yêu cầu tuyển dụng")
    probation_legal_group: Optional[str] = Field(
        None,
        description="Nhóm pháp lý thử việc theo Điều 25 BLLĐ 2019",
    )

    @field_validator("code")
    @classmethod
    def _uppercase_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("probation_legal_group")
    @classmethod
    def _normalize_probation_legal_group(cls, v: Optional[str]) -> Optional[str]:
        return normalize_probation_legal_group(v)


class JobPositionUpdate(BaseModel):
    name:               Optional[str]  = Field(None, max_length=200)
    department_id:      Optional[int]  = None
    job_title_id:       Optional[int]  = None
    default_grade:      Optional[int]  = Field(None, ge=1)
    bhxh_allowance:     Optional[int]  = Field(None, ge=0)
    non_bhxh_allowance: Optional[int]  = Field(None, ge=0)
    description:        Optional[str]  = None
    requirements:       Optional[str]  = None
    probation_legal_group: Optional[str] = Field(
        None,
        description="Nhóm pháp lý thử việc theo Điều 25 BLLĐ 2019",
    )
    is_active:          Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("probation_legal_group")
    @classmethod
    def _normalize_probation_legal_group(cls, v: Optional[str]) -> Optional[str]:
        return normalize_probation_legal_group(v)


class JobPositionRead(BaseModel):
    """Chi tiết đầy đủ — dùng trong dialog."""
    id:                 int
    code:               str
    name:               str
    department_id:      int
    job_title_id:       Optional[int]
    default_grade:      int
    bhxh_allowance:     int
    non_bhxh_allowance: int
    description:        Optional[str]
    requirements:       Optional[str]
    probation_legal_group: Optional[str]
    probation_legal_group_label: Optional[str] = None
    probation_days_limit: Optional[int] = None
    is_active:          bool
    created_at:         datetime
    updated_at:         Optional[datetime]

    model_config = {"from_attributes": True}


class JobPositionListItem(BaseModel):
    """Dòng trong DataTable — có tên phòng/ban và chức danh đã join."""
    id:                 int
    code:               str
    name:               str
    department_id:      int
    department_name:    str
    job_title_id:       Optional[int]
    job_title_name:     Optional[str]
    bhxh_allowance:     int
    non_bhxh_allowance: int
    probation_legal_group: Optional[str]
    probation_legal_group_label: Optional[str] = None
    probation_days_limit: Optional[int] = None
    is_active:          bool
    created_at:         datetime
    updated_at:         Optional[datetime]


class ProbationLegalGroupOption(BaseModel):
    code: str
    label: str
    probation_days_limit: int


def enrich_probation_legal_group_fields(data: dict) -> dict:
    group = data.get("probation_legal_group")
    data["probation_legal_group_label"] = get_probation_legal_group_label(group)
    data["probation_days_limit"] = get_probation_limit(group)
    return data


class AttachmentRead(BaseModel):
    """File đính kèm của vị trí công việc."""
    id:           int
    file_name:    str
    file_path:    str          # object_name trong MinIO
    file_size:    Optional[int]
    uploaded_at:  datetime
    download_url: str          # presigned URL, hết hạn sau 1 giờ
