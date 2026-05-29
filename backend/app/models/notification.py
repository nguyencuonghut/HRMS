from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class NotificationTemplate(SQLModel, table=True):
    __tablename__ = "notification_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        max_length=100,
        sa_column=Column(sa.String(100), nullable=False, unique=True, index=True),
    )
    event_type: str = Field(max_length=50)
    name: str = Field(max_length=255)
    subject: str = Field(max_length=500)
    body_html: str = Field(sa_column=Column(sa.Text(), nullable=False))
    body_text: Optional[str] = Field(
        default=None, sa_column=Column(sa.Text(), nullable=True)
    )
    merge_fields: list = Field(
        default_factory=list,
        sa_column=Column(
            postgresql.JSONB(), nullable=False, server_default="'[]'::jsonb"
        ),
    )
    is_active: bool = Field(default=True)
    is_system: bool = Field(default=True)
    days_before: Optional[int] = Field(default=None)
    recipient_type: str = Field(default="hr", max_length=50)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class EmailLog(SQLModel, table=True):
    __tablename__ = "email_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    template_code: Optional[str] = Field(default=None, max_length=100)
    event_type: str = Field(max_length=50)
    employee_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    recipient_email: str = Field(max_length=255)
    recipient_name: Optional[str] = Field(default=None, max_length=255)
    subject: Optional[str] = Field(default=None, max_length=500)
    status: str = Field(max_length=20)  # sent | failed | skipped
    error_message: Optional[str] = Field(
        default=None, sa_column=Column(sa.Text(), nullable=True)
    )
    sent_at: datetime = Field(default_factory=_utcnow)
    celery_task_id: Optional[str] = Field(default=None, max_length=255)


class NotifConfig(SQLModel, table=True):
    __tablename__ = "notification_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(
        max_length=50,
        sa_column=Column(sa.String(50), nullable=False, unique=True, index=True),
    )
    is_enabled: bool = Field(default=True)
    days_before: Optional[list[int]] = Field(
        default=None,
        sa_column=Column(postgresql.ARRAY(sa.Integer()), nullable=True),
    )
    extra_recipients: Optional[list[str]] = Field(
        default=None,
        sa_column=Column(postgresql.ARRAY(sa.Text()), nullable=True),
    )
    updated_at: datetime = Field(default_factory=_utcnow)
