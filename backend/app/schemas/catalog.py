from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


UnitType = Literal["province", "district", "ward"]
SystemType = Literal["old", "new"]
ImportMode = Literal["merge", "replace"]


class AdministrativeUnitCreate(BaseModel):
    code: str = Field(..., max_length=20)
    source_code: Optional[str] = Field(None, max_length=20)
    name: str = Field(..., max_length=255)
    unit_type: UnitType
    official_name: Optional[str] = Field(None, max_length=255)
    province_code: Optional[str] = Field(None, max_length=20)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    source_name: Optional[str] = Field(None, max_length=100)
    source_version: Optional[str] = Field(None, max_length=50)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def _strip_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("name", "official_name", "province_code", "source_name", "source_version", "source_code")
    @classmethod
    def _strip_str(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class AdministrativeUnitUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    official_name: Optional[str] = Field(None, max_length=255)
    province_code: Optional[str] = Field(None, max_length=20)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None

    @field_validator("name", "official_name", "province_code")
    @classmethod
    def _strip_str(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class AdministrativeUnitRead(BaseModel):
    id: int
    code: str
    source_code: Optional[str]
    name: str
    normalized_name: str
    unit_type: str
    official_name: Optional[str]
    province_code: Optional[str]
    is_active: bool
    effective_from: Optional[date]
    effective_to: Optional[date]
    source_name: Optional[str]
    source_version: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AdministrativeTreeNode(AdministrativeUnitRead):
    children: list["AdministrativeTreeNode"] = []


class AdministrativeUnitListPage(BaseModel):
    items: list[AdministrativeUnitRead]
    total: int
    page: int
    page_size: int


class AdministrativeImportRequest(BaseModel):
    system_type: SystemType = "new"
    json_path: Optional[str] = None
    source_name: str = Field("official_import", max_length=100)
    source_version: str = Field("qd19_2025", max_length=50)
    file_name: Optional[str] = Field(None, max_length=255)
    imported_by: Optional[int] = None
    mode: ImportMode = "merge"


class AdministrativeImportBatchRead(BaseModel):
    id: int
    source_name: str
    source_version: str
    file_name: Optional[str]
    imported_by: Optional[int]
    imported_at: datetime
    status: str
    total_rows: int
    success_rows: int
    failed_rows: int
    error_summary: Optional[str]

    model_config = {"from_attributes": True}


class AddressSystemRead(BaseModel):
    code: SystemType
    label: str
    levels: int


class ValidateLocationPathRequest(BaseModel):
    system_type: SystemType
    province_unit_id: int
    district_unit_id: Optional[int] = None
    ward_unit_id: int


class ValidateLocationPathResult(BaseModel):
    valid: bool
    message: str
