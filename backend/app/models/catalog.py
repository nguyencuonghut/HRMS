from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AdministrativeUnit(SQLModel, table=True):
    """Đơn vị hành chính: tỉnh/thành, quận/huyện, xã/phường."""

    __tablename__ = "administrative_units"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=20, unique=True, index=True)
    source_code: Optional[str] = Field(default=None, max_length=20, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    # province | district | ward
    unit_type: str = Field(max_length=20, sa_column=Column(sa.String(20), nullable=False, index=True))
    official_name: Optional[str] = Field(default=None, max_length=255)
    # denormalized để filter nhanh theo tỉnh
    province_code: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)
    effective_from: Optional[date] = Field(default=None)
    effective_to: Optional[date] = Field(default=None)
    source_name: Optional[str] = Field(default=None, max_length=100)
    source_version: Optional[str] = Field(default=None, max_length=50)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class AdministrativeHierarchy(SQLModel, table=True):
    """Quan hệ phân cấp giữa các đơn vị hành chính theo hệ cũ/mới."""

    __tablename__ = "administrative_hierarchies"

    id: Optional[int] = Field(default=None, primary_key=True)
    # old | new
    system_type: str = Field(max_length=20)
    parent_unit_id: int = Field(foreign_key="administrative_units.id")
    child_unit_id: int = Field(foreign_key="administrative_units.id")
    # 1=tỉnh, 2=quận (hệ cũ), 3=xã; hoặc 1=tỉnh, 2=xã (hệ mới)
    level_depth: int = Field(
        sa_column=Column(sa.SmallInteger(), nullable=False)
    )
    effective_from: Optional[date] = Field(default=None)
    effective_to: Optional[date] = Field(default=None)
    is_active: bool = Field(default=True)


class AdministrativeImportBatch(SQLModel, table=True):
    """Lịch sử một lần import dữ liệu hành chính."""

    __tablename__ = "administrative_import_batches"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_name: str = Field(max_length=100)
    source_version: str = Field(max_length=50)
    file_name: Optional[str] = Field(default=None, max_length=255)
    imported_by: Optional[int] = Field(default=None, foreign_key="users.id")
    imported_at: datetime = Field(default_factory=_utcnow)
    # draft | success | failed
    status: str = Field(default="draft", max_length=20)
    total_rows: int = Field(default=0)
    success_rows: int = Field(default=0)
    failed_rows: int = Field(default=0)
    error_summary: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))


class AdministrativeImportError(SQLModel, table=True):
    """Chi tiết lỗi từng dòng trong một batch import."""

    __tablename__ = "administrative_import_errors"

    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: int = Field(foreign_key="administrative_import_batches.id")
    row_no: Optional[int] = Field(default=None)
    raw_payload: Optional[dict] = Field(
        default=None,
        sa_column=Column(sa.dialects.postgresql.JSONB, nullable=True),
    )
    error_message: Optional[str] = Field(
        default=None, sa_column=Column(sa.Text(), nullable=True)
    )


class EducationLevel(SQLModel, table=True):
    """Danh mục trình độ học vấn chuẩn hóa."""

    __tablename__ = "education_levels"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    rank_no: int = Field(sa_column=Column(sa.Integer(), nullable=False, unique=True, index=True))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class EducationalInstitution(SQLModel, table=True):
    """Danh mục trường học / cơ sở đào tạo."""

    __tablename__ = "educational_institutions"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: Optional[str] = Field(default=None, max_length=50, unique=True, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    short_name: Optional[str] = Field(default=None, max_length=100)
    institution_type: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.String(50), nullable=True, index=True),
    )
    country_code: Optional[str] = Field(default=None, max_length=10)
    province_code: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class EducationMajor(SQLModel, table=True):
    """Danh mục chuyên ngành học vấn."""

    __tablename__ = "education_majors"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: Optional[str] = Field(default=None, max_length=50, unique=True, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    major_group: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.String(100), nullable=True, index=True),
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class ContractCategory(SQLModel, table=True):
    """Danh mục loại hợp đồng / nhóm phụ lục hợp đồng."""

    __tablename__ = "contract_categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    document_kind: str = Field(
        sa_column=Column(sa.String(30), nullable=False, index=True)
    )
    legal_contract_type: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.String(30), nullable=True, index=True),
    )
    business_group: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.String(50), nullable=True, index=True),
    )
    default_term_months: Optional[int] = Field(default=None)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class Nationality(SQLModel, table=True):
    """Danh mục quốc tịch."""

    __tablename__ = "nationalities"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=20, unique=True, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    iso2_code: Optional[str] = Field(default=None, max_length=2, index=True)
    iso3_code: Optional[str] = Field(default=None, max_length=3, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class Ethnicity(SQLModel, table=True):
    """Danh mục dân tộc."""

    __tablename__ = "ethnicities"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=20, unique=True, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class Religion(SQLModel, table=True):
    """Danh mục tôn giáo."""

    __tablename__ = "religions"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=20, unique=True, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class Bank(SQLModel, table=True):
    """Danh mục ngân hàng."""

    __tablename__ = "banks"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=30, unique=True, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    short_name: Optional[str] = Field(default=None, max_length=100, index=True)
    bin_code: Optional[str] = Field(default=None, max_length=20, index=True)
    swift_code: Optional[str] = Field(default=None, max_length=20, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class Skill(SQLModel, table=True):
    """Danh mục kỹ năng."""

    __tablename__ = "skills"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    skill_group: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.String(100), nullable=True, index=True),
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class Certificate(SQLModel, table=True):
    """Danh mục chứng chỉ."""

    __tablename__ = "certificates"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    certificate_group: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.String(100), nullable=True, index=True),
    )
    issuer_name: Optional[str] = Field(default=None, max_length=255)
    expiry_policy: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.String(30), nullable=True, index=True),
    )
    default_valid_months: Optional[int] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class LeaveType(SQLModel, table=True):
    """Danh mục loại nghỉ phép."""

    __tablename__ = "leave_types"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    is_paid_leave: bool = Field(default=False)
    affects_annual_leave: bool = Field(default=False)
    allow_half_day: bool = Field(default=False)
    requires_attachment: bool = Field(default=False)
    color_tag: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    count_public_holidays:  bool          = Field(default=True)
    max_days_per_year:      Optional[int] = Field(default=None)
    max_consecutive_days:   Optional[int] = Field(default=None)
    min_advance_days:       int           = Field(default=0)
    carryover_allowed:      bool          = Field(default=False)
    carryover_cutoff_month: int           = Field(default=3)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class ContractTemplate(SQLModel, table=True):
    """Mẫu hợp đồng lao động / phụ lục hợp đồng."""

    __tablename__ = "contract_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=50, index=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255, index=True)
    contract_category_id: int = Field(foreign_key="contract_categories.id")
    document_kind: str = Field(
        sa_column=Column(sa.String(30), nullable=False, index=True)
    )
    template_engine: str = Field(
        default="docx_placeholders",
        sa_column=Column(sa.String(30), nullable=False, server_default="docx_placeholders"),
    )
    file_name: str = Field(max_length=255)
    storage_path: Optional[str] = Field(default=None, max_length=500)
    mime_type: str = Field(max_length=100)
    file_size: Optional[int] = Field(default=None)
    file_checksum: Optional[str] = Field(default=None, max_length=128)
    version_no: int = Field(
        default=1,
        sa_column=Column(sa.Integer(), nullable=False, server_default="1"),
    )
    effective_from: Optional[date] = Field(default=None)
    effective_to: Optional[date] = Field(default=None)
    is_active: bool = Field(default=True)
    note: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class ContractTemplatePlaceholder(SQLModel, table=True):
    """Placeholder cho mẫu hợp đồng / phụ lục hợp đồng."""

    __tablename__ = "contract_template_placeholders"

    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="contract_templates.id")
    placeholder_key: str = Field(max_length=100)
    label: str = Field(max_length=255)
    source_scope: str = Field(
        sa_column=Column(sa.String(50), nullable=False, index=True)
    )
    source_path: str = Field(max_length=255)
    data_type: str = Field(
        sa_column=Column(sa.String(30), nullable=False, index=True)
    )
    formatter: Optional[str] = Field(default=None, max_length=50)
    is_required: bool = Field(default=False)
    default_value: Optional[str] = Field(default=None, max_length=255)
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)
