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


class AdministrativeAddressSelection(BaseModel):
    system_type: SystemType
    province_unit_id: int
    district_unit_id: Optional[int] = None
    ward_unit_id: int
    address_line: Optional[str] = Field(None, max_length=255)


class ValidateDualLocationPathsRequest(BaseModel):
    old_address: AdministrativeAddressSelection
    new_address: AdministrativeAddressSelection

    @field_validator("old_address")
    @classmethod
    def _old_address_must_use_old_system(cls, value: AdministrativeAddressSelection) -> AdministrativeAddressSelection:
        if value.system_type != "old":
            raise ValueError("old_address phải dùng system_type='old'")
        return value

    @field_validator("new_address")
    @classmethod
    def _new_address_must_use_new_system(cls, value: AdministrativeAddressSelection) -> AdministrativeAddressSelection:
        if value.system_type != "new":
            raise ValueError("new_address phải dùng system_type='new'")
        return value


class ValidateDualLocationPathsResult(BaseModel):
    valid: bool
    message: str
    old_address: ValidateLocationPathResult
    new_address: ValidateLocationPathResult


InstitutionType = Literal["university", "college", "vocational", "high_school", "other"]


class EducationLevelCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    rank_no: int = Field(..., ge=1, le=999)
    is_active: bool = True

    @field_validator("code", "name")
    @classmethod
    def _strip_required_str(cls, v: str) -> str:
        return v.strip()


class EducationLevelUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    rank_no: Optional[int] = Field(None, ge=1, le=999)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _strip_optional_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class EducationLevelRead(BaseModel):
    id: int
    code: str
    name: str
    normalized_name: str
    rank_no: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EducationLevelListPage(BaseModel):
    items: list[EducationLevelRead]
    total: int
    page: int
    page_size: int


class EducationalInstitutionCreate(BaseModel):
    code: Optional[str] = Field(None, max_length=50)
    name: str = Field(..., max_length=255)
    short_name: Optional[str] = Field(None, max_length=100)
    institution_type: Optional[InstitutionType] = None
    country_code: Optional[str] = Field(None, max_length=10)
    province_code: Optional[str] = Field(None, max_length=20)
    is_active: bool = True

    @field_validator("code", "name", "short_name", "province_code")
    @classmethod
    def _strip_optional_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("country_code")
    @classmethod
    def _normalize_country_code(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else v


class EducationalInstitutionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    short_name: Optional[str] = Field(None, max_length=100)
    institution_type: Optional[InstitutionType] = None
    country_code: Optional[str] = Field(None, max_length=10)
    province_code: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None

    @field_validator("name", "short_name", "province_code")
    @classmethod
    def _strip_optional_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("country_code")
    @classmethod
    def _normalize_country_code(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else v


class EducationalInstitutionRead(BaseModel):
    id: int
    code: Optional[str]
    name: str
    normalized_name: str
    short_name: Optional[str]
    institution_type: Optional[str]
    country_code: Optional[str]
    province_code: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EducationalInstitutionListPage(BaseModel):
    items: list[EducationalInstitutionRead]
    total: int
    page: int
    page_size: int


class EducationMajorCreate(BaseModel):
    code: Optional[str] = Field(None, max_length=50)
    name: str = Field(..., max_length=255)
    major_group: Optional[str] = Field(None, max_length=100)
    is_active: bool = True

    @field_validator("code", "name", "major_group")
    @classmethod
    def _strip_optional_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class EducationMajorUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    major_group: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None

    @field_validator("name", "major_group")
    @classmethod
    def _strip_optional_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class EducationMajorRead(BaseModel):
    id: int
    code: Optional[str]
    name: str
    normalized_name: str
    major_group: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EducationMajorListPage(BaseModel):
    items: list[EducationMajorRead]
    total: int
    page: int
    page_size: int
