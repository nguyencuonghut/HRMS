from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Request schemas ────────────────────────────────────────────────────────────

class RoleCreate(BaseModel):
    code:        str            = Field(..., max_length=50)
    name:        str            = Field(..., max_length=200)
    description: Optional[str] = None

    @field_validator("code")
    @classmethod
    def _lower_code(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip()


class RoleUpdate(BaseModel):
    name:        Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class PermissionsReplace(BaseModel):
    permission_ids: list[int]


# ── Response schemas ───────────────────────────────────────────────────────────

class PermissionRead(BaseModel):
    id:          int
    code:        str
    name:        str
    module:      str
    module_label: str
    module_order: int
    action:      str
    action_label: str
    action_order: int
    description: Optional[str]


class RoleRead(BaseModel):
    id:          int
    code:        str
    name:        str
    description: Optional[str]
    is_system:   bool
    created_at:  datetime
    permissions: list[PermissionRead] = []

    model_config = {"from_attributes": True}


class RoleListItem(BaseModel):
    id:               int
    code:             str
    name:             str
    description:      Optional[str]
    is_system:        bool
    created_at:       datetime
    permission_count: int = 0

    model_config = {"from_attributes": True}
