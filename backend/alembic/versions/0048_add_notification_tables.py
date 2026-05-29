"""add notification tables

Revision ID: 0048
Revises: 0047
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=100), nullable=False, unique=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column(
            "merge_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("days_before", sa.Integer(), nullable=True),
        sa.Column("recipient_type", sa.String(length=50), nullable=False, server_default="hr"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notif_templates_event_type", "notification_templates", ["event_type"])

    op.create_table(
        "email_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("template_code", sa.String(length=100), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("recipient_name", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_email_logs_event_type", "email_logs", ["event_type"])
    op.create_index("ix_email_logs_employee_id", "email_logs", ["employee_id"])
    op.create_index("ix_email_logs_sent_at", "email_logs", ["sent_at"])
    op.create_index("ix_email_logs_status", "email_logs", ["status"])

    op.create_table(
        "notification_config",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=50), nullable=False, unique=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("days_before", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("extra_recipients", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notif_config_event_type", "notification_config", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_notif_config_event_type", table_name="notification_config")
    op.drop_table("notification_config")

    op.drop_index("ix_email_logs_status", table_name="email_logs")
    op.drop_index("ix_email_logs_sent_at", table_name="email_logs")
    op.drop_index("ix_email_logs_employee_id", table_name="email_logs")
    op.drop_index("ix_email_logs_event_type", table_name="email_logs")
    op.drop_table("email_logs")

    op.drop_index("ix_notif_templates_event_type", table_name="notification_templates")
    op.drop_table("notification_templates")
