from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, model_validator


def compute_total_days(
    start_date: date,
    end_date: date,
    start_half: str | None,
    end_half: str | None,
) -> Decimal:
    calendar_days = (end_date - start_date).days + 1
    offset = Decimal("0")
    if start_half == "PM":
        offset += Decimal("0.5")
    if end_half == "AM":
        offset += Decimal("0.5")
    total = Decimal(str(calendar_days)) - offset
    if total <= 0:
        raise ValueError("Số ngày nghỉ phải >= 0.5")
    return total


class LeaveRecordCreate(BaseModel):
    employee_id:   int
    leave_type_id: int
    start_date:    date
    end_date:      date
    start_half:    Optional[Literal["AM", "PM"]] = None
    end_half:      Optional[Literal["AM", "PM"]] = None
    reason:        Optional[str] = None
    note:          Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self) -> LeaveRecordCreate:
        if self.start_date > self.end_date:
            raise ValueError("start_date phải ≤ end_date")
        if self.start_date.year != self.end_date.year:
            raise ValueError(
                "Không hỗ trợ ghi nhận nghỉ phép vắt qua năm — vui lòng tạo 2 bản ghi"
            )
        return self


class LeaveRecordUpdate(BaseModel):
    start_date:  Optional[date] = None
    end_date:    Optional[date] = None
    start_half:  Optional[Literal["AM", "PM"]] = None
    end_half:    Optional[Literal["AM", "PM"]] = None
    reason:      Optional[str] = None
    note:        Optional[str] = None


class CancelRequest(BaseModel):
    cancel_reason: Optional[str] = None


class LeaveRecordRead(BaseModel):
    id:             int
    employee_id:    int
    employee_code:  str
    employee_name:  str
    leave_type_id:  int
    leave_type_code: str
    leave_type_name: str
    entitlement_id: Optional[int]
    start_date:     date
    end_date:       date
    start_half:     Optional[str]
    end_half:       Optional[str]
    total_days:     float
    reason:         Optional[str]
    status:         str
    cancel_reason:  Optional[str]
    note:           Optional[str]
    created_by_id:  Optional[int]
    created_at:     datetime
    updated_at:     Optional[datetime]
    remaining_days_after: Optional[float]
    warning:        Optional[str]

    model_config = {"from_attributes": True}


class LeaveRecordListPage(BaseModel):
    items:     list[LeaveRecordRead]
    total:     int
    page:      int
    page_size: int
