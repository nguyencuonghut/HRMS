from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class JobTitleCreate(BaseModel):
    code:  str = Field(..., max_length=20,  description="Mã chức danh (tự động viết hoa)")
    name:  str = Field(..., max_length=200, description="Tên chức danh")
    level: int = Field(1, ge=1,             description="Cấp bậc: 1 = cao nhất (Giám đốc)")

    @field_validator("code")
    @classmethod
    def _uppercase_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip()


class JobTitleUpdate(BaseModel):
    name:      Optional[str]  = Field(None, max_length=200)
    level:     Optional[int]  = Field(None, ge=1)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class JobTitleRead(BaseModel):
    id:         int
    code:       str
    name:       str
    level:      int
    is_active:  bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
