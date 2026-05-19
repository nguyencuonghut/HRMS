from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field, model_validator


class LeaveEntitlementCreate(BaseModel):
    employee_id:       int
    leave_type_id:     int
    year:              int   = Field(ge=2020, le=2100)
    allocated_days:    float = Field(ge=0, le=365)
    carryover_days:    float = Field(default=0.0, ge=0, le=365)
    carryover_expires: Optional[date]  = None
    note:              Optional[str]   = None

    @model_validator(mode="after")
    def _carryover_consistency(self) -> LeaveEntitlementCreate:
        if self.carryover_days > 0 and self.carryover_expires is None:
            raise ValueError("carryover_expires phải được cung cấp khi carryover_days > 0")
        return self


class LeaveEntitlementUpdate(BaseModel):
    allocated_days:    Optional[float] = Field(default=None, ge=0, le=365)
    carryover_days:    Optional[float] = Field(default=None, ge=0, le=365)
    carryover_expires: Optional[date]  = None
    note:              Optional[str]   = None


class LeaveEntitlementRead(BaseModel):
    id:                int
    employee_id:       int
    employee_code:     str
    employee_name:     str
    leave_type_id:     int
    leave_type_code:   str
    leave_type_name:   str
    year:              int
    allocated_days:    float
    carryover_days:    float
    carryover_expires: Optional[date]
    used_days:         float
    note:              Optional[str]
    created_by_id:     Optional[int]
    created_at:        datetime
    updated_at:        Optional[datetime]

    @computed_field
    @property
    def remaining_days(self) -> float:
        """
        FIFO: carryover tiêu trước allocated.
        Sau cutoff — chỉ phần carryover chưa dùng bị hủy:
          remaining = allocated - max(0, used - carryover)
        """
        allocated = self.allocated_days
        carryover = self.carryover_days
        used      = self.used_days
        if self.carryover_expires and date.today() > self.carryover_expires:
            used_from_regular = max(0.0, used - carryover)
            return allocated - used_from_regular
        return allocated + carryover - used

    model_config = {"from_attributes": True}


class BulkAllocateRequest(BaseModel):
    year:             int                  = Field(ge=2020, le=2100)
    # None = chỉ annual_leave; truyền danh sách code để nạp nhiều loại
    leave_type_codes: Optional[list[str]]  = None
    # None = tất cả nhân viên active
    employee_ids:     Optional[list[int]]  = None
    # True = ghi đè dù đã có used_days > 0
    overwrite:        bool                 = False


class BulkAllocateResult(BaseModel):
    year:      int
    allocated: int    # số bản ghi được tạo / cập nhật
    skipped:   int    # bỏ qua (đã có used_days > 0 và overwrite=False)
    errors:    list[str]
