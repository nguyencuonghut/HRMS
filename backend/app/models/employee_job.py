from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmployeeJobRecord(SQLModel, table=True):
    """Bản ghi công việc của nhân viên — phòng ban, chức danh, vị trí, mốc thời gian.

    Thiết kế lịch sử bất biến:
    - is_current=True: bản ghi hiện hành duy nhất (partial unique index).
    - Khi chuyển công tác: set is_current=False + effective_to trên bản cũ,
      tạo bản ghi mới với is_current=True.
    - Dùng POST .../transfer để chuyển công tác; PUT .../current chỉ để sửa ghi nhầm.
    """

    __tablename__ = "employee_job_records"

    id: Optional[int] = Field(default=None, primary_key=True)

    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # ── Đơn vị tổ chức ───────────────────────────────────────────────────
    department_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("departments.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    # Nullable: vị trí chưa xác định chức danh
    job_title_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("job_titles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Nullable: có thể gán phòng ban mà không cần xác định vị trí cụ thể
    job_position_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("job_positions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── Mốc thời gian nhân sự ────────────────────────────────────────────
    probation_start_date: Optional[date] = Field(default=None)
    probation_end_date: Optional[date] = Field(default=None)   # ngày kế hoạch kết thúc thử việc
    official_date: Optional[date] = Field(default=None)        # ngày thực tế chính thức

    # ── Hiệu lực bản ghi ─────────────────────────────────────────────────
    effective_from: date   # ngày bắt đầu hiệu lực
    effective_to: Optional[date] = Field(default=None)   # NULL = đang hiệu lực
    # Partial unique index trên DB đảm bảo tối đa 1 bản ghi is_current=TRUE per employee.
    is_current: bool = Field(default=True)

    # ── Ghi chú & Audit ──────────────────────────────────────────────────
    notes: Optional[str] = Field(
        default=None, sa_column=Column(sa.Text(), nullable=True)
    )
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
        # Partial unique index: mỗi nhân viên tối đa 1 bản ghi is_current=TRUE.
        # Không dùng application-level check vì race condition có thể tạo 2 bản ghi đồng thời.
        sa.Index(
            "uq_job_record_current",
            "employee_id",
            unique=True,
            postgresql_where=sa.text("is_current = TRUE"),
        ),
    )
