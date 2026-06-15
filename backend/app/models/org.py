from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, Column

from app.models.mixins import SoftDeleteMixin


def _utcnow() -> datetime:
    # Trả về naive UTC — SQLModel map datetime → TIMESTAMP WITHOUT TIME ZONE
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Department(SoftDeleteMixin, SQLModel, table=True):
    """Phòng / Ban / Bộ phận / Nhóm / Tổ — cây phân cấp tùy độ sâu."""

    __tablename__ = "departments"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=20, unique=True, index=True)
    name: str = Field(max_length=200)
    short_name: Optional[str] = Field(default=None, max_length=50)
    # NULL = đơn vị cấp gốc (không có cha)
    parent_id: Optional[int] = Field(default=None, foreign_key="departments.id")
    # PHONG | BAN | BO_PHAN | NHOM | TO
    dept_type: str = Field(default="PHONG", max_length=20)
    order_no: int = Field(default=0)
    # Tiền tố ngắn dùng để tạo mã hiển thị nhân viên: "HC" → "HC0011", "KH" → "KH2278".
    # Nullable: phòng ban chưa đặt prefix thì mã nhân viên hiển thị thuần số.
    display_prefix: Optional[str] = Field(default=None, max_length=5)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class JobTitle(SoftDeleteMixin, SQLModel, table=True):
    """Chức danh (Director, Manager, Staff, ...) — dùng trong thang bảng lương."""

    __tablename__ = "job_titles"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=20, unique=True, index=True)
    name: str = Field(max_length=200)
    # Cấp bậc quản lý: 1 = cao nhất (Giám đốc), càng lớn càng thấp
    level: int = Field(default=1, sa_column=Column(sa.SmallInteger(), nullable=False, server_default="1"))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class JobPosition(SoftDeleteMixin, SQLModel, table=True):
    """Vị trí công việc — gắn với một phòng/ban và một chức danh."""

    __tablename__ = "job_positions"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=20, unique=True, index=True)
    name: str = Field(max_length=200)
    department_id: int = Field(foreign_key="departments.id")
    # Chức danh, có thể để trống (null) khi vị trí chưa xác định chức danh
    job_title_id: Optional[int] = Field(default=None, foreign_key="job_titles.id")
    # Bậc lương mặc định khi tuyển nhân viên mới vào vị trí này
    default_grade: int = Field(
        default=1,
        sa_column=Column(sa.SmallInteger(), nullable=False, server_default="1"),
    )
    # Phụ cấp cố định GHI TRONG HỢP ĐỒNG, được tính vào lương đóng BHXH
    # (phụ cấp chức vụ, trách nhiệm, nặng nhọc/độc hại...)
    bhxh_allowance: int = Field(
        default=0,
        sa_column=Column(sa.Numeric(15, 0), nullable=False, server_default="0"),
    )
    # Phụ cấp KHÔNG tính BHXH, phải tách thành dòng riêng trong hợp đồng
    # (ăn ca, xăng xe, điện thoại, nhà ở...)
    non_bhxh_allowance: int = Field(
        default=0,
        sa_column=Column(sa.Numeric(15, 0), nullable=False, server_default="0"),
    )
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    requirements: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    # Nhóm pháp lý thử việc theo Điều 25 BLLĐ 2019.
    # enterprise_manager | college_plus | intermediate_technical_clerical | other
    probation_legal_group: Optional[str] = Field(default=None, max_length=50, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class JobPositionAttachment(SQLModel, table=True):
    """File đính kèm tiêu chuẩn tuyển dụng của vị trí công việc."""

    __tablename__ = "job_position_attachments"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_position_id: int = Field(foreign_key="job_positions.id")
    file_name: str = Field(max_length=255)
    # Đường dẫn tương đối tính từ thư mục storage, VD: "positions/42/jd.pdf"
    file_path: str = Field(max_length=500)
    file_size: Optional[int] = Field(default=None)
    uploaded_at: datetime = Field(default_factory=_utcnow)


class DepartmentHead(SQLModel, table=True):
    """Người đứng đầu đơn vị theo từng giai đoạn hiệu lực.

    Một employee có thể đồng thời phụ trách nhiều đơn vị.
    Mỗi department chỉ có tối đa 1 dòng is_current = TRUE.
    """

    __tablename__ = "department_heads"

    id: Optional[int] = Field(default=None, primary_key=True)
    department_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("departments.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    head_role_label: Optional[str] = Field(default=None, max_length=100)
    effective_from: date = Field()
    effective_to: Optional[date] = Field(default=None)
    is_current: bool = Field(default=True)
    changed_by: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        sa.Index(
            "uq_department_head_current",
            "department_id",
            unique=True,
            postgresql_where=sa.text("is_current = TRUE"),
        ),
    )


class OrgChangeLog(SQLModel, table=True):
    """Lịch sử thay đổi cơ cấu tổ chức — ghi khi tạo/sửa/xóa phòng ban, vị trí."""

    __tablename__ = "org_change_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    # 'department' | 'job_title' | 'job_position'
    entity_type: str = Field(max_length=30)
    entity_id: int = Field()
    entity_name: str = Field(max_length=200)
    # 'create' | 'update' | 'delete'
    action: str = Field(max_length=10)
    # ID người thực hiện — sẽ có FK → users.id sau khi Auth Foundation được implement
    changed_by: Optional[int] = Field(default=None)
    changed_at: datetime = Field(default_factory=_utcnow)
    # Snapshot dữ liệu trước khi thay đổi (NULL với action='create')
    old_data: Optional[Any] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    # Snapshot dữ liệu sau khi thay đổi (NULL với action='delete')
    new_data: Optional[Any] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
