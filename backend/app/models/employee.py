from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel

from app.core.encryption import EncryptedString


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Employee(SQLModel, table=True):
    """Hồ sơ nhân viên — thông tin cá nhân cơ bản (3.1).

    Thông tin công việc (phòng ban, chức danh) sẽ ở bảng employee_job_records (3.2).
    """

    __tablename__ = "employees"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Mã số nhân viên: số nguyên thuần, tăng độc lập theo từng hệ mã nhân viên.
    employee_seq: int = Field(
        sa_column=Column(sa.Integer(), nullable=False, index=True)
    )
    employee_code_sequence_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employee_code_sequences.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )

    # ── Họ tên ──────────────────────────────────────────────────────────────
    full_name: str = Field(max_length=200)
    # unaccented lowercase — dùng để full-text search
    normalized_name: str = Field(
        sa_column=Column(sa.String(200), nullable=False, index=True)
    )
    last_name: str = Field(max_length=100)
    first_name: str = Field(max_length=100)

    # ── Thông tin cá nhân cơ bản ─────────────────────────────────────────
    date_of_birth: date
    # male | female | other
    gender: str = Field(max_length=10)
    nationality_id: int = Field(foreign_key="nationalities.id")
    ethnicity_id: Optional[int] = Field(default=None, foreign_key="ethnicities.id")
    religion_id: Optional[int] = Field(default=None, foreign_key="religions.id")

    # ── Giấy tờ nhận dạng (CCCD/CMND) ───────────────────────────────────
    id_number: str = Field(
        sa_column=Column(EncryptedString(), nullable=False)
    )
    id_number_hash: str = Field(
        sa_column=Column(sa.String(64), nullable=False, unique=True, index=True)
    )
    id_issued_on: date
    id_issued_by: str = Field(max_length=200)
    # Nullable: CCCD cấp trước 2021 không có ngày hết hạn
    id_expires_on: Optional[date] = Field(default=None)

    # ── Hộ chiếu (nullable — chủ yếu người nước ngoài) ──────────────────
    passport_number: Optional[str] = Field(
        default=None,
        max_length=50,
        sa_column=Column(EncryptedString(), nullable=True),
    )
    passport_issued_on: Optional[date] = Field(default=None)
    passport_expires_on: Optional[date] = Field(default=None)

    # ── Giấy phép lao động (nullable — chỉ người nước ngoài) ────────────
    work_permit_number: Optional[str] = Field(default=None, max_length=50)
    work_permit_issued_on: Optional[date] = Field(default=None)
    work_permit_expires_on: Optional[date] = Field(default=None)

    # ── Liên lạc & thuế ─────────────────────────────────────────────────
    phone_number: Optional[str] = Field(default=None, max_length=20)
    personal_email: Optional[str] = Field(default=None, max_length=200)
    personal_tax_code: Optional[str] = Field(
        default=None,
        max_length=20,
        sa_column=Column(EncryptedString(), nullable=True),
    )
    bhxh_code: Optional[str] = Field(default=None, max_length=20)

    # ── Ảnh thẻ nhân viên ────────────────────────────────────────────────
    avatar_path: Optional[str] = Field(default=None, max_length=500)

    # ── Trạng thái nhân sự ───────────────────────────────────────────────
    # probation | official | long_leave | resigned
    status: str = Field(default="probation", max_length=20)
    start_date: date
    resigned_date: Optional[date] = Field(default=None)
    resigned_reason_type: Optional[str] = Field(default=None, max_length=50)
    resigned_reason_note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    # ── Liên kết tài khoản hệ thống (1-1, nullable) ──────────────────────
    # Không thêm FK ở đây để tránh circular dependency (users ↔ employees).
    # Quan hệ ngược employees.user_id → users.id đã đủ.
    user_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            unique=True,
            nullable=True,
        ),
    )

    # ── Audit ────────────────────────────────────────────────────────────
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        sa.UniqueConstraint(
            "employee_code_sequence_id",
            "employee_seq",
            name="uq_employees_sequence_seq",
        ),
    )


class EmployeeAddress(SQLModel, table=True):
    """Địa chỉ nhân viên — lưu song song hệ cũ và hệ mới.

    address_type: permanent = hộ khẩu thường trú, contact = địa chỉ liên lạc.
    Mỗi nhân viên có tối đa 1 hàng cho mỗi type (UNIQUE constraint).
    """

    __tablename__ = "employee_addresses"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    # permanent | contact
    address_type: str = Field(max_length=20)

    # ── Địa chỉ hệ mới (QĐ 19/2025) ────────────────────────────────────
    new_province_unit_id: Optional[int] = Field(
        default=None, foreign_key="administrative_units.id"
    )
    new_district_unit_id: Optional[int] = Field(
        default=None, foreign_key="administrative_units.id"
    )
    new_ward_unit_id: Optional[int] = Field(
        default=None, foreign_key="administrative_units.id"
    )
    new_address_line: Optional[str] = Field(default=None, max_length=500)

    # ── Địa chỉ hệ cũ (legacy 3 cấp trước 2025) ────────────────────────
    old_province_unit_id: Optional[int] = Field(
        default=None, foreign_key="administrative_units.id"
    )
    old_district_unit_id: Optional[int] = Field(
        default=None, foreign_key="administrative_units.id"
    )
    old_ward_unit_id: Optional[int] = Field(
        default=None, foreign_key="administrative_units.id"
    )
    old_address_line: Optional[str] = Field(default=None, max_length=500)

    # Địa chỉ đầy đủ dạng text — denormalized để hiển thị nhanh
    full_address_text: Optional[str] = Field(default=None, max_length=1000)

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        sa.UniqueConstraint("employee_id", "address_type", name="uq_employee_address_type"),
    )


class EmployeeBankAccount(SQLModel, table=True):
    """Tài khoản ngân hàng của nhân viên.

    Một nhân viên có thể có nhiều tài khoản; đúng một tài khoản mang is_primary=True
    được dùng để nhận lương.
    """

    __tablename__ = "employee_bank_accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    bank_id: int = Field(foreign_key="banks.id")
    account_number: str = Field(
        max_length=50,
        sa_column=Column(EncryptedString(), nullable=False),
    )
    # Tên chủ tài khoản — thường giống full_name nhưng cho phép khác
    account_name: str = Field(max_length=200)
    branch_name: Optional[str] = Field(default=None, max_length=200)
    is_primary: bool = Field(default=False)
    is_active: bool = Field(default=True)
    note: Optional[str] = Field(
        default=None, sa_column=Column(sa.Text(), nullable=True)
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)
