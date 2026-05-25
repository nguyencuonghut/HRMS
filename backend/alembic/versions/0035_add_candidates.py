"""add candidates and related tables.

Revision ID: 0035
Revises: 0034
Create Date: 2026-05-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("nationality", sa.String(100), nullable=True),
        sa.Column("id_number", sa.String(30), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("current_company", sa.String(200), nullable=True),
        sa.Column("current_position", sa.String(200), nullable=True),
        sa.Column("expected_salary", sa.Numeric(15, 2), nullable=True),
        sa.Column(
            "source_channel_id", sa.Integer(),
            sa.ForeignKey("recruitment_channels.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_by_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_candidates_email", "candidates", ["email"])
    op.execute(
        "CREATE INDEX ix_candidates_name ON candidates "
        "USING gin(to_tsvector('simple', full_name))"
    )

    op.create_table(
        "candidate_educations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "candidate_id", sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "institution_id", sa.Integer(),
            sa.ForeignKey("educational_institutions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("institution_name", sa.String(300), nullable=True),
        sa.Column(
            "major_id", sa.Integer(),
            sa.ForeignKey("education_majors.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("major_name", sa.String(300), nullable=True),
        sa.Column(
            "education_level_id", sa.Integer(),
            sa.ForeignKey("education_levels.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("graduation_year", sa.SmallInteger(), nullable=True),
        sa.Column("diploma_type", sa.String(100), nullable=True),
        sa.Column("is_main_education", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_candidate_educations_candidate", "candidate_educations", ["candidate_id"])

    op.create_table(
        "candidate_work_experiences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "candidate_id", sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(300), nullable=False),
        sa.Column("position_name", sa.String(200), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
    )
    op.create_index("ix_candidate_work_experiences_candidate", "candidate_work_experiences", ["candidate_id"])

    op.create_table(
        "candidate_skills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "candidate_id", sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("skill_name", sa.String(200), nullable=False),
        sa.Column("proficiency_level", sa.String(20), nullable=True),
        sa.UniqueConstraint("candidate_id", "skill_name", name="uq_candidate_skill"),
    )

    op.create_table(
        "candidate_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "candidate_id", sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attachment_type", sa.String(30), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(300), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "uploaded_by_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_candidate_attachments_candidate", "candidate_attachments", ["candidate_id"])

    op.create_table(
        "candidate_applications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "candidate_id", sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "job_requisition_id", sa.Integer(),
            sa.ForeignKey("job_requisitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("applied_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column(
            "source_channel_id", sa.Integer(),
            sa.ForeignKey("recruitment_channels.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("current_stage", sa.String(50), nullable=False, server_default="new"),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column(
            "created_by_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("candidate_id", "job_requisition_id", name="uq_application_candidate_jr"),
    )
    op.create_index("ix_applications_jr", "candidate_applications", ["job_requisition_id"])
    op.create_index("ix_applications_stage", "candidate_applications", ["current_stage"])


def downgrade() -> None:
    op.drop_index("ix_applications_stage", "candidate_applications")
    op.drop_index("ix_applications_jr", "candidate_applications")
    op.drop_table("candidate_applications")
    op.drop_index("ix_candidate_attachments_candidate", "candidate_attachments")
    op.drop_table("candidate_attachments")
    op.drop_table("candidate_skills")
    op.drop_index("ix_candidate_work_experiences_candidate", "candidate_work_experiences")
    op.drop_table("candidate_work_experiences")
    op.drop_index("ix_candidate_educations_candidate", "candidate_educations")
    op.drop_table("candidate_educations")
    op.drop_index("ix_candidates_name", "candidates")
    op.drop_index("ix_candidates_email", "candidates")
    op.drop_table("candidates")
