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


DocumentKind = Literal["labor_contract", "contract_appendix"]
LegalContractType = Literal["indefinite_term", "definite_term"]
TemplateEngine = Literal["docx_placeholders"]
ExpiryPolicy = Literal["none", "fixed_date", "months_after_issue"]
SourceScope = Literal["employee", "organization", "contract_draft", "signer", "system"]
PlaceholderDataType = Literal["text", "date", "number", "currency", "boolean"]


class ContractCategoryCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    document_kind: DocumentKind
    legal_contract_type: Optional[LegalContractType] = None
    business_group: Optional[str] = Field(None, max_length=50)
    default_term_months: Optional[int] = Field(None, ge=1, le=120)
    sort_order: int = Field(0, ge=0, le=9999)
    is_active: bool = True
    description: Optional[str] = None

    @field_validator("code", "name", "business_group", "description")
    @classmethod
    def _strip_contract_category_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("code")
    @classmethod
    def _normalize_contract_category_code(cls, v: str) -> str:
        return v.upper()


class ContractCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    document_kind: Optional[DocumentKind] = None
    legal_contract_type: Optional[LegalContractType] = None
    business_group: Optional[str] = Field(None, max_length=50)
    default_term_months: Optional[int] = Field(None, ge=1, le=120)
    sort_order: Optional[int] = Field(None, ge=0, le=9999)
    is_active: Optional[bool] = None
    description: Optional[str] = None

    @field_validator("name", "business_group", "description")
    @classmethod
    def _strip_contract_category_update_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class ContractCategoryRead(BaseModel):
    id: int
    code: str
    name: str
    normalized_name: str
    document_kind: str
    legal_contract_type: Optional[str]
    business_group: Optional[str]
    default_term_months: Optional[int]
    sort_order: int
    is_active: bool
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ContractCategoryListPage(BaseModel):
    items: list[ContractCategoryRead]
    total: int
    page: int
    page_size: int


class NationalityCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=255)
    iso2_code: Optional[str] = Field(None, max_length=2)
    iso3_code: Optional[str] = Field(None, max_length=3)
    is_active: bool = True

    @field_validator("code", "name")
    @classmethod
    def _strip_nationality_required(cls, v: str) -> str:
        return v.strip()

    @field_validator("code", "iso2_code", "iso3_code")
    @classmethod
    def _normalize_nationality_code(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else v


class NationalityUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    iso2_code: Optional[str] = Field(None, max_length=2)
    iso3_code: Optional[str] = Field(None, max_length=3)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _strip_nationality_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("iso2_code", "iso3_code")
    @classmethod
    def _normalize_nationality_update_codes(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else v


class NationalityRead(BaseModel):
    id: int
    code: str
    name: str
    normalized_name: str
    iso2_code: Optional[str]
    iso3_code: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class NationalityListPage(BaseModel):
    items: list[NationalityRead]
    total: int
    page: int
    page_size: int


class EthnicityCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=255)
    is_active: bool = True

    @field_validator("code", "name")
    @classmethod
    def _strip_ethnicity_required(cls, v: str) -> str:
        return v.strip()

    @field_validator("code")
    @classmethod
    def _normalize_ethnicity_code(cls, v: str) -> str:
        return v.upper()


class EthnicityUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _strip_ethnicity_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class EthnicityRead(BaseModel):
    id: int
    code: str
    name: str
    normalized_name: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EthnicityListPage(BaseModel):
    items: list[EthnicityRead]
    total: int
    page: int
    page_size: int


class ReligionCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=255)
    is_active: bool = True

    @field_validator("code", "name")
    @classmethod
    def _strip_religion_required(cls, v: str) -> str:
        return v.strip()

    @field_validator("code")
    @classmethod
    def _normalize_religion_code(cls, v: str) -> str:
        return v.upper()


class ReligionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _strip_religion_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class ReligionRead(BaseModel):
    id: int
    code: str
    name: str
    normalized_name: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ReligionListPage(BaseModel):
    items: list[ReligionRead]
    total: int
    page: int
    page_size: int


class BankCreate(BaseModel):
    code: str = Field(..., max_length=30)
    name: str = Field(..., max_length=255)
    short_name: Optional[str] = Field(None, max_length=100)
    bin_code: Optional[str] = Field(None, max_length=20)
    swift_code: Optional[str] = Field(None, max_length=20)
    is_active: bool = True

    @field_validator("code", "name", "short_name", "bin_code", "swift_code")
    @classmethod
    def _strip_bank_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("code", "swift_code")
    @classmethod
    def _normalize_bank_code(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else v


class BankUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    short_name: Optional[str] = Field(None, max_length=100)
    bin_code: Optional[str] = Field(None, max_length=20)
    swift_code: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None

    @field_validator("name", "short_name", "bin_code", "swift_code")
    @classmethod
    def _strip_bank_update_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("swift_code")
    @classmethod
    def _normalize_bank_update_swift(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else v


class BankRead(BaseModel):
    id: int
    code: str
    name: str
    normalized_name: str
    short_name: Optional[str]
    bin_code: Optional[str]
    swift_code: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class BankListPage(BaseModel):
    items: list[BankRead]
    total: int
    page: int
    page_size: int


class SkillCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    skill_group: Optional[str] = Field(None, max_length=100)
    is_active: bool = True

    @field_validator("code", "name", "skill_group")
    @classmethod
    def _strip_skill_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("code")
    @classmethod
    def _normalize_skill_code(cls, v: str) -> str:
        return v.upper()


class SkillUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    skill_group: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None

    @field_validator("name", "skill_group")
    @classmethod
    def _strip_skill_update_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class SkillRead(BaseModel):
    id: int
    code: str
    name: str
    normalized_name: str
    skill_group: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SkillListPage(BaseModel):
    items: list[SkillRead]
    total: int
    page: int
    page_size: int


class CertificateCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    certificate_group: Optional[str] = Field(None, max_length=100)
    issuer_name: Optional[str] = Field(None, max_length=255)
    expiry_policy: Optional[ExpiryPolicy] = None
    default_valid_months: Optional[int] = Field(None, ge=1, le=240)
    is_active: bool = True

    @field_validator("code", "name", "certificate_group", "issuer_name")
    @classmethod
    def _strip_certificate_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("code")
    @classmethod
    def _normalize_certificate_code(cls, v: str) -> str:
        return v.upper()


class CertificateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    certificate_group: Optional[str] = Field(None, max_length=100)
    issuer_name: Optional[str] = Field(None, max_length=255)
    expiry_policy: Optional[ExpiryPolicy] = None
    default_valid_months: Optional[int] = Field(None, ge=1, le=240)
    is_active: Optional[bool] = None

    @field_validator("name", "certificate_group", "issuer_name")
    @classmethod
    def _strip_certificate_update_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class CertificateRead(BaseModel):
    id: int
    code: str
    name: str
    normalized_name: str
    certificate_group: Optional[str]
    issuer_name: Optional[str]
    expiry_policy: Optional[str]
    default_valid_months: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CertificateListPage(BaseModel):
    items: list[CertificateRead]
    total: int
    page: int
    page_size: int


class LeaveTypeCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    is_paid_leave: bool = False
    affects_annual_leave: bool = False
    allow_half_day: bool = False
    requires_attachment: bool = False
    color_tag: Optional[str] = Field(None, max_length=20)
    is_active: bool = True
    description: Optional[str] = None

    @field_validator("code", "name", "color_tag", "description")
    @classmethod
    def _strip_leave_type_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("code")
    @classmethod
    def _normalize_leave_type_code(cls, v: str) -> str:
        return v.upper()


class LeaveTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    is_paid_leave: Optional[bool] = None
    affects_annual_leave: Optional[bool] = None
    allow_half_day: Optional[bool] = None
    requires_attachment: Optional[bool] = None
    color_tag: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    description: Optional[str] = None

    @field_validator("name", "color_tag", "description")
    @classmethod
    def _strip_leave_type_update_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class LeaveTypeRead(BaseModel):
    id: int
    code: str
    name: str
    normalized_name: str
    is_paid_leave: bool
    affects_annual_leave: bool
    allow_half_day: bool
    requires_attachment: bool
    color_tag: Optional[str]
    is_active: bool
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LeaveTypeListPage(BaseModel):
    items: list[LeaveTypeRead]
    total: int
    page: int
    page_size: int


class ContractTemplateCreate(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    contract_category_id: int
    document_kind: DocumentKind
    template_engine: TemplateEngine = "docx_placeholders"
    file_name: str = Field(..., max_length=255)
    storage_path: Optional[str] = Field(None, max_length=500)
    mime_type: str = Field(..., max_length=100)
    file_size: Optional[int] = Field(None, ge=0)
    file_checksum: Optional[str] = Field(None, max_length=128)
    version_no: int = Field(1, ge=1, le=999)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_active: bool = True
    note: Optional[str] = None

    @field_validator("code", "name", "file_name", "storage_path", "mime_type", "file_checksum", "note")
    @classmethod
    def _strip_contract_template_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("code")
    @classmethod
    def _normalize_contract_template_code(cls, v: str) -> str:
        return v.lower()


class ContractTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    contract_category_id: Optional[int] = None
    document_kind: Optional[DocumentKind] = None
    template_engine: Optional[TemplateEngine] = None
    file_name: Optional[str] = Field(None, max_length=255)
    storage_path: Optional[str] = Field(None, max_length=500)
    mime_type: Optional[str] = Field(None, max_length=100)
    file_size: Optional[int] = Field(None, ge=0)
    file_checksum: Optional[str] = Field(None, max_length=128)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None
    note: Optional[str] = None

    @field_validator("name", "file_name", "storage_path", "mime_type", "file_checksum", "note")
    @classmethod
    def _strip_contract_template_update_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class ContractTemplateRead(BaseModel):
    id: int
    code: str
    name: str
    normalized_name: str
    contract_category_id: int
    document_kind: str
    template_engine: str
    file_name: str
    storage_path: Optional[str]
    mime_type: str
    file_size: Optional[int]
    file_checksum: Optional[str]
    version_no: int
    effective_from: Optional[date]
    effective_to: Optional[date]
    is_active: bool
    note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ContractTemplateListPage(BaseModel):
    items: list[ContractTemplateRead]
    total: int
    page: int
    page_size: int


class ContractTemplatePlaceholderWrite(BaseModel):
    placeholder_key: str = Field(..., max_length=100)
    label: str = Field(..., max_length=255)
    source_scope: SourceScope
    source_path: str = Field(..., max_length=255)
    data_type: PlaceholderDataType
    formatter: Optional[str] = Field(None, max_length=50)
    is_required: bool = False
    default_value: Optional[str] = Field(None, max_length=255)
    sort_order: int = Field(0, ge=0, le=9999)

    @field_validator("placeholder_key", "label", "source_path", "formatter", "default_value")
    @classmethod
    def _strip_placeholder_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class ContractTemplatePlaceholderRead(BaseModel):
    id: int
    template_id: int
    placeholder_key: str
    label: str
    source_scope: str
    source_path: str
    data_type: str
    formatter: Optional[str]
    is_required: bool
    default_value: Optional[str]
    sort_order: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
