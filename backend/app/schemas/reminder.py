"""Schemas cho module Sự kiện & Nhắc nhở (3.6)."""

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel

VALID_EVENT_TYPES = {"birthday", "anniversary", "probation_end", "contract_expiry"}

ANNIVERSARY_MILESTONES = [1, 3, 5, 10]


class ReminderItem(BaseModel):
    employee_id:   int
    employee_code: str
    employee_name: str
    department:    Optional[str]
    event_type:    str
    event_date:    date
    days_until:    int
    extra:         dict[str, Any] = {}


class RemindersResponse(BaseModel):
    birthday:         list[ReminderItem]
    anniversary:      list[ReminderItem]
    probation_end:    list[ReminderItem]
    contract_expiry:  list[ReminderItem] = []
    total:            int
