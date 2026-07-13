from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import datetime, timezone
from urllib.parse import urlsplit

from minio import Minio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from urllib3 import PoolManager, Timeout

from app.core.config import settings
from app.models.backup import BackupConfig, BackupJob, RestoreRequest
from app.schemas.backup import (
    BackupConfigResponse,
    BackupConfigUpdate,
    BackupJobSummary,
    BackupOverviewResponse,
    BackupValidateTargetResponse,
    RestoreRequestSummary,
)


BACKUP_KIND_DEFS: list[tuple[str, str]] = [
    ("db", "Cơ sở dữ liệu PostgreSQL"),
    ("object_storage", "Tệp tải lên trên MinIO"),
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

CONFIG_AUDIT_FIELDS = (
    "kind",
    "enabled",
    "cron_expression",
    "retention_days",
    "source_endpoint",
    "source_bucket",
    "source_secure",
    "target_endpoint",
    "target_bucket",
    "target_prefix",
    "target_secure",
    "notify_emails",
    "secret_source",
)


class BackupConfigNotFound(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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


def _normalize_minio_endpoint(raw: str | None) -> str:
    endpoint = (raw or "").strip().rstrip("/")
    if "://" in endpoint:
        parsed = urlsplit(endpoint)
        endpoint = parsed.netloc
    return endpoint


def _target_values(row: BackupConfig | None = None) -> tuple[str, str, bool]:
    endpoint = _normalize_minio_endpoint(
        (row.target_endpoint if row and row.target_endpoint else None)
        or settings.BACKUP_STORAGE_ENDPOINT
    )
    bucket = (
        (row.target_bucket if row and row.target_bucket else None)
        or settings.BACKUP_STORAGE_BUCKET
    ).strip()
    secure = row.target_secure if row is not None else settings.BACKUP_STORAGE_SECURE
    return endpoint, bucket, secure


def _target_configured(row: BackupConfig | None = None) -> bool:
    endpoint, bucket, _ = _target_values(row)
    return bool(
        endpoint
        and settings.BACKUP_STORAGE_ACCESS_KEY.strip()
        and settings.BACKUP_STORAGE_SECRET_KEY.strip()
        and bucket
    )


def _object_source_configured(row: BackupConfig | None = None) -> bool:
    access_key = settings.SOURCE_STORAGE_ACCESS_KEY.strip() or settings.MINIO_ACCESS_KEY.strip()
    secret_key = settings.SOURCE_STORAGE_SECRET_KEY.strip() or settings.MINIO_SECRET_KEY.strip()
    endpoint = (
        (row.source_endpoint if row and row.source_endpoint else None)
        or settings.SOURCE_STORAGE_ENDPOINT
        or settings.MINIO_ENDPOINT
    ).strip()
    bucket = (
        (row.source_bucket if row and row.source_bucket else None)
        or settings.MINIO_BUCKET
        or settings.minio_bucket_name
    ).strip()
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
    source_configured = bool(settings.DATABASE_URL.strip()) if row.kind == "db" else _object_source_configured(row)
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
        target_configured=_target_configured(row),
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


def config_response(row: BackupConfig) -> BackupConfigResponse:
    return _to_config_response(row)


def safe_config_snapshot(row: BackupConfig) -> dict:
    return {field: getattr(row, field) for field in CONFIG_AUDIT_FIELDS}


async def get_backup_config_row(session: AsyncSession, kind: str) -> BackupConfig:
    await ensure_backup_configs(session)
    row = (
        await session.execute(select(BackupConfig).where(BackupConfig.kind == kind))
    ).scalar_one_or_none()
    if row is None:
        raise BackupConfigNotFound(kind)
    return row


async def update_backup_config(
    session: AsyncSession,
    *,
    kind: str,
    payload: BackupConfigUpdate,
    user_id: int | None,
) -> tuple[BackupConfig, dict, dict]:
    row = await get_backup_config_row(session, kind)
    old_data = safe_config_snapshot(row)

    row.enabled = payload.enabled
    row.cron_expression = payload.cron_expression
    row.retention_days = payload.retention_days
    row.source_endpoint = payload.source_endpoint
    row.source_bucket = payload.source_bucket
    row.source_secure = payload.source_secure
    row.target_endpoint = payload.target_endpoint
    row.target_bucket = payload.target_bucket
    row.target_prefix = payload.target_prefix
    row.target_secure = payload.target_secure
    row.notify_emails = payload.notify_emails
    row.secret_source = "env"
    row.updated_by_id = user_id
    row.updated_at = _utcnow()

    session.add(row)
    return row, old_data, safe_config_snapshot(row)


def _sanitize_validation_message(message: str) -> str:
    sanitized = message
    for secret in (
        settings.BACKUP_STORAGE_ACCESS_KEY,
        settings.BACKUP_STORAGE_SECRET_KEY,
        settings.MINIO_ACCESS_KEY,
        settings.MINIO_SECRET_KEY,
    ):
        secret = secret.strip()
        if secret:
            sanitized = sanitized.replace(secret, "***")
    return sanitized[:500]


def _probe_target_bucket(endpoint: str, bucket: str, secure: bool) -> tuple[bool, str]:
    http_client = PoolManager(
        timeout=Timeout(connect=1.5, read=2.0),
        retries=False,
    )
    client = Minio(
        endpoint=endpoint,
        access_key=settings.BACKUP_STORAGE_ACCESS_KEY.strip(),
        secret_key=settings.BACKUP_STORAGE_SECRET_KEY.strip(),
        secure=secure,
        http_client=http_client,
    )
    if not client.bucket_exists(bucket):
        return False, "Không tìm thấy kho lưu trữ đích sao lưu."
    return True, "Đã kết nối được đích sao lưu."


async def validate_backup_target(
    session: AsyncSession,
    *,
    kind: str,
    user_id: int | None,
) -> tuple[BackupConfig, BackupValidateTargetResponse]:
    row = await get_backup_config_row(session, kind)
    checked_at = _utcnow()
    endpoint, bucket, secure = _target_values(row)

    if not _target_configured(row):
        status = "failed"
        message = "Thiếu địa chỉ kết nối, kho lưu trữ hoặc thông tin xác thực của đích sao lưu trong cấu hình máy chủ."
    else:
        try:
            ok, message = await asyncio.to_thread(_probe_target_bucket, endpoint, bucket, secure)
            status = "success" if ok else "failed"
        except Exception as exc:  # pragma: no cover - phụ thuộc hạ tầng MinIO runtime
            status = "failed"
            message = _sanitize_validation_message(f"Không kết nối được đích sao lưu: {exc}")

    row.last_validated_at = checked_at
    row.last_validation_status = status
    row.last_validation_error = None if status == "success" else message
    row.updated_by_id = user_id
    row.updated_at = checked_at
    session.add(row)

    return row, BackupValidateTargetResponse(
        kind=row.kind,
        status=status,
        message=message,
        checked_at=checked_at,
        target_configured=_target_configured(row),
    )


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
