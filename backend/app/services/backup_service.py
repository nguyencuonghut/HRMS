from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.backup import BackupConfig, BackupJob, RestoreRequest
from app.schemas.backup import (
    BackupConfigResponse,
    BackupJobSummary,
    BackupOverviewResponse,
    RestoreRequestSummary,
)


BACKUP_KIND_DEFS: list[tuple[str, str]] = [
    ("db", "Database PostgreSQL"),
    ("object_storage", "File upload / object storage"),
]

JOB_STATUS_DEFS: list[tuple[str, str, str]] = [
    ("queued", "Đang chờ", "secondary"),
    ("running", "Đang chạy", "info"),
    ("success", "Thành công", "success"),
    ("failed", "Thất bại", "danger"),
    ("cancelled", "Đã hủy", "warn"),
]

RESTORE_STATUS_DEFS: list[tuple[str, str, str]] = [
    ("draft", "Bản nháp", "secondary"),
    ("queued", "Đang chờ", "secondary"),
    ("running", "Đang chạy", "info"),
    ("verified", "Đã kiểm tra", "success"),
    ("restored", "Đã khôi phục", "success"),
    ("failed", "Thất bại", "danger"),
    ("cancelled", "Đã hủy", "warn"),
]

KIND_LABELS = {code: label for code, label in BACKUP_KIND_DEFS}


def _split_emails(raw: str) -> list[str] | None:
    emails = [item.strip() for item in raw.split(",") if item.strip()]
    return emails or None


def _optional_bool(raw: str, fallback: bool) -> bool:
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return fallback


def _target_configured() -> bool:
    return bool(
        settings.BACKUP_STORAGE_ENDPOINT.strip()
        and settings.BACKUP_STORAGE_ACCESS_KEY.strip()
        and settings.BACKUP_STORAGE_SECRET_KEY.strip()
        and settings.BACKUP_STORAGE_BUCKET.strip()
    )


def _object_source_configured() -> bool:
    access_key = settings.SOURCE_STORAGE_ACCESS_KEY.strip() or settings.MINIO_ACCESS_KEY.strip()
    secret_key = settings.SOURCE_STORAGE_SECRET_KEY.strip() or settings.MINIO_SECRET_KEY.strip()
    endpoint = settings.SOURCE_STORAGE_ENDPOINT.strip() or settings.MINIO_ENDPOINT.strip()
    bucket = settings.MINIO_BUCKET.strip() or settings.minio_bucket_name
    return bool(endpoint and bucket and access_key and secret_key)


def _seed_rows() -> list[BackupConfig]:
    notify_emails = _split_emails(settings.BACKUP_NOTIFY_EMAILS)
    source_secure = _optional_bool(settings.SOURCE_STORAGE_SECURE, settings.MINIO_SECURE)

    return [
        BackupConfig(
            kind="db",
            enabled=True,
            cron_expression=settings.DB_BACKUP_CRON,
            retention_days=settings.BACKUP_RETENTION_DAYS,
            target_endpoint=settings.BACKUP_STORAGE_ENDPOINT.strip() or None,
            target_bucket=settings.BACKUP_STORAGE_BUCKET.strip() or "hrms-backup",
            target_prefix="postgres",
            target_secure=settings.BACKUP_STORAGE_SECURE,
            notify_emails=notify_emails,
            secret_source="env",
        ),
        BackupConfig(
            kind="object_storage",
            enabled=True,
            cron_expression=settings.MINIO_BACKUP_CRON,
            retention_days=settings.BACKUP_RETENTION_DAYS,
            source_endpoint=settings.SOURCE_STORAGE_ENDPOINT.strip() or settings.MINIO_ENDPOINT.strip() or None,
            source_bucket=settings.MINIO_BUCKET.strip() or settings.minio_bucket_name,
            source_secure=source_secure,
            target_endpoint=settings.BACKUP_STORAGE_ENDPOINT.strip() or None,
            target_bucket=settings.BACKUP_STORAGE_BUCKET.strip() or "hrms-backup",
            target_prefix="files",
            target_secure=settings.BACKUP_STORAGE_SECURE,
            notify_emails=notify_emails,
            secret_source="env",
        ),
    ]


async def ensure_backup_configs(session: AsyncSession) -> None:
    existing = set((await session.execute(select(BackupConfig.kind))).scalars().all())
    inserted = False
    for row in _seed_rows():
        if row.kind in existing:
            continue
        session.add(row)
        inserted = True

    if inserted:
        await session.commit()


def _to_config_response(row: BackupConfig) -> BackupConfigResponse:
    source_configured = bool(settings.DATABASE_URL.strip()) if row.kind == "db" else _object_source_configured()
    return BackupConfigResponse(
        id=row.id,
        kind=row.kind,
        kind_label=KIND_LABELS.get(row.kind, row.kind),
        enabled=row.enabled,
        cron_expression=row.cron_expression,
        retention_days=row.retention_days,
        source_endpoint=row.source_endpoint,
        source_bucket=row.source_bucket,
        source_secure=row.source_secure,
        target_endpoint=row.target_endpoint,
        target_bucket=row.target_bucket,
        target_prefix=row.target_prefix,
        target_secure=row.target_secure,
        notify_emails=row.notify_emails,
        secret_source=row.secret_source,
        source_configured=source_configured,
        target_configured=_target_configured(),
        last_validated_at=row.last_validated_at,
        last_validation_status=row.last_validation_status,
        last_validation_error=row.last_validation_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _job_summaries(rows: Iterable[BackupJob]) -> list[BackupJobSummary]:
    return [BackupJobSummary.model_validate(row) for row in rows]


def _restore_summaries(rows: Iterable[RestoreRequest]) -> list[RestoreRequestSummary]:
    return [RestoreRequestSummary.model_validate(row) for row in rows]


async def list_backup_configs(session: AsyncSession) -> list[BackupConfigResponse]:
    await ensure_backup_configs(session)
    rows = (
        await session.execute(
            select(BackupConfig).order_by(BackupConfig.kind)
        )
    ).scalars().all()
    return [_to_config_response(row) for row in rows]


async def get_backup_overview(session: AsyncSession) -> BackupOverviewResponse:
    configs = await list_backup_configs(session)
    jobs = (
        await session.execute(
            select(BackupJob).order_by(BackupJob.created_at.desc()).limit(5)
        )
    ).scalars().all()
    restore_requests = (
        await session.execute(
            select(RestoreRequest).order_by(RestoreRequest.created_at.desc()).limit(5)
        )
    ).scalars().all()

    return BackupOverviewResponse(
        config_count=len(configs),
        configs=configs,
        latest_jobs=_job_summaries(jobs),
        latest_restore_requests=_restore_summaries(restore_requests),
    )

