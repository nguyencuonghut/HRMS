"""Schemas cho hợp đồng lao động nhân viên (4.1)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

ALLOWED_STATUSES = {"active", "expired", "terminated", "draft"}
ALLOWED_FILE_EXTS = {".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _status_display(status: str, effective_to: Optional[date]) -> str:
    if status == "terminated":
        return "Đã hủy"
    if status == "draft":
        return "Chưa hiệu lực"
    today = date.today()
    if effective_to is None:
        return "Đang hiệu lực (vô thời hạn)"
    days = (effective_to - today).days
    if days < 0:
        return f"Hết hạn ({abs(days)} ngày trước)"
    if days == 0:
        return "Hết hạn hôm nay"
    return f"Đang hiệu lực (còn {days} ngày)"


def _days_until(status: str, effective_to: Optional[date]) -> Optional[int]:
    if status == "terminated" or effective_to is None:
        return None
    return (effective_to - date.today()).days


class ContractCreate(BaseModel):
    contract_category_id: int
    contract_number:      str
    signed_date:          date
    effective_from:       date
    effective_to:         Optional[date] = None
    insurance_salary:     Optional[Decimal] = None
    parent_contract_id:   Optional[int] = None
    notes:                Optional[str] = None

    @model_validator(mode="after")
    def check_dates(self) -> ContractCreate:
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to phải >= effective_from")
        return self


class ContractUpdate(BaseModel):
    contract_number:  Optional[str]     = None
    signed_date:      Optional[date]    = None
    effective_from:   Optional[date]    = None
    effective_to:     Optional[date]    = None
    insurance_salary: Optional[Decimal] = None
    status:           Optional[str]     = None   # chỉ cho phép "terminated"
    notes:            Optional[str]     = None

    @model_validator(mode="after")
    def check_status(self) -> ContractUpdate:
        if self.status and self.status not in ALLOWED_STATUSES:
            raise ValueError(f"status phải là một trong: {ALLOWED_STATUSES}")
        return self


class ContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                   int
    employee_id:          int
    parent_contract_id:   Optional[int]
    contract_category_id: int
    document_kind:        str
    contract_number:      str
    signed_date:          date
    effective_from:       date
    effective_to:         Optional[date]
    insurance_salary:     Optional[Decimal]
    status:               str
    status_display:       str
    days_until_expiry:    Optional[int]
    has_file:             bool
    file_name:            Optional[str]
    file_size:            Optional[int]
    mime_type:            Optional[str]
    category_name:        str
    notes:                Optional[str]
    created_at:           datetime
    updated_at:           Optional[datetime]
    appendices:           list[ContractRead] = []


class ContractListPage(BaseModel):
    items:     list[ContractRead]
    total:     int
    page:      int
    page_size: int
