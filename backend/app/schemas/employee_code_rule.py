from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


RuleScopeType = Literal["department", "job_position"]


class EmployeeCodeSequenceRead(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    min_digits: int
    is_default: bool
    is_active: bool

    model_config = {"from_attributes": True}


class EmployeeCodeSequenceRuleRead(BaseModel):
    id: int
    scope_type: RuleScopeType
    department_id: Optional[int]
    job_position_id: Optional[int]
    employee_code_sequence_id: int
    employee_code_sequence_code: str
    employee_code_sequence_name: str
    apply_to_descendants: bool
    note: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]


class EmployeeCodeSequenceRuleUpsert(BaseModel):
    employee_code_sequence_id: int = Field(..., description="ID hệ mã nhân viên áp dụng")
    apply_to_descendants: bool = Field(False, description="Chỉ dùng cho rule theo phòng/ban")
    note: Optional[str] = Field(None, max_length=1000)
