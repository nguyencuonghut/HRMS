"""Models tuyển dụng ATS (13.1 — Kế hoạch & Yêu cầu tuyển dụng / 13.2 — Đăng tin / 13.3 — Ứng viên)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY as PgARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class HeadcountPlan(SQLModel, table=True):
    """Kế hoạch nhân sự theo năm / phòng ban / vị trí (tùy chọn)."""

    __tablename__ = "headcount_plans"

    id: Optional[int] = Field(default=None, primary_key=True)
    year: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    department_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
    )
    job_position_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("job_positions.id", ondelete="SET NULL"), nullable=True),
    )
    current_count: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False, server_default="0"))
    planned_count: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    reason: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint("year", "department_id", "job_position_id", name="uq_headcount_plan_year_dept_pos"),
        sa.Index("ix_headcount_plans_year", "year"),
        sa.Index("ix_headcount_plans_department_id", "department_id"),
    )


class JobRequisition(SQLModel, table=True):
    """Yêu cầu tuyển dụng (JR) — nền tảng của toàn bộ ATS."""

    __tablename__ = "job_requisitions"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(sa_column=Column(sa.String(30), nullable=False, unique=True))
    job_position_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("job_positions.id", ondelete="RESTRICT"), nullable=False)
    )
    department_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    )
    headcount_plan_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("headcount_plans.id", ondelete="SET NULL"), nullable=True),
    )

    quantity: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False, server_default="1"))
    # Số lượng còn cần tuyển (giảm dần khi hiring_decision.convert_to_employee chạy)
    quantity_remaining: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False, server_default="1"))
    reason_type: str = Field(sa_column=Column(sa.String(20), nullable=False))
    # new | replacement | expansion

    deadline: Optional[datetime] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    salary_min: Optional[Decimal] = Field(
        default=None, sa_column=Column(sa.Numeric(15, 2), nullable=True)
    )
    salary_max: Optional[Decimal] = Field(
        default=None, sa_column=Column(sa.Numeric(15, 2), nullable=True)
    )

    # JD override — None = kế thừa từ job_position.description/requirements
    jd_description: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    jd_requirements: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    status: str = Field(sa_column=Column(sa.String(20), nullable=False, server_default="draft"))
    # draft | pending_review | approved | in_progress | completed | cancelled

    submitted_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    submitted_at: Optional[datetime] = Field(default=None, sa_column=Column(sa.DateTime(), nullable=True))

    approved_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    approved_at: Optional[datetime] = Field(default=None, sa_column=Column(sa.DateTime(), nullable=True))

    rejection_note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    internal_note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))

    created_by_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.Index("ix_jr_department_id", "department_id"),
        sa.Index("ix_jr_job_position_id", "job_position_id"),
        sa.Index("ix_jr_status", "status"),
        sa.Index("ix_jr_code", "code"),
    )


class RecruitmentBudgetItem(SQLModel, table=True):
    """Khoản chi phí tuyển dụng dự toán/thực tế cho một JR."""

    __tablename__ = "recruitment_budget_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_requisition_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("job_requisitions.id", ondelete="CASCADE"), nullable=False)
    )
    item_name: str = Field(sa_column=Column(sa.String(200), nullable=False))
    estimated_amount: Optional[Decimal] = Field(
        default=None, sa_column=Column(sa.Numeric(15, 2), nullable=True)
    )
    actual_amount: Optional[Decimal] = Field(
        default=None, sa_column=Column(sa.Numeric(15, 2), nullable=True)
    )
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.Index("ix_budget_items_jr_id", "job_requisition_id"),
    )


# ── Recruitment Channel (13.2) ────────────────────────────────────────────────


class RecruitmentChannel(SQLModel, table=True):
    """Danh mục kênh tuyển dụng (TopCV, VietnamWorks, nội bộ…)."""

    __tablename__ = "recruitment_channels"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(sa_column=Column(sa.String(50), nullable=False, unique=True))
    name: str = Field(sa_column=Column(sa.String(200), nullable=False))
    is_active: bool = Field(sa_column=Column(sa.Boolean(), nullable=False, server_default="true"))
    sort_order: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False, server_default="0"))


# ── Job Posting (13.2) ────────────────────────────────────────────────────────


class JobPosting(SQLModel, table=True):
    """Tin tuyển dụng — tạo từ JR đã duyệt."""

    __tablename__ = "job_postings"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_requisition_id: int = Field(
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("job_requisitions.id", ondelete="RESTRICT"), nullable=False
        )
    )
    title: str = Field(sa_column=Column(sa.String(300), nullable=False))
    description: str = Field(sa_column=Column(sa.Text(), nullable=False))
    requirements: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    benefits: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    work_location: Optional[str] = Field(
        default=None, sa_column=Column(sa.String(300), nullable=True)
    )
    deadline: Optional[date] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    salary_display: Optional[str] = Field(
        default=None, sa_column=Column(sa.String(100), nullable=True)
    )
    posting_type: str = Field(
        sa_column=Column(sa.String(20), nullable=False, server_default="external")
    )
    # Mảng channel_id đã đăng
    channels: List[int] = Field(
        default_factory=list,
        sa_column=Column(PgARRAY(sa.Integer()), nullable=False, server_default="{}"),
    )
    status: str = Field(
        sa_column=Column(sa.String(20), nullable=False, server_default="draft")
    )
    # draft | active | closed | expired

    opened_at: Optional[datetime] = Field(default=None, sa_column=Column(sa.DateTime(), nullable=True))
    closed_at: Optional[datetime] = Field(default=None, sa_column=Column(sa.DateTime(), nullable=True))
    expires_at: Optional[datetime] = Field(default=None, sa_column=Column(sa.DateTime(), nullable=True))

    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id: int = Field(
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False
        )
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.Index("ix_job_postings_jr", "job_requisition_id"),
        sa.Index("ix_job_postings_status", "status"),
    )


# ── Candidates (13.3) ─────────────────────────────────────────────────────────


class Candidate(SQLModel, table=True):
    """Hồ sơ ứng viên — độc lập với bảng employees."""

    __tablename__ = "candidates"

    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str = Field(sa_column=Column(sa.String(200), nullable=False))
    last_name: Optional[str] = Field(default=None, sa_column=Column(sa.String(100), nullable=True))
    first_name: Optional[str] = Field(default=None, sa_column=Column(sa.String(100), nullable=True))
    date_of_birth: Optional[date] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    gender: Optional[str] = Field(default=None, sa_column=Column(sa.String(10), nullable=True))
    nationality_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("nationalities.id", ondelete="SET NULL"), nullable=True),
    )
    # Giữ lại dữ liệu text thô để import/backfill catalog, không dùng làm nguồn convert sang employee.
    raw_nationality_text: Optional[str] = Field(
        default=None,
        sa_column=Column("nationality", sa.String(100), nullable=True),
    )
    ethnicity_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("ethnicities.id", ondelete="SET NULL"), nullable=True),
    )
    religion_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("religions.id", ondelete="SET NULL"), nullable=True),
    )
    id_number: Optional[str] = Field(default=None, sa_column=Column(sa.String(30), nullable=True))
    id_issued_on: Optional[date] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    id_issued_by: Optional[str] = Field(default=None, sa_column=Column(sa.String(200), nullable=True))
    id_expires_on: Optional[date] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    passport_number: Optional[str] = Field(default=None, sa_column=Column(sa.String(50), nullable=True))
    passport_issued_on: Optional[date] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    passport_expires_on: Optional[date] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    work_permit_number: Optional[str] = Field(default=None, sa_column=Column(sa.String(50), nullable=True))
    work_permit_issued_on: Optional[date] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    work_permit_expires_on: Optional[date] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    phone_number: Optional[str] = Field(default=None, sa_column=Column(sa.String(20), nullable=True))
    personal_email: Optional[str] = Field(default=None, sa_column=Column(sa.String(200), nullable=True))
    personal_tax_code: Optional[str] = Field(default=None, sa_column=Column(sa.String(20), nullable=True))
    bhxh_code: Optional[str] = Field(default=None, sa_column=Column(sa.String(20), nullable=True))
    address: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    current_company: Optional[str] = Field(default=None, sa_column=Column(sa.String(200), nullable=True))
    current_position: Optional[str] = Field(default=None, sa_column=Column(sa.String(200), nullable=True))
    expected_salary: Optional[Decimal] = Field(
        default=None, sa_column=Column(sa.Numeric(15, 2), nullable=True)
    )
    source_channel_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("recruitment_channels.id", ondelete="SET NULL"), nullable=True
        ),
    )
    source_note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    internal_note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(PgARRAY(sa.Text()), nullable=False, server_default="{}"),
    )
    is_active: bool = Field(sa_column=Column(sa.Boolean(), nullable=False, server_default="true"))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.Index("ix_candidates_personal_email", "personal_email"),
    )


class CandidateEducation(SQLModel, table=True):
    __tablename__ = "candidate_educations"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    )
    institution_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("educational_institutions.id", ondelete="SET NULL"), nullable=True
        ),
    )
    institution_name: Optional[str] = Field(default=None, sa_column=Column(sa.String(300), nullable=True))
    major_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("education_majors.id", ondelete="SET NULL"), nullable=True),
    )
    major_name: Optional[str] = Field(default=None, sa_column=Column(sa.String(300), nullable=True))
    education_level_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("education_levels.id", ondelete="SET NULL"), nullable=True
        ),
    )
    graduation_year: Optional[int] = Field(
        default=None, sa_column=Column(sa.SmallInteger(), nullable=True)
    )
    diploma_type: Optional[str] = Field(default=None, sa_column=Column(sa.String(100), nullable=True))
    is_main_education: bool = Field(sa_column=Column(sa.Boolean(), nullable=False, server_default="false"))
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))


class CandidateWorkExperience(SQLModel, table=True):
    __tablename__ = "candidate_work_experiences"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    )
    company_name: str = Field(sa_column=Column(sa.String(300), nullable=False))
    position_name: Optional[str] = Field(default=None, sa_column=Column(sa.String(200), nullable=True))
    start_date: Optional[date] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    end_date: Optional[date] = Field(default=None, sa_column=Column(sa.Date(), nullable=True))
    description: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    sort_order: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False, server_default="0"))


class CandidateSkill(SQLModel, table=True):
    __tablename__ = "candidate_skills"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    )
    skill_name: str = Field(sa_column=Column(sa.String(200), nullable=False))
    proficiency_level: Optional[str] = Field(
        default=None, sa_column=Column(sa.String(20), nullable=True)
    )

    __table_args__ = (
        sa.UniqueConstraint("candidate_id", "skill_name", name="uq_candidate_skill"),
    )


class CandidateAttachment(SQLModel, table=True):
    __tablename__ = "candidate_attachments"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    )
    attachment_type: str = Field(sa_column=Column(sa.String(30), nullable=False))
    file_path: str = Field(sa_column=Column(sa.String(500), nullable=False))
    file_name: str = Field(sa_column=Column(sa.String(300), nullable=False))
    file_size: Optional[int] = Field(default=None, sa_column=Column(sa.Integer(), nullable=True))
    mime_type: Optional[str] = Field(default=None, sa_column=Column(sa.String(100), nullable=True))
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    uploaded_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )
    uploaded_at: datetime = Field(default_factory=_utcnow)


class CandidateApplication(SQLModel, table=True):
    __tablename__ = "candidate_applications"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("candidates.id", ondelete="RESTRICT"), nullable=False
        )
    )
    job_requisition_id: int = Field(
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("job_requisitions.id", ondelete="RESTRICT"), nullable=False
        )
    )
    applied_date: date = Field(
        sa_column=Column(sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE"))
    )
    source_channel_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("recruitment_channels.id", ondelete="SET NULL"), nullable=True
        ),
    )
    current_stage: str = Field(
        sa_column=Column(sa.String(50), nullable=False, server_default="new")
    )
    rejection_reason: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    internal_note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint("candidate_id", "job_requisition_id", name="uq_application_candidate_jr"),
        sa.Index("ix_applications_jr", "job_requisition_id"),
        sa.Index("ix_applications_stage", "current_stage"),
    )


class PipelineStageTemplate(SQLModel, table=True):
    __tablename__ = "pipeline_stage_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(sa.String(200), nullable=False))
    job_position_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("job_positions.id", ondelete="SET NULL"), nullable=True),
    )
    is_default: bool = Field(sa_column=Column(sa.Boolean(), nullable=False, server_default="false"))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.Index("ix_pipeline_stage_templates_job_position", "job_position_id"),
    )


class PipelineStageTemplateItem(SQLModel, table=True):
    __tablename__ = "pipeline_stage_template_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("pipeline_stage_templates.id", ondelete="CASCADE"), nullable=False
        )
    )
    stage_order: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    stage_name: str = Field(sa_column=Column(sa.String(100), nullable=False))
    stage_type: str = Field(sa_column=Column(sa.String(30), nullable=False))
    is_required: bool = Field(sa_column=Column(sa.Boolean(), nullable=False, server_default="true"))

    __table_args__ = (
        sa.UniqueConstraint("template_id", "stage_order", name="uq_pipeline_stage_template_order"),
        sa.UniqueConstraint("template_id", "stage_type", name="uq_pipeline_stage_template_type"),
    )


class PipelineStage(SQLModel, table=True):
    __tablename__ = "pipeline_stages"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_requisition_id: int = Field(
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("job_requisitions.id", ondelete="CASCADE"), nullable=False
        )
    )
    stage_order: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False))
    stage_name: str = Field(sa_column=Column(sa.String(100), nullable=False))
    stage_type: str = Field(sa_column=Column(sa.String(30), nullable=False))
    is_active: bool = Field(sa_column=Column(sa.Boolean(), nullable=False, server_default="true"))

    __table_args__ = (
        sa.UniqueConstraint("job_requisition_id", "stage_order", name="uq_pipeline_stage_jr_order"),
        sa.UniqueConstraint("job_requisition_id", "stage_type", name="uq_pipeline_stage_jr_type"),
        sa.Index("ix_pipeline_stages_jr", "job_requisition_id"),
    )


class CandidateStageResult(SQLModel, table=True):
    __tablename__ = "candidate_stage_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("candidate_applications.id", ondelete="CASCADE"), nullable=False
        )
    )
    stage_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("pipeline_stages.id", ondelete="CASCADE"), nullable=False)
    )
    result: Optional[str] = Field(default=None, sa_column=Column(sa.String(20), nullable=True))
    score: Optional[Decimal] = Field(default=None, sa_column=Column(sa.Numeric(5, 2), nullable=True))
    notes: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    test_file_path: Optional[str] = Field(default=None, sa_column=Column(sa.String(500), nullable=True))
    test_file_name: Optional[str] = Field(default=None, sa_column=Column(sa.String(300), nullable=True))
    test_score_raw: Optional[Decimal] = Field(default=None, sa_column=Column(sa.Numeric(5, 2), nullable=True))
    test_pass_threshold: Optional[Decimal] = Field(default=None, sa_column=Column(sa.Numeric(5, 2), nullable=True))
    evaluated_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    evaluated_at: Optional[datetime] = Field(default=None, sa_column=Column(sa.DateTime(), nullable=True))
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint("application_id", "stage_id", name="uq_candidate_stage_result_application_stage"),
        sa.Index("ix_candidate_stage_results_application", "application_id"),
    )


class InterviewSession(SQLModel, table=True):
    __tablename__ = "interview_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("candidate_applications.id", ondelete="CASCADE"), nullable=False
        )
    )
    stage_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("pipeline_stages.id", ondelete="CASCADE"), nullable=False)
    )
    scheduled_at: datetime = Field(sa_column=Column(sa.DateTime(), nullable=False))
    duration_minutes: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False, server_default="60"))
    format: str = Field(sa_column=Column(sa.String(20), nullable=False, server_default="in_person"))
    location: Optional[str] = Field(default=None, sa_column=Column(sa.String(300), nullable=True))
    note: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    status: str = Field(sa_column=Column(sa.String(20), nullable=False, server_default="scheduled"))
    completed_at: Optional[datetime] = Field(default=None, sa_column=Column(sa.DateTime(), nullable=True))
    cancel_reason: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.Index("ix_interview_sessions_application", "application_id"),
        sa.Index("ix_interview_sessions_scheduled", "scheduled_at"),
    )


class InterviewPanelist(SQLModel, table=True):
    __tablename__ = "interview_panelists"

    id: Optional[int] = Field(default=None, primary_key=True)
    interview_session_id: int = Field(
        sa_column=Column(
            sa.Integer(), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
        )
    )
    user_id: int = Field(
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    )
    criteria_scores: Optional[list[dict]] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    overall_score: Optional[Decimal] = Field(default=None, sa_column=Column(sa.Numeric(4, 2), nullable=True))
    result: Optional[str] = Field(default=None, sa_column=Column(sa.String(20), nullable=True))
    private_notes: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    submitted_at: Optional[datetime] = Field(default=None, sa_column=Column(sa.DateTime(), nullable=True))

    __table_args__ = (
        sa.UniqueConstraint("interview_session_id", "user_id", name="uq_interview_panelist_session_user"),
    )


class InterviewQuestion(SQLModel, table=True):
    __tablename__ = "interview_questions"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_text: str = Field(sa_column=Column(sa.Text(), nullable=False))
    category: Optional[str] = Field(default=None, sa_column=Column(sa.String(100), nullable=True))
    difficulty: Optional[str] = Field(default=None, sa_column=Column(sa.String(20), nullable=True))
    job_position_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("job_positions.id", ondelete="SET NULL"), nullable=True),
    )
    stage_type: Optional[str] = Field(default=None, sa_column=Column(sa.String(30), nullable=True))
    is_active: bool = Field(sa_column=Column(sa.Boolean(), nullable=False, server_default="true"))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.Index("ix_interview_questions_position", "job_position_id"),
    )


class ScorecardCriterion(SQLModel, table=True):
    __tablename__ = "scorecard_criteria"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(sa.String(200), nullable=False))
    job_position_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("job_positions.id", ondelete="SET NULL"), nullable=True),
    )
    stage_type: Optional[str] = Field(default=None, sa_column=Column(sa.String(30), nullable=True))
    max_score: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False, server_default="5"))
    sort_order: int = Field(sa_column=Column(sa.SmallInteger(), nullable=False, server_default="0"))
    is_active: bool = Field(sa_column=Column(sa.Boolean(), nullable=False, server_default="true"))

    __table_args__ = (
        sa.Index("ix_scorecard_criteria_position", "job_position_id"),
    )
