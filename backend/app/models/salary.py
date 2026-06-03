from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Field, SQLModel, Column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RegionalMinimumWage(SQLModel, table=True):
    """
    Lịch sử mức lương tối thiểu vùng theo từng nghị định của Chính phủ.
    Dùng để tính lương BHXH theo công thức: Lương BHXH = LTTV × hệ_số_bậc.
    """

    __tablename__ = "regional_minimum_wages"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Số hiệu nghị định, VD: "293/2025/NĐ-CP"
    decree_number: str = Field(max_length=50)
    # Vùng lương: 1=Vùng I (HN/HCM), 2=Vùng II, 3=Vùng III, 4=Vùng IV (vùng sâu xa)
    region: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    # Mức lương tối thiểu tháng (VNĐ), VD: 4140000
    amount: int = Field(sa_column=Column(sa.Numeric(15, 0), nullable=False))
    # Ngày bắt đầu có hiệu lực
    effective_from: date = Field(sa_column=Column(sa.Date(), nullable=False))
    # Ngày kết thúc hiệu lực — NULL nghĩa là đang áp dụng
    effective_to: Optional[date] = Field(
        default=None,
        sa_column=Column(sa.Date(), nullable=True),
    )
    note: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )


class CompanyBhxhRegion(SQLModel, table=True):
    """
    Vùng BHXH của công ty theo từng thời kỳ.
    Khi công ty chuyển địa điểm sang vùng khác, thêm dòng mới (không sửa cũ).
    """

    __tablename__ = "company_bhxh_region"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Vùng lương đang áp dụng: 1 | 2 | 3 | 4
    region: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    # Ngày bắt đầu áp dụng vùng này
    effective_from: date = Field(sa_column=Column(sa.Date(), nullable=False))
    # NULL = đang áp dụng hiện tại
    effective_to: Optional[date] = Field(
        default=None,
        sa_column=Column(sa.Date(), nullable=True),
    )
    # Ghi chú, VD: "Đang áp dụng — trụ sở tại tỉnh Đắk Lắk"
    note: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )


class SalaryScale(SQLModel, table=True):
    """
    Phiên bản thang bảng lương của công ty (thường cập nhật theo năm).
    Mỗi phiên bản chứa nhiều dòng hệ số theo chức danh + bậc.
    """

    __tablename__ = "salary_scales"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Tên phiên bản, VD: "Thang bảng lương 2026"
    name: str = Field(max_length=200)
    # Ngày bắt đầu áp dụng thang lương này
    effective_from: date = Field(sa_column=Column(sa.Date(), nullable=False))
    # NULL = đang áp dụng
    effective_to: Optional[date] = Field(
        default=None,
        sa_column=Column(sa.Date(), nullable=True),
    )
    note: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)


class SalaryScaleEntry(SQLModel, table=True):
    """
    Hệ số bậc lương theo từng chức danh trong một phiên bản thang bảng lương.
    Lương bậc N = LTTV_vùng × coefficient.
    Ví dụ: Chủ tịch HĐQT Bậc 1 → coefficient=2.68 → 4.140.000 × 2.68 = 11.095.200 ₫.
    """

    __tablename__ = "salary_scale_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    salary_scale_id: int = Field(foreign_key="salary_scales.id")
    job_title_id: int = Field(foreign_key="job_titles.id")
    # Số thứ tự bậc lương, bắt đầu từ 1
    grade_no: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    # Hệ số nhân với LTTV vùng để ra mức lương bậc này
    coefficient: float = Field(
        sa_column=Column(sa.Numeric(6, 4), nullable=False)
    )
    # Số tháng tối thiểu trước khi được xét nâng lên bậc tiếp theo (thường 12)
    promotion_months: int = Field(
        default=12,
        sa_column=Column(sa.SmallInteger(), nullable=False, server_default="12"),
    )
    # Điều kiện để đạt bậc này (yêu cầu theo pháp lý về thang bảng lương)
    criteria: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )


class BhxhSenioritySetting(SQLModel, table=True):
    """
    Rule thâm niên dùng chung của công ty để xét tăng bậc BHXH.
    Phase 1 chỉ cần một rule active, nhưng vẫn lưu lịch sử theo effective date.
    """

    __tablename__ = "bhxh_seniority_settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    raise_month: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    raise_day: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    years_per_grade: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    first_year_cutoff_month: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    first_year_cutoff_day: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    effective_from: date = Field(sa_column=Column(sa.Date(), nullable=False))
    effective_to: Optional[date] = Field(
        default=None,
        sa_column=Column(sa.Date(), nullable=True),
    )
    note: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)
