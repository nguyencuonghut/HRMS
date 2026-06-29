from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

COMMON_PASSWORDS = {
    "123456",
    "12345678",
    "password",
    "qwerty",
    "abc123",
    "111111",
    "admin123",
    "welcome1",
}


def validate_password_strength(v: str) -> str:
    has_letter = any(c.isalpha() for c in v)
    has_digit = any(c.isdigit() for c in v)
    has_special = any(not c.isalnum() for c in v)
    if len(v) < 8:
        raise ValueError("Mật khẩu phải có ít nhất 8 ký tự")
    if not has_letter:
        raise ValueError("Mật khẩu phải có ít nhất 1 chữ cái")
    if not has_digit:
        raise ValueError("Mật khẩu phải có ít nhất 1 chữ số")
    if not has_special:
        raise ValueError("Mật khẩu phải có ít nhất 1 ký tự đặc biệt")
    if v.lower() in COMMON_PASSWORDS:
        raise ValueError("Mật khẩu quá phổ biến, vui lòng chọn mật khẩu khác")
    return v


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
        return validate_password_strength(v)


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
        return validate_password_strength(v)


class RoleAssign(BaseModel):
    role_id:        int              = Field(...)
    scope_type:     Optional[str]   = Field(None, max_length=20)
    department_ids: Optional[list[int]] = None

    @field_validator("scope_type")
    @classmethod
    def _validate_scope_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        value = v.strip().lower()
        if value != "department":
            raise ValueError("scope_type chỉ hỗ trợ giá trị 'department'")
        return value

    @field_validator("department_ids")
    @classmethod
    def _normalize_department_ids(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        if v is None:
            return None
        normalized = [int(item) for item in v]
        return list(dict.fromkeys(normalized))


# ── Response schemas ───────────────────────────────────────────────────────────

class RoleRef(BaseModel):
    id:   int
    code: str
    name: str
    scope_type: Optional[str] = None
    department_ids: list[int] = Field(default_factory=list)
    department_names: list[str] = Field(default_factory=list)

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
