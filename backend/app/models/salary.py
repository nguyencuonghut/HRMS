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

    __table_args__ = (
        sa.Index(
            "ix_regional_minimum_wages_lookup",
            "region",
            "effective_from",
            unique=True,
        ),
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


class BhxhPositionGroup(SQLModel, table=True):
    """
    Nhóm vị trí BHXH của công ty.
    Dùng để gom nhiều job_position vào một nhóm "vị trí tương đương" theo bảng HR.
    """

    __tablename__ = "bhxh_position_groups"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=255)
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class BhxhPositionGroupMember(SQLModel, table=True):
    """
    Mapping một vị trí công việc vào đúng một nhóm vị trí BHXH.
    """

    __tablename__ = "bhxh_position_group_members"

    id: Optional[int] = Field(default=None, primary_key=True)
    bhxh_position_group_id: int = Field(foreign_key="bhxh_position_groups.id")
    job_position_id: int = Field(foreign_key="job_positions.id", unique=True)
    note: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class SalaryScaleEntry(SQLModel, table=True):
    """
    Hệ số bậc lương theo từng nhóm vị trí BHXH trong một phiên bản thang bảng lương.
    `job_title_id` được giữ nullable để tương thích dữ liệu legacy cũ chưa migrate sạch.
    Lương bậc N = LTTV_vùng × coefficient.
    Ví dụ: Nhóm Giám đốc công ty Bậc 1 → coefficient=2.68 → 4.140.000 × 2.68 = 11.095.200 ₫.
    """

    __tablename__ = "salary_scale_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    salary_scale_id: int = Field(foreign_key="salary_scales.id")
    job_title_id: Optional[int] = Field(default=None, foreign_key="job_titles.id")
    bhxh_position_group_id: Optional[int] = Field(default=None, foreign_key="bhxh_position_groups.id")
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


class RetirementAgePolicy(SQLModel, table=True):
    """
    Cấu hình lộ trình tuổi nghỉ hưu áp dụng cho báo cáo lao động cao tuổi.

    Thiết kế theo version hiệu lực:
    - mỗi policy có `effective_from` / `effective_to`
    - bảng con lưu ngưỡng tuổi nghỉ hưu theo giới tính + năm áp dụng
    - khi pháp luật đổi lộ trình, chỉ cần tạo policy mới và nhập lại các ngưỡng
    """

    __tablename__ = "retirement_age_policies"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    legal_basis_summary: Optional[str] = Field(
        default=None,
        sa_column=Column(sa.Text(), nullable=True),
    )
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


class RetirementAgePolicyThreshold(SQLModel, table=True):
    """Ngưỡng tuổi nghỉ hưu theo giới tính và năm báo cáo."""

    __tablename__ = "retirement_age_policy_thresholds"

    id: Optional[int] = Field(default=None, primary_key=True)
    policy_id: int = Field(foreign_key="retirement_age_policies.id")
    gender: str = Field(max_length=10)
    applicable_year: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    age_years: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    age_months: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))

    __table_args__ = (
        sa.UniqueConstraint(
            "policy_id",
            "gender",
            "applicable_year",
            name="uq_retirement_age_policy_thresholds",
        ),
        sa.Index(
            "ix_retirement_age_policy_thresholds_lookup",
            "policy_id",
            "gender",
            "applicable_year",
        ),
    )
