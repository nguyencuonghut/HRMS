from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
import inspect
import structlog
from typing import Awaitable, Callable
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from minio import Minio
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession
from urllib3 import PoolManager, Timeout

from app.core.config import settings
from app.models.backup import BackupConfig, BackupJob, BackupSet, RestoreRequest
from app.schemas.backup import (
    BackupConfigResponse,
    BackupConfigUpdate,
    BackupJobSummary,
    BackupOverviewResponse,
    BackupSetSummary,
    BackupSnapshotSummary,
    BackupValidateTargetResponse,
    RestoreRequestSummary,
)
from app.services import backup_notification_service
from app.services.backup_runner_service import BackupRunResult, run_backup
from app.services.restore_runner_service import RestoreRunResult, run_restore_request as execute_restore_request

logger = structlog.get_logger(__name__)

BackupRunner = Callable[[AsyncSession, BackupConfig, datetime], Awaitable[BackupRunResult] | BackupRunResult]
RestoreRunner = Callable[[AsyncSession, RestoreRequest, datetime], Awaitable[RestoreRunResult] | RestoreRunResult]


BACKUP_KIND_DEFS: list[tuple[str, str]] = [
    ("db", "Cơ sở dữ liệu PostgreSQL"),
    ("object_storage", "Kho tệp ứng dụng trên MinIO"),
]

JOB_STATUS_DEFS: list[tuple[str, str, str]] = [
    ("queued", "Đang chờ", "secondary"),
    ("running", "Đang chạy", "info"),
    ("success", "Thành công", "success"),
    ("failed", "Thất bại", "danger"),
    ("cancelled", "Đã hủy", "warn"),
]
JOB_STATUS_LABELS = {code: label for code, label, _severity in JOB_STATUS_DEFS}

RESTORE_STATUS_DEFS: list[tuple[str, str, str]] = [
    ("draft", "Chờ duyệt", "secondary"),
    ("queued", "Đã duyệt, đang chờ", "secondary"),
    ("running", "Đang chạy", "info"),
    ("verified", "Đã kiểm tra", "success"),
    ("restored", "Đã khôi phục", "success"),
    ("failed", "Thất bại", "danger"),
    ("cancelled", "Đã hủy", "warn"),
]

KIND_LABELS = {code: label for code, label in BACKUP_KIND_DEFS}
ACTIVE_BACKUP_SET_STATUSES = ("queued", "running")
FULL_BACKUP_TRIGGER_MANUAL = "manual_full"
FULL_BACKUP_TRIGGER_SCHEDULED = "scheduled_full"

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


class BackupJobNotFound(Exception):
    pass


class BackupSnapshotNotFound(Exception):
    pass


class BackupSetNotFound(Exception):
    pass


class ActiveBackupSetExists(Exception):
    def __init__(self, backup_set_id: int):
        self.backup_set_id = backup_set_id


class RestoreRequestNotFound(Exception):
    pass


class RestoreRequestInvalidState(Exception):
    pass


class UnsafeRestoreTarget(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).replace(tzinfo=None)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _as_app_timezone(value: datetime) -> datetime:
    aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return aware.astimezone(ZoneInfo(settings.APP_TIMEZONE))


def _cron_values(raw: str, minimum: int, maximum: int) -> set[int]:
    values: set[int] = set()
    for item in raw.split(","):
        base, separator, step_raw = item.partition("/")
        step = int(step_raw) if separator else 1
        if base == "*":
            start = minimum
            end = maximum
        else:
            start_raw, range_separator, end_raw = base.partition("-")
            start = int(start_raw)
            end = int(end_raw) if range_separator else start
        values.update(range(start, end + 1, step))
    return values


def _cron_matches(expression: str, value: datetime) -> bool:
    parts = " ".join(expression.strip().split()).split(" ")
    if len(parts) != 5:
        return False

    minute_raw, hour_raw, day_raw, month_raw, weekday_raw = parts
    try:
        minute_values = _cron_values(minute_raw, 0, 59)
        hour_values = _cron_values(hour_raw, 0, 23)
        day_values = _cron_values(day_raw, 1, 31)
        month_values = _cron_values(month_raw, 1, 12)
        weekday_values = _cron_values(weekday_raw, 0, 7)
    except (TypeError, ValueError):
        return False

    cron_weekday = 0 if value.isoweekday() == 7 else value.isoweekday()
    weekday_matches = cron_weekday in weekday_values or (cron_weekday == 0 and 7 in weekday_values)
    day_matches = value.day in day_values
    day_restricted = day_raw != "*"
    weekday_restricted = weekday_raw != "*"
    if day_restricted and weekday_restricted:
        schedule_day_matches = day_matches or weekday_matches
    else:
        schedule_day_matches = day_matches and weekday_matches

    return (
        value.minute in minute_values
        and value.hour in hour_values
        and value.month in month_values
        and schedule_day_matches
    )


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


def _backup_set_summary(row: BackupSet, jobs_by_id: dict[int, BackupJob]) -> BackupSetSummary:
    db_job = jobs_by_id.get(row.db_job_id or 0)
    object_job = jobs_by_id.get(row.object_job_id or 0)
    artifact_bucket = (
        db_job.artifact_bucket
        if db_job and db_job.artifact_bucket
        else object_job.artifact_bucket if object_job and object_job.artifact_bucket else None
    )
    return BackupSetSummary(
        id=row.id,
        trigger=row.trigger,
        status=row.status,
        db_job_id=row.db_job_id,
        object_job_id=row.object_job_id,
        db_artifact_key=db_job.artifact_key if db_job else None,
        object_snapshot_key=object_job.artifact_key if object_job else None,
        artifact_bucket=artifact_bucket,
        started_at=row.started_at,
        finished_at=row.finished_at,
        error_summary=row.error_summary,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _backup_set_summaries(session: AsyncSession, rows: Iterable[BackupSet]) -> list[BackupSetSummary]:
    rows_list = list(rows)
    job_ids = {
        job_id
        for row in rows_list
        for job_id in (row.db_job_id, row.object_job_id)
        if job_id is not None
    }
    jobs_by_id: dict[int, BackupJob] = {}
    if job_ids:
        jobs = (
            await session.execute(select(BackupJob).where(BackupJob.id.in_(job_ids)))
        ).scalars().all()
        jobs_by_id = {job.id: job for job in jobs if job.id is not None}
    return [_backup_set_summary(row, jobs_by_id) for row in rows_list]


def _snapshot_summaries(rows: Iterable[BackupJob]) -> list[BackupSnapshotSummary]:
    return [
        BackupSnapshotSummary(
            kind=row.kind,
            artifact_key=row.artifact_key or "",
            artifact_bucket=row.artifact_bucket or "",
            artifact_size_bytes=row.artifact_size_bytes,
            object_count=row.object_count,
            created_at=row.created_at,
            finished_at=row.finished_at,
        )
        for row in rows
        if row.artifact_key and row.artifact_bucket
    ]


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


def _secrets_for_sanitization() -> tuple[str, ...]:
    secrets = [
        settings.BACKUP_STORAGE_ACCESS_KEY,
        settings.BACKUP_STORAGE_SECRET_KEY,
        settings.SOURCE_STORAGE_ACCESS_KEY,
        settings.SOURCE_STORAGE_SECRET_KEY,
        settings.MINIO_ACCESS_KEY,
        settings.MINIO_SECRET_KEY,
        settings.DATABASE_URL,
    ]
    try:
        db_password = make_url(settings.DATABASE_URL).password
        if db_password:
            secrets.append(db_password)
    except Exception:
        pass
    return tuple(secrets)


def _sanitize_validation_message(message: str) -> str:
    sanitized = message
    for secret in _secrets_for_sanitization():
        secret = secret.strip()
        if secret:
            sanitized = sanitized.replace(secret, "***")
    return sanitized[:500]


def _notification_timestamp(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZoneInfo(settings.APP_TIMEZONE)).isoformat()


def _notification_summary(row: BackupJob) -> str:
    kind_label = KIND_LABELS.get(row.kind, row.kind)
    if row.status == "success":
        return f"Sao lưu {kind_label} đã hoàn tất."
    return row.error_summary or f"Sao lưu {kind_label} thất bại."


def _notification_details(row: BackupJob) -> str:
    lines = [
        f"Loại sao lưu: {KIND_LABELS.get(row.kind, row.kind)}",
        f"Trạng thái: {JOB_STATUS_LABELS.get(row.status, row.status)}",
    ]
    if row.artifact_bucket:
        lines.append(f"Kho lưu trữ: {row.artifact_bucket}")
    if row.artifact_key:
        lines.append(f"Đường dẫn bản sao: {row.artifact_key}")
    if row.artifact_size_bytes is not None:
        lines.append(f"Dung lượng: {row.artifact_size_bytes} bytes")
    if row.object_count is not None:
        lines.append(f"Số đối tượng: {row.object_count}")
    if row.error_summary:
        lines.append(f"Lỗi: {row.error_summary}")
    if row.log_excerpt:
        lines.extend(["", "Log rút gọn:", row.log_excerpt])
    return "\n".join(lines)


async def _send_backup_job_notification(
    session: AsyncSession,
    *,
    config: BackupConfig,
    row: BackupJob,
) -> None:
    if row.status not in {"success", "failed"}:
        return

    try:
        result = await backup_notification_service.send_backup_status_email(
            session,
            job_name=KIND_LABELS.get(row.kind, row.kind),
            status=row.status,
            summary=_notification_summary(row),
            details=_notification_details(row),
            started_at=_notification_timestamp(row.started_at),
            finished_at=_notification_timestamp(row.finished_at),
            override_recipients=config.notify_emails,
        )
    except Exception as exc:  # pragma: no cover - phụ thuộc hạ tầng SMTP runtime
        logger.warning(
            "backup_notification_failed",
            job_id=row.id,
            kind=row.kind,
            error=_sanitize_validation_message(str(exc)),
        )
        return

    if result.get("status") in {"failed", "partial"}:
        logger.warning(
            "backup_notification_not_fully_sent",
            job_id=row.id,
            kind=row.kind,
            notification_status=result.get("status"),
            failed_recipients=sorted((result.get("failed") or {}).keys()),
        )


def job_response(row: BackupJob) -> BackupJobSummary:
    return BackupJobSummary.model_validate(row)


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


async def create_manual_backup_job(
    session: AsyncSession,
    *,
    kind: str,
    user_id: int | None,
) -> BackupJob:
    await get_backup_config_row(session, kind)
    now = _utcnow()
    row = BackupJob(
        kind=kind,
        trigger="manual",
        status="queued",
        created_by_id=user_id,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    return row


async def create_manual_backup_set(
    session: AsyncSession,
    *,
    user_id: int | None,
) -> BackupSet:
    await get_backup_config_row(session, "db")
    await get_backup_config_row(session, "object_storage")
    active_backup_set_id = (
        await session.execute(
            select(BackupSet.id)
            .where(BackupSet.status.in_(ACTIVE_BACKUP_SET_STATUSES))
            .order_by(BackupSet.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if active_backup_set_id is not None:
        raise ActiveBackupSetExists(active_backup_set_id)

    now = _utcnow()
    row = BackupSet(
        trigger="manual",
        status="queued",
        created_by_id=user_id,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()

    db_job = BackupJob(
        backup_set_id=row.id,
        kind="db",
        trigger=FULL_BACKUP_TRIGGER_MANUAL,
        status="queued",
        created_by_id=user_id,
        created_at=now,
        updated_at=now,
    )
    object_job = BackupJob(
        backup_set_id=row.id,
        kind="object_storage",
        trigger=FULL_BACKUP_TRIGGER_MANUAL,
        status="queued",
        created_by_id=user_id,
        created_at=now,
        updated_at=now,
    )
    session.add(db_job)
    session.add(object_job)
    await session.flush()

    row.db_job_id = db_job.id
    row.object_job_id = object_job.id
    row.updated_at = now
    session.add(row)
    await session.flush()
    return row


async def create_scheduled_backup_set_if_due(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> BackupSet | None:
    db_config = await get_backup_config_row(session, "db")
    object_config = await get_backup_config_row(session, "object_storage")
    if not db_config.enabled or not object_config.enabled:
        return None

    current = now or _utcnow()
    app_now = _as_app_timezone(current).replace(second=0, microsecond=0)
    if not _cron_matches(db_config.cron_expression, app_now):
        return None

    slot_start = _as_utc_naive(app_now)
    slot_end = slot_start + timedelta(minutes=1)
    existing_scheduled_id = (
        await session.execute(
            select(BackupSet.id)
            .where(BackupSet.trigger == FULL_BACKUP_TRIGGER_SCHEDULED)
            .where(BackupSet.created_at >= slot_start)
            .where(BackupSet.created_at < slot_end)
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing_scheduled_id is not None:
        return None

    active_backup_set_id = (
        await session.execute(
            select(BackupSet.id)
            .where(BackupSet.status.in_(ACTIVE_BACKUP_SET_STATUSES))
            .order_by(BackupSet.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if active_backup_set_id is not None:
        logger.info(
            "scheduled_backup_set_skipped_active_set",
            active_backup_set_id=active_backup_set_id,
            scheduled_for=app_now.isoformat(),
        )
        return None

    row = BackupSet(
        trigger=FULL_BACKUP_TRIGGER_SCHEDULED,
        status="queued",
        created_by_id=None,
        created_at=slot_start,
        updated_at=slot_start,
    )
    session.add(row)
    await session.flush()

    db_job = BackupJob(
        backup_set_id=row.id,
        kind="db",
        trigger=FULL_BACKUP_TRIGGER_SCHEDULED,
        status="queued",
        created_by_id=None,
        created_at=slot_start,
        updated_at=slot_start,
    )
    object_job = BackupJob(
        backup_set_id=row.id,
        kind="object_storage",
        trigger=FULL_BACKUP_TRIGGER_SCHEDULED,
        status="queued",
        created_by_id=None,
        created_at=slot_start,
        updated_at=slot_start,
    )
    session.add(db_job)
    session.add(object_job)
    await session.flush()

    row.db_job_id = db_job.id
    row.object_job_id = object_job.id
    row.updated_at = slot_start
    session.add(row)
    await session.flush()
    return row


def safe_job_snapshot(row: BackupJob) -> dict:
    return {
        "id": row.id,
        "backup_set_id": row.backup_set_id,
        "kind": row.kind,
        "trigger": row.trigger,
        "status": row.status,
        "artifact_key": row.artifact_key,
        "artifact_bucket": row.artifact_bucket,
        "artifact_size_bytes": row.artifact_size_bytes,
        "object_count": row.object_count,
    }


def safe_backup_set_snapshot(row: BackupSet) -> dict:
    return {
        "id": row.id,
        "trigger": row.trigger,
        "status": row.status,
        "db_job_id": row.db_job_id,
        "object_job_id": row.object_job_id,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "error_summary": row.error_summary,
    }


def safe_restore_snapshot(row: RestoreRequest) -> dict:
    return {
        "id": row.id,
        "backup_set_id": row.backup_set_id,
        "kind": row.kind,
        "mode": row.mode,
        "status": row.status,
        "db_artifact_key": row.db_artifact_key,
        "object_snapshot_key": row.object_snapshot_key,
        "target_db_name": row.target_db_name,
        "target_bucket": row.target_bucket,
        "requested_by_id": row.requested_by_id,
        "approved_by_id": row.approved_by_id,
    }


def enqueue_backup_job(job_id: int) -> None:
    try:
        from app.workers.backup_tasks import run_backup_job_task

        run_backup_job_task.apply_async(args=[job_id], queue="backups")
    except Exception as exc:  # pragma: no cover - phụ thuộc broker runtime
        logger.warning("backup_job_enqueue_failed", job_id=job_id, error=str(exc))


def enqueue_backup_set(backup_set_id: int) -> None:
    try:
        from app.workers.backup_tasks import run_backup_set_task

        run_backup_set_task.apply_async(args=[backup_set_id], queue="backups")
    except Exception as exc:  # pragma: no cover - phụ thuộc broker runtime
        logger.warning("backup_set_enqueue_failed", backup_set_id=backup_set_id, error=str(exc))


def enqueue_restore_request(restore_request_id: int) -> bool:
    try:
        from app.workers.backup_tasks import run_restore_request_task

        run_restore_request_task.apply_async(args=[restore_request_id], queue="backups")
        return True
    except Exception as exc:  # pragma: no cover - phụ thuộc broker runtime
        logger.warning("restore_request_enqueue_failed", restore_request_id=restore_request_id, error=str(exc))
        return False


async def list_backup_jobs(
    session: AsyncSession,
    *,
    kind: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[BackupJobSummary]:
    query = select(BackupJob)
    if kind:
        query = query.where(BackupJob.kind == kind)
    if status:
        query = query.where(BackupJob.status == status)
    rows = (
        await session.execute(
            query.order_by(BackupJob.created_at.desc()).limit(limit)
        )
    ).scalars().all()
    return _job_summaries(rows)


async def list_backup_sets(
    session: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[BackupSetSummary]:
    query = select(BackupSet)
    if status:
        query = query.where(BackupSet.status == status)
    rows = (
        await session.execute(
            query.order_by(BackupSet.created_at.desc()).limit(limit)
        )
    ).scalars().all()
    return await _backup_set_summaries(session, rows)


async def get_backup_set_summary(session: AsyncSession, backup_set_id: int) -> BackupSetSummary:
    row = await session.get(BackupSet, backup_set_id)
    if row is None:
        raise BackupSetNotFound(backup_set_id)
    return (await _backup_set_summaries(session, [row]))[0]


async def list_backup_snapshots(
    session: AsyncSession,
    *,
    kind: str | None = None,
    limit: int = 50,
) -> list[BackupSnapshotSummary]:
    query = (
        select(BackupJob)
        .where(BackupJob.status == "success")
        .where(BackupJob.artifact_key.is_not(None))
        .where(BackupJob.artifact_bucket.is_not(None))
    )
    if kind:
        query = query.where(BackupJob.kind == kind)
    rows = (
        await session.execute(
            query.order_by(BackupJob.finished_at.desc().nullslast(), BackupJob.created_at.desc()).limit(limit)
        )
    ).scalars().all()
    return _snapshot_summaries(rows)


async def _find_snapshot_job(session: AsyncSession, *, kind: str, artifact_key: str) -> BackupJob:
    row = (
        await session.execute(
            select(BackupJob)
            .where(BackupJob.kind == kind)
            .where(BackupJob.status == "success")
            .where(BackupJob.artifact_key == artifact_key)
            .order_by(BackupJob.created_at.desc())
        )
    ).scalars().first()
    if row is None or not row.artifact_bucket:
        raise BackupSnapshotNotFound(artifact_key)
    return row


async def _find_successful_backup_set(session: AsyncSession, backup_set_id: int) -> tuple[BackupSet, BackupJob, BackupJob]:
    row = await session.get(BackupSet, backup_set_id)
    if row is None or row.status != "success" or not row.db_job_id or not row.object_job_id:
        raise BackupSetNotFound(backup_set_id)

    jobs = (
        await session.execute(
            select(BackupJob).where(BackupJob.id.in_([row.db_job_id, row.object_job_id]))
        )
    ).scalars().all()
    jobs_by_kind = {job.kind: job for job in jobs}
    db_job = jobs_by_kind.get("db")
    object_job = jobs_by_kind.get("object_storage")
    if (
        db_job is None
        or object_job is None
        or db_job.status != "success"
        or object_job.status != "success"
        or not db_job.artifact_key
        or not db_job.artifact_bucket
        or not object_job.artifact_key
        or not object_job.artifact_bucket
    ):
        raise BackupSetNotFound(backup_set_id)
    return row, db_job, object_job


def _current_database_name() -> str:
    return (make_url(settings.DATABASE_URL).database or "").strip()


async def _production_object_buckets(session: AsyncSession) -> set[str]:
    buckets = {
        settings.MINIO_BUCKET.strip(),
        settings.minio_bucket_name.strip(),
        settings.BACKUP_STORAGE_BUCKET.strip(),
    }
    try:
        config = await get_backup_config_row(session, "object_storage")
        if config.source_bucket:
            buckets.add(config.source_bucket.strip())
        if config.target_bucket:
            buckets.add(config.target_bucket.strip())
    except BackupConfigNotFound:
        pass
    return {bucket for bucket in buckets if bucket}


async def _validate_restore_targets(
    session: AsyncSession,
    *,
    kind: str,
    mode: str,
    target_db_name: str | None,
    target_bucket: str | None,
) -> None:
    if mode != "restore_to_new_target":
        return

    if kind in {"db", "full"} and target_db_name == _current_database_name():
        raise UnsafeRestoreTarget("Không được khôi phục vào cơ sở dữ liệu production hiện tại.")

    if kind in {"object_storage", "full"} and target_bucket:
        production_buckets = await _production_object_buckets(session)
        if target_bucket in production_buckets:
            raise UnsafeRestoreTarget("Không được khôi phục vào kho tệp production hoặc kho backup hiện tại.")


async def create_restore_request(
    session: AsyncSession,
    *,
    kind: str,
    mode: str,
    backup_set_id: int | None,
    db_artifact_key: str | None,
    object_snapshot_key: str | None,
    target_db_name: str | None,
    target_bucket: str | None,
    confirmation_text: str,
    notes: str | None,
    user_id: int | None,
) -> RestoreRequest:
    if kind == "full":
        if not backup_set_id:
            raise BackupSetNotFound("missing")
        _, db_job, object_job = await _find_successful_backup_set(session, backup_set_id)
        db_artifact_key = db_job.artifact_key
        object_snapshot_key = object_job.artifact_key
    elif kind == "db":
        backup_set_id = None
        object_snapshot_key = None
    elif kind == "object_storage":
        backup_set_id = None
        db_artifact_key = None

    if kind == "db" and db_artifact_key:
        await _find_snapshot_job(session, kind="db", artifact_key=db_artifact_key)
    if kind == "object_storage" and object_snapshot_key:
        await _find_snapshot_job(session, kind="object_storage", artifact_key=object_snapshot_key)
    await _validate_restore_targets(
        session,
        kind=kind,
        mode=mode,
        target_db_name=target_db_name,
        target_bucket=target_bucket,
    )

    now = _utcnow()
    row = RestoreRequest(
        backup_set_id=backup_set_id,
        kind=kind,
        db_artifact_key=db_artifact_key,
        object_snapshot_key=object_snapshot_key,
        mode=mode,
        target_db_name=target_db_name,
        target_bucket=target_bucket,
        status="draft",
        requested_by_id=user_id,
        confirmation_text=confirmation_text,
        notes=notes,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    return row


async def list_restore_requests(
    session: AsyncSession,
    *,
    kind: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[RestoreRequestSummary]:
    query = select(RestoreRequest)
    if kind:
        query = query.where(RestoreRequest.kind == kind)
    if status:
        query = query.where(RestoreRequest.status == status)
    rows = (
        await session.execute(
            query.order_by(RestoreRequest.created_at.desc()).limit(limit)
        )
    ).scalars().all()
    return _restore_summaries(rows)


async def get_restore_request(session: AsyncSession, restore_request_id: int) -> RestoreRequest:
    row = (
        await session.execute(select(RestoreRequest).where(RestoreRequest.id == restore_request_id))
    ).scalar_one_or_none()
    if row is None:
        raise RestoreRequestNotFound(restore_request_id)
    return row


async def approve_restore_request(
    session: AsyncSession,
    *,
    restore_request_id: int,
    user_id: int | None,
) -> tuple[RestoreRequest, dict, dict]:
    row = await get_restore_request(session, restore_request_id)
    if row.status != "draft":
        raise RestoreRequestInvalidState("Chỉ có thể duyệt yêu cầu khôi phục đang chờ duyệt.")

    old_data = safe_restore_snapshot(row)
    now = _utcnow()
    row.status = "queued"
    row.approved_by_id = user_id
    row.notes = "Đã duyệt và đưa vào hàng đợi xử lý."
    row.updated_at = now
    session.add(row)
    await session.flush()
    return row, old_data, safe_restore_snapshot(row)


async def retry_restore_request(
    session: AsyncSession,
    *,
    restore_request_id: int,
    user_id: int | None,
) -> tuple[RestoreRequest, dict, dict]:
    row = await get_restore_request(session, restore_request_id)
    if row.status not in {"failed", "cancelled", "queued"}:
        raise RestoreRequestInvalidState("Chỉ có thể gửi lại yêu cầu khôi phục đang lỗi, đã hủy hoặc đang chờ.")

    old_data = safe_restore_snapshot(row)
    now = _utcnow()
    row.status = "queued"
    row.approved_by_id = user_id
    row.notes = "Đã gửi lại yêu cầu khôi phục vào hàng đợi xử lý."
    row.updated_at = now
    session.add(row)
    await session.flush()
    return row, old_data, safe_restore_snapshot(row)


async def cancel_restore_request(
    session: AsyncSession,
    *,
    restore_request_id: int,
) -> tuple[RestoreRequest, dict, dict]:
    row = await get_restore_request(session, restore_request_id)
    if row.status not in {"draft", "queued"}:
        raise RestoreRequestInvalidState("Chỉ có thể hủy yêu cầu khôi phục đang chờ duyệt hoặc đang chờ xử lý.")

    old_data = safe_restore_snapshot(row)
    now = _utcnow()
    row.status = "cancelled"
    row.notes = "Đã hủy yêu cầu khôi phục."
    row.updated_at = now
    session.add(row)
    await session.flush()
    return row, old_data, safe_restore_snapshot(row)


async def mark_restore_enqueue_failed(
    session: AsyncSession,
    *,
    restore_request_id: int,
) -> RestoreRequest:
    row = await get_restore_request(session, restore_request_id)
    if row.status == "queued":
        row.status = "failed"
        row.notes = "Không đưa được yêu cầu khôi phục vào hàng đợi xử lý."
        row.updated_at = _utcnow()
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


async def run_restore_request(
    session: AsyncSession,
    *,
    restore_request_id: int,
    runner: RestoreRunner = execute_restore_request,
) -> RestoreRequest:
    row = await get_restore_request(session, restore_request_id)
    if row.status != "queued":
        return row

    now = _utcnow()
    row.status = "running"
    row.updated_at = now
    session.add(row)
    await session.commit()

    try:
        result_or_awaitable = runner(session, row, now)
        result = await result_or_awaitable if inspect.isawaitable(result_or_awaitable) else result_or_awaitable
        finished_at = _utcnow()
        row.status = result.status
        row.notes = result.notes
        row.updated_at = finished_at
    except Exception as exc:
        finished_at = _utcnow()
        row.status = "failed"
        row.notes = _sanitize_validation_message(str(exc))
        row.updated_at = finished_at

    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def run_backup_job(
    session: AsyncSession,
    *,
    job_id: int,
    runner: BackupRunner = run_backup,
) -> BackupJob:
    row = (
        await session.execute(select(BackupJob).where(BackupJob.id == job_id))
    ).scalar_one_or_none()
    if row is None:
        raise BackupJobNotFound(job_id)
    if row.status != "queued":
        return row

    config = await get_backup_config_row(session, row.kind)
    now = _utcnow()
    row.status = "running"
    row.started_at = now
    row.updated_at = now
    session.add(row)
    await session.commit()

    try:
        result_or_awaitable = runner(session, config, now)
        result = await result_or_awaitable if inspect.isawaitable(result_or_awaitable) else result_or_awaitable
        finished_at = _utcnow()
        row.status = "success"
        row.artifact_key = result.artifact_key
        row.artifact_bucket = result.artifact_bucket
        row.artifact_size_bytes = result.artifact_size_bytes
        row.object_count = result.object_count
        row.error_summary = None
        row.log_excerpt = result.log_excerpt
        row.finished_at = finished_at
        row.updated_at = finished_at
    except Exception as exc:
        finished_at = _utcnow()
        row.status = "failed"
        row.error_summary = _sanitize_validation_message(str(exc))
        row.log_excerpt = "Tác vụ sao lưu thất bại. Xem lỗi rút gọn trong error_summary."
        row.finished_at = finished_at
        row.updated_at = finished_at

    session.add(row)
    await session.commit()
    await session.refresh(row)
    await _send_backup_job_notification(session, config=config, row=row)
    return row


async def _run_backup_set_child(
    session: AsyncSession,
    *,
    job_id: int | None,
    runner: BackupRunner,
) -> BackupJob:
    if job_id is None:
        raise BackupJobNotFound("missing")
    row = await run_backup_job(session, job_id=job_id, runner=runner)
    if row.status != "success":
        raise RuntimeError(row.error_summary or f"Sao lưu {KIND_LABELS.get(row.kind, row.kind)} thất bại.")
    return row


async def run_backup_set(
    session: AsyncSession,
    *,
    backup_set_id: int,
    runner: BackupRunner = run_backup,
) -> BackupSet:
    row = await session.get(BackupSet, backup_set_id)
    if row is None:
        raise BackupSetNotFound(backup_set_id)
    if row.status != "queued":
        return row

    now = _utcnow()
    row.status = "running"
    row.started_at = now
    row.updated_at = now
    session.add(row)
    await session.commit()

    try:
        await _run_backup_set_child(session, job_id=row.db_job_id, runner=runner)
        await _run_backup_set_child(session, job_id=row.object_job_id, runner=runner)
        finished_at = _utcnow()
        row.status = "success"
        row.error_summary = None
        row.finished_at = finished_at
        row.updated_at = finished_at
    except Exception as exc:
        finished_at = _utcnow()
        row.status = "failed"
        row.error_summary = _sanitize_validation_message(str(exc))
        row.finished_at = finished_at
        row.updated_at = finished_at

    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


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
    backup_sets = (
        await session.execute(
            select(BackupSet).order_by(BackupSet.created_at.desc()).limit(5)
        )
    ).scalars().all()

    return BackupOverviewResponse(
        config_count=len(configs),
        configs=configs,
        latest_jobs=_job_summaries(jobs),
        latest_backup_sets=await _backup_set_summaries(session, backup_sets),
        latest_restore_requests=_restore_summaries(restore_requests),
    )
