from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BackupOption(BaseModel):
    code: str
    label: str
    order: int


class BackupStatusOption(BaseModel):
    code: str
    label: str
    severity: str
    order: int


class BackupMetaResponse(BaseModel):
    kinds: list[BackupOption]
    job_statuses: list[BackupStatusOption]
    restore_statuses: list[BackupStatusOption]


class BackupConfigResponse(BaseModel):
    id: int
    kind: str
    kind_label: str
    enabled: bool
    cron_expression: str
    retention_days: int
    source_endpoint: Optional[str]
    source_bucket: Optional[str]
    source_secure: Optional[bool]
    target_endpoint: Optional[str]
    target_bucket: str
    target_prefix: Optional[str]
    target_secure: bool
    notify_emails: Optional[list[str]]
    secret_source: str
    source_configured: bool
    target_configured: bool
    last_validated_at: Optional[datetime]
    last_validation_status: Optional[str]
    last_validation_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BackupJobSummary(BaseModel):
    id: int
    kind: str
    trigger: str
    status: str
    artifact_key: Optional[str]
    artifact_bucket: Optional[str]
    artifact_size_bytes: Optional[int]
    object_count: Optional[int]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_summary: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class RestoreRequestSummary(BaseModel):
    id: int
    kind: str
    mode: str
    status: str
    db_artifact_key: Optional[str]
    object_snapshot_key: Optional[str]
    target_db_name: Optional[str]
    target_bucket: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BackupOverviewResponse(BaseModel):
    config_count: int
    configs: list[BackupConfigResponse]
    latest_jobs: list[BackupJobSummary]
    latest_restore_requests: list[RestoreRequestSummary]

