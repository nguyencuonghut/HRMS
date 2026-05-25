"""add recruitment pipeline and interview tables.

Revision ID: 0037
Revises: 0036
Create Date: 2026-05-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_stage_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("job_position_id", sa.Integer(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["job_position_id"], ["job_positions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_pipeline_stage_templates_job_position", "pipeline_stage_templates", ["job_position_id"])

    op.create_table(
        "pipeline_stage_template_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("stage_order", sa.SmallInteger(), nullable=False),
        sa.Column("stage_name", sa.String(length=100), nullable=False),
        sa.Column("stage_type", sa.String(length=30), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["template_id"], ["pipeline_stage_templates.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("template_id", "stage_order", name="uq_pipeline_stage_template_order"),
        sa.UniqueConstraint("template_id", "stage_type", name="uq_pipeline_stage_template_type"),
    )

    op.create_table(
        "pipeline_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_requisition_id", sa.Integer(), nullable=False),
        sa.Column("stage_order", sa.SmallInteger(), nullable=False),
        sa.Column("stage_name", sa.String(length=100), nullable=False),
        sa.Column("stage_type", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["job_requisition_id"], ["job_requisitions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_requisition_id", "stage_order", name="uq_pipeline_stage_jr_order"),
        sa.UniqueConstraint("job_requisition_id", "stage_type", name="uq_pipeline_stage_jr_type"),
    )
    op.create_index("ix_pipeline_stages_jr", "pipeline_stages", ["job_requisition_id"])

    op.create_table(
        "candidate_stage_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=True),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("test_file_path", sa.String(length=500), nullable=True),
        sa.Column("test_file_name", sa.String(length=300), nullable=True),
        sa.Column("test_score_raw", sa.Numeric(5, 2), nullable=True),
        sa.Column("test_pass_threshold", sa.Numeric(5, 2), nullable=True),
        sa.Column("evaluated_by_id", sa.Integer(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["application_id"], ["candidate_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stage_id"], ["pipeline_stages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("application_id", "stage_id", name="uq_candidate_stage_result_application_stage"),
    )
    op.create_index("ix_candidate_stage_results_application", "candidate_stage_results", ["application_id"])

    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("duration_minutes", sa.SmallInteger(), nullable=False, server_default="60"),
        sa.Column("format", sa.String(length=20), nullable=False, server_default="in_person"),
        sa.Column("location", sa.String(length=300), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["application_id"], ["candidate_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stage_id"], ["pipeline_stages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_interview_sessions_application", "interview_sessions", ["application_id"])
    op.create_index("ix_interview_sessions_scheduled", "interview_sessions", ["scheduled_at"])

    op.create_table(
        "interview_panelists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("interview_session_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("criteria_scores", JSONB, nullable=True),
        sa.Column("overall_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("result", sa.String(length=20), nullable=True),
        sa.Column("private_notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["interview_session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("interview_session_id", "user_id", name="uq_interview_panelist_session_user"),
    )

    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=True),
        sa.Column("job_position_id", sa.Integer(), nullable=True),
        sa.Column("stage_type", sa.String(length=30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["job_position_id"], ["job_positions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_interview_questions_position", "interview_questions", ["job_position_id"])

    op.create_table(
        "scorecard_criteria",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("job_position_id", sa.Integer(), nullable=True),
        sa.Column("stage_type", sa.String(length=30), nullable=True),
        sa.Column("max_score", sa.SmallInteger(), nullable=False, server_default="5"),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["job_position_id"], ["job_positions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_scorecard_criteria_position", "scorecard_criteria", ["job_position_id"])


def downgrade() -> None:
    op.drop_index("ix_scorecard_criteria_position", table_name="scorecard_criteria")
    op.drop_table("scorecard_criteria")

    op.drop_index("ix_interview_questions_position", table_name="interview_questions")
    op.drop_table("interview_questions")

    op.drop_table("interview_panelists")

    op.drop_index("ix_interview_sessions_scheduled", table_name="interview_sessions")
    op.drop_index("ix_interview_sessions_application", table_name="interview_sessions")
    op.drop_table("interview_sessions")

    op.drop_index("ix_candidate_stage_results_application", table_name="candidate_stage_results")
    op.drop_table("candidate_stage_results")

    op.drop_index("ix_pipeline_stages_jr", table_name="pipeline_stages")
    op.drop_table("pipeline_stages")

    op.drop_table("pipeline_stage_template_items")

    op.drop_index("ix_pipeline_stage_templates_job_position", table_name="pipeline_stage_templates")
    op.drop_table("pipeline_stage_templates")
