from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field, field_validator


class DeptType(str, Enum):
    PHONG   = "PHONG"    # Phòng
    BAN     = "BAN"      # Ban
    BO_PHAN = "BO_PHAN"  # Bộ phận
    NHOM    = "NHOM"     # Nhóm
    TO      = "TO"       # Tổ


_DEPT_TYPE_LABELS: dict[str, str] = {
    "PHONG":   "Phòng",
    "BAN":     "Ban",
    "BO_PHAN": "Bộ phận",
    "NHOM":    "Nhóm",
    "TO":      "Tổ",
}


# ── Request schemas ────────────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    code:       str            = Field(..., max_length=20,  description="Mã phòng/ban (tự động viết hoa)")
    name:       str            = Field(..., max_length=200, description="Tên đầy đủ")
    short_name: Optional[str]  = Field(None, max_length=50, description="Tên viết tắt")
    display_prefix: Optional[str] = Field(None, max_length=5, description="Tiền tố hiển thị mã nhân viên")
    parent_id:  Optional[int]  = Field(None,  description="ID phòng/ban cha; NULL = cấp gốc")
    dept_type:  DeptType       = Field(DeptType.PHONG, description="Loại đơn vị")
    order_no:   int            = Field(0, description="Thứ tự hiển thị trong cùng cấp")

    @field_validator("code")
    @classmethod
    def _uppercase_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("name", "short_name")
    @classmethod
    def _strip_str(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("display_prefix")
    @classmethod
    def _normalize_display_prefix(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        normalized = v.strip().upper()
        return normalized or None


class DepartmentUpdate(BaseModel):
    """Tất cả trường đều optional. Chỉ trường nào được gửi mới được cập nhật."""
    name:       Optional[str]      = Field(None, max_length=200)
    short_name: Optional[str]      = Field(None, max_length=50)
    display_prefix: Optional[str]  = Field(None, max_length=5)
    # Nếu trường parent_id có trong request body (kể cả null) thì mới cập nhật.
    # null = chuyển về cấp gốc (không có cha).
    parent_id:  Optional[int]      = Field(None)
    dept_type:  Optional[DeptType] = None
    order_no:   Optional[int]      = None
    is_active:  Optional[bool]     = None

    @field_validator("name", "short_name")
    @classmethod
    def _strip_str(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("display_prefix")
    @classmethod
    def _normalize_display_prefix(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        normalized = v.strip().upper()
        return normalized or None


# ── Response schemas ───────────────────────────────────────────────────────────

class DepartmentRead(BaseModel):
    id:         int
    code:       str
    name:       str
    short_name: Optional[str]
    display_prefix: Optional[str]
    parent_id:  Optional[int]
    dept_type:  str
    order_no:   int
    is_active:  bool
    created_at: datetime
    updated_at: Optional[datetime]

    @computed_field
    @property
    def dept_type_label(self) -> str:
        return _DEPT_TYPE_LABELS.get(self.dept_type, self.dept_type)

    model_config = {"from_attributes": True}


class DepartmentTreeNode(DepartmentRead):
    """Node trong cây phân cấp — có danh sách con đệ quy."""
    children: list[DepartmentTreeNode] = []


class DepartmentBrief(BaseModel):
    id: int
    code: str
    name: str
    parent_id: Optional[int]
    dept_type: str
    is_active: bool

    @computed_field
    @property
    def dept_type_label(self) -> str:
        return _DEPT_TYPE_LABELS.get(self.dept_type, self.dept_type)

    model_config = {"from_attributes": True}


class DepartmentDetailSummary(BaseModel):
    direct_headcount: int
    total_headcount: int
    direct_child_count: int
    job_position_count: int


class DepartmentDirectEmployeeItem(BaseModel):
    id: int
    display_code: str
    full_name: str
    status: str
    start_date: date
    job_title_name: Optional[str] = None
    job_position_name: Optional[str] = None


class DepartmentDetailRead(BaseModel):
    department: DepartmentRead
    parent: Optional[DepartmentBrief] = None
    summary: DepartmentDetailSummary
    direct_employees: list[DepartmentDirectEmployeeItem]
