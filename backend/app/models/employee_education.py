from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel, UniqueConstraint


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmployeeEducationHistory(SQLModel, table=True):
    """Quá trình học vấn của nhân viên."""

    __tablename__ = "employee_education_histories"

    id: Optional[int] = Field(default=None, primary_key=True)

    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # Dual-field: FK danh mục hoặc nhập tự do
    institution_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("educational_institutions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    institution_name: Optional[str] = Field(default=None, max_length=255)
    major_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("education_majors.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    major_name: Optional[str] = Field(default=None, max_length=255)
    education_level_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("education_levels.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )

    graduation_year: Optional[int] = Field(default=None, sa_column=Column(sa.SmallInteger(), nullable=True))
    diploma_type: Optional[str] = Field(default=None, max_length=100)
    is_main_education: bool = Field(default=False)
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class EmployeeWorkExperience(SQLModel, table=True):
    """Kinh nghiệm làm việc trước của nhân viên."""

    __tablename__ = "employee_work_experiences"

    id: Optional[int] = Field(default=None, primary_key=True)

    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    company_name: str = Field(max_length=255)
    position_name: Optional[str] = Field(default=None, max_length=255)
    start_date: date
    end_date: Optional[date] = Field(default=None)
    description: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class EmployeeSkill(SQLModel, table=True):
    """Kỹ năng của nhân viên — liên kết catalog skills."""

    __tablename__ = "employee_skills"
    __table_args__ = (UniqueConstraint("employee_id", "skill_id", name="uq_employee_skills"),)

    id: Optional[int] = Field(default=None, primary_key=True)

    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    skill_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("skills.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )

    # beginner | intermediate | advanced | expert
    proficiency_level: str = Field(max_length=20)
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class EmployeeCertificate(SQLModel, table=True):
    """Chứng chỉ của nhân viên — liên kết catalog certificates."""

    __tablename__ = "employee_certificates"

    id: Optional[int] = Field(default=None, primary_key=True)

    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    certificate_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("certificates.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )

    certificate_number: Optional[str] = Field(default=None, max_length=100)
    issued_date: Optional[date] = Field(default=None)
    expires_on: Optional[date] = Field(default=None)
    issued_by: Optional[str] = Field(default=None, max_length=255)
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class EmployeeLanguage(SQLModel, table=True):
    """Ngoại ngữ của nhân viên — theo khung CEFR."""

    __tablename__ = "employee_languages"
    __table_args__ = (UniqueConstraint("employee_id", "language_name", name="uq_employee_languages"),)

    id: Optional[int] = Field(default=None, primary_key=True)

    employee_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    language_name: str = Field(max_length=100)
    # native | A1 | A2 | B1 | B2 | C1 | C2
    proficiency_level: str = Field(max_length=10)
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = Field(default=None)
