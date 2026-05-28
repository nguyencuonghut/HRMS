from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _default_expiry() -> datetime:
    return _utcnow() + timedelta(days=7)


class ExportJob(SQLModel, table=True):
    __tablename__ = "export_jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    report_type: str = Field(max_length=100)
    format: str = Field(max_length=10)
    filters: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default=dict),
    )
    status: str = Field(default="pending", max_length=20)
    filename: Optional[str] = Field(default=None, max_length=255)
    file_path: Optional[str] = Field(default=None, max_length=500)
    file_size_bytes: Optional[int] = Field(default=None)
    row_count: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    celery_task_id: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=_utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    expires_at: datetime = Field(default_factory=_default_expiry)


class ReportTemplate(SQLModel, table=True):
    __tablename__ = "report_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    report_type: str = Field(max_length=100)
    format: str = Field(default="xlsx", max_length=10)
    filters: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default=dict),
    )
    is_default: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint("user_id", "name", name="uq_report_templates_user_name"),
    )
