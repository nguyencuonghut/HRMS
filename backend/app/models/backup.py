from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BackupConfig(SQLModel, table=True):
    __tablename__ = "backup_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str = Field(
        max_length=50,
        sa_column=Column(sa.String(50), nullable=False, unique=True, index=True),
    )
    enabled: bool = Field(default=True)
    cron_expression: str = Field(max_length=100)
    retention_days: int = Field(default=90)
    source_endpoint: Optional[str] = Field(default=None, max_length=255)
    source_bucket: Optional[str] = Field(default=None, max_length=255)
    source_secure: Optional[bool] = Field(default=None)
    target_endpoint: Optional[str] = Field(default=None, max_length=255)
    target_bucket: str = Field(default="hrms-backup", max_length=255)
    target_prefix: Optional[str] = Field(default=None, max_length=255)
    target_secure: bool = Field(default=True)
    notify_emails: Optional[list[str]] = Field(
        default=None,
        sa_column=Column(postgresql.ARRAY(sa.Text()), nullable=True),
    )
    secret_source: str = Field(default="env", max_length=50)
    last_validated_at: Optional[datetime] = Field(default=None)
    last_validation_status: Optional[str] = Field(default=None, max_length=50)
    last_validation_error: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    updated_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class BackupJob(SQLModel, table=True):
    __tablename__ = "backup_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str = Field(max_length=50, index=True)
    trigger: str = Field(max_length=50)
    status: str = Field(default="queued", max_length=50, index=True)
    artifact_key: Optional[str] = Field(default=None, max_length=500)
    artifact_bucket: Optional[str] = Field(default=None, max_length=255)
    artifact_size_bytes: Optional[int] = Field(default=None)
    object_count: Optional[int] = Field(default=None)
    started_at: Optional[datetime] = Field(default=None)
    finished_at: Optional[datetime] = Field(default=None)
    error_summary: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    log_excerpt: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class RestoreRequest(SQLModel, table=True):
    __tablename__ = "restore_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str = Field(max_length=50, index=True)
    db_artifact_key: Optional[str] = Field(default=None, max_length=500)
    object_snapshot_key: Optional[str] = Field(default=None, max_length=500)
    mode: str = Field(max_length=100)
    target_db_name: Optional[str] = Field(default=None, max_length=255)
    target_bucket: Optional[str] = Field(default=None, max_length=255)
    status: str = Field(default="draft", max_length=50, index=True)
    requested_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    approved_by_id: Optional[int] = Field(
        default=None,
        sa_column=Column(sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    confirmation_text: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, sa_column=Column(sa.Text(), nullable=True))
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

