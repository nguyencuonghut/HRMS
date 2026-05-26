from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Request schemas ────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email:        str            = Field(..., max_length=200)
    full_name:    str            = Field(..., max_length=200)
    password:     str            = Field(..., min_length=8)
    phone_number: Optional[str]  = Field(None, max_length=20)
    is_active:    bool           = Field(True)
    is_superuser: bool           = Field(False)

    @field_validator("email")
    @classmethod
    def _strip_lower(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        has_letter = any(c.isalpha() for c in v)
        has_digit  = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError("Mật khẩu phải có ít nhất 1 chữ cái và 1 chữ số")
        return v


class UserUpdate(BaseModel):
    email:        Optional[str]  = Field(None, max_length=200)
    full_name:    Optional[str]  = Field(None, max_length=200)
    phone_number: Optional[str]  = Field(None, max_length=20)
    is_active:    Optional[bool] = None

    @field_validator("email")
    @classmethod
    def _strip_lower(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else v

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        has_letter = any(c.isalpha() for c in v)
        has_digit  = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError("Mật khẩu phải có ít nhất 1 chữ cái và 1 chữ số")
        return v


class RoleAssign(BaseModel):
    role_id:        int              = Field(...)
    scope_type:     Optional[str]   = Field(None, max_length=20)
    department_ids: Optional[list[int]] = None


# ── Response schemas ───────────────────────────────────────────────────────────

class RoleRef(BaseModel):
    id:   int
    code: str
    name: str

    model_config = {"from_attributes": True}


class UserRead(BaseModel):
    id:            int
    email:         str
    full_name:     str
    phone_number:  Optional[str]
    is_active:     bool
    is_superuser:  bool
    last_login_at: Optional[datetime]
    created_at:    datetime
    updated_at:    Optional[datetime]
    roles:         list[RoleRef] = []

    model_config = {"from_attributes": True}


class UserListItem(BaseModel):
    id:            int
    email:         str
    full_name:     str
    phone_number:  Optional[str]
    is_active:     bool
    is_superuser:  bool
    last_login_at: Optional[datetime]
    roles:         list[RoleRef] = []

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserListItem]
    total: int
    skip:  int
    limit: int
