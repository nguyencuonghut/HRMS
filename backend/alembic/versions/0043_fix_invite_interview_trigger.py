"""fix invite_interview trigger_event: stage_moved:interview -> interview_scheduled

Revision ID: 0043
Revises: 0042
Create Date: 2026-05-26
"""
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE recruitment_email_templates
        SET trigger_event = 'interview_scheduled'
        WHERE code = 'invite_interview'
          AND trigger_event = 'stage_moved:interview'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE recruitment_email_templates
        SET trigger_event = 'stage_moved:interview'
        WHERE code = 'invite_interview'
          AND trigger_event = 'interview_scheduled'
    """)
