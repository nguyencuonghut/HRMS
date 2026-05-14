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
