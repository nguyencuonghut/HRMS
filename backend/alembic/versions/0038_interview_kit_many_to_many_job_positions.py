"""interview kit many-to-many job positions.

Revision ID: 0038
Revises: 0037
Create Date: 2026-05-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Junction table: interview_questions <-> job_positions
    op.create_table(
        "interview_question_job_positions",
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("job_position_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["interview_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_position_id"], ["job_positions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("question_id", "job_position_id"),
    )
    op.create_index("ix_iq_job_position", "interview_question_job_positions", ["job_position_id"])

    # Junction table: scorecard_criteria <-> job_positions
    op.create_table(
        "scorecard_criterion_job_positions",
        sa.Column("criterion_id", sa.Integer(), nullable=False),
        sa.Column("job_position_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["criterion_id"], ["scorecard_criteria.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_position_id"], ["job_positions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("criterion_id", "job_position_id"),
    )
    op.create_index("ix_sc_job_position", "scorecard_criterion_job_positions", ["job_position_id"])

    # Drop old single FK columns
    op.drop_index("ix_interview_questions_position", table_name="interview_questions")
    op.drop_column("interview_questions", "job_position_id")

    op.drop_index("ix_scorecard_criteria_position", table_name="scorecard_criteria")
    op.drop_column("scorecard_criteria", "job_position_id")


def downgrade() -> None:
    op.add_column("scorecard_criteria", sa.Column("job_position_id", sa.Integer(), nullable=True))
    op.create_index("ix_scorecard_criteria_position", "scorecard_criteria", ["job_position_id"])

    op.add_column("interview_questions", sa.Column("job_position_id", sa.Integer(), nullable=True))
    op.create_index("ix_interview_questions_position", "interview_questions", ["job_position_id"])

    op.drop_index("ix_sc_job_position", table_name="scorecard_criterion_job_positions")
    op.drop_table("scorecard_criterion_job_positions")

    op.drop_index("ix_iq_job_position", table_name="interview_question_job_positions")
    op.drop_table("interview_question_job_positions")
