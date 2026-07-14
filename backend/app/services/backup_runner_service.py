from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
import gzip
import json
import os
from pathlib import Path
import shutil
import tempfile

from fastapi.encoders import jsonable_encoder
from minio import Minio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession
from urllib3 import PoolManager, Timeout

from app.core.config import settings
from app.models.backup import BackupConfig

BACKUP_STREAM_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class BackupRunResult:
    artifact_key: str
    artifact_bucket: str
    artifact_size_bytes: int
    object_count: int | None = None
    log_excerpt: str | None = None


def _timestamp(now: datetime) -> str:
    return now.strftime("%Y%m%d_%H%M%S")


def _join_object_key(prefix: str | None, name: str) -> str:
    cleaned = (prefix or "").strip("/")
    return f"{cleaned}/{name}" if cleaned else name


def _normalize_endpoint(raw: str | None) -> str:
    return (raw or "").strip().replace("http://", "").replace("https://", "").rstrip("/")


def _target_values(config: BackupConfig) -> tuple[str, str, bool]:
    endpoint = _normalize_endpoint(config.target_endpoint or settings.BACKUP_STORAGE_ENDPOINT)
    bucket = (config.target_bucket or settings.BACKUP_STORAGE_BUCKET).strip()
    secure = config.target_secure
    return endpoint, bucket, secure


def _source_values(config: BackupConfig) -> tuple[str, str, bool, str, str]:
    endpoint = _normalize_endpoint(
        config.source_endpoint
        or settings.SOURCE_STORAGE_ENDPOINT
        or settings.MINIO_ENDPOINT
    )
    bucket = (
        config.source_bucket
        or settings.MINIO_BUCKET
        or settings.minio_bucket_name
    ).strip()
    secure = (
        config.source_secure
        if config.source_secure is not None
        else _source_secure_fallback()
    )
    access_key = (settings.SOURCE_STORAGE_ACCESS_KEY or settings.MINIO_ACCESS_KEY).strip()
    secret_key = (settings.SOURCE_STORAGE_SECRET_KEY or settings.MINIO_SECRET_KEY).strip()
    return endpoint, bucket, secure, access_key, secret_key


def _source_secure_fallback() -> bool:
    raw = settings.SOURCE_STORAGE_SECURE.strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return settings.MINIO_SECURE


def _minio_client(endpoint: str, access_key: str, secret_key: str, secure: bool) -> Minio:
    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
        http_client=PoolManager(
            timeout=Timeout(connect=5.0, read=120.0),
            retries=False,
        ),
    )


def _target_client(config: BackupConfig) -> tuple[Minio, str]:
    endpoint, bucket, secure = _target_values(config)
    client = _minio_client(
        endpoint,
        settings.BACKUP_STORAGE_ACCESS_KEY.strip(),
        settings.BACKUP_STORAGE_SECRET_KEY.strip(),
        secure,
    )
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    return client, bucket


def _backup_temp_dir() -> Path:
    path = Path(settings.BACKUP_TEMP_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _temporary_backup_path(*, prefix: str, suffix: str) -> Path:
    fd, raw_path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=_backup_temp_dir())
    os.close(fd)
    return Path(raw_path)


def _put_bytes(config: BackupConfig, object_name: str, payload: bytes, content_type: str) -> BackupRunResult:
    client, bucket = _target_client(config)
    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=BytesIO(payload),
        length=len(payload),
        content_type=content_type,
    )
    return BackupRunResult(
        artifact_key=object_name,
        artifact_bucket=bucket,
        artifact_size_bytes=len(payload),
    )


def _put_file(config: BackupConfig, object_name: str, path: Path, content_type: str) -> BackupRunResult:
    client, bucket = _target_client(config)
    length = path.stat().st_size
    with path.open("rb") as data:
        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=data,
            length=length,
            content_type=content_type,
        )
    return BackupRunResult(
        artifact_key=object_name,
        artifact_bucket=bucket,
        artifact_size_bytes=length,
    )


def _pg_dump_command_and_env() -> tuple[list[str], dict[str, str]]:
    url = make_url(settings.DATABASE_URL)
    command = [
        "pg_dump",
        "--no-owner",
        "--no-privileges",
    ]
    if url.host:
        command.extend(["-h", url.host])
    if url.port:
        command.extend(["-p", str(url.port)])
    if url.username:
        command.extend(["-U", url.username])
    if url.database:
        command.append(url.database)

    env = {**os.environ, "PGCONNECT_TIMEOUT": "10"}
    if url.password:
        env["PGPASSWORD"] = url.password
    return command, env


async def _copy_async_reader(reader, writer) -> None:
    while True:
        chunk = await reader.read(BACKUP_STREAM_CHUNK_SIZE)
        if not chunk:
            return
        writer.write(chunk)


async def _run_pg_dump_backup(config: BackupConfig, now: datetime) -> BackupRunResult:
    command, env = _pg_dump_command_and_env()
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    object_name = _join_object_key(
        config.target_prefix,
        f"hrms_{_timestamp(now)}.sql.gz",
    )
    output_path = _temporary_backup_path(prefix="hrms-db-", suffix=".sql.gz")
    stderr_path = _temporary_backup_path(prefix="hrms-db-", suffix=".stderr")
    try:
        if process.stdout is None or process.stderr is None:
            raise RuntimeError("Không mở được stream pg_dump.")

        with gzip.open(output_path, "wb", compresslevel=9) as gz_file, stderr_path.open("wb") as stderr_file:
            stdout_task = asyncio.create_task(_copy_async_reader(process.stdout, gz_file))
            stderr_task = asyncio.create_task(_copy_async_reader(process.stderr, stderr_file))
            returncode = await process.wait()
            await stdout_task
            await stderr_task

        if returncode != 0:
            detail = stderr_path.read_text(encoding="utf-8", errors="replace").strip() or "pg_dump thất bại"
            raise RuntimeError(detail)

        if not output_path.exists() or output_path.stat().st_size <= 0:
            raise RuntimeError("pg_dump không tạo được dữ liệu sao lưu.")

        result = _put_file(config, object_name, output_path, "application/gzip")
    finally:
        output_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)

    return BackupRunResult(
        artifact_key=result.artifact_key,
        artifact_bucket=result.artifact_bucket,
        artifact_size_bytes=result.artifact_size_bytes,
        object_count=result.object_count,
        log_excerpt="Đã tạo bản sao lưu cơ sở dữ liệu bằng pg_dump.",
    )


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


async def _write_json_db_snapshot(session: AsyncSession, now: datetime, writer) -> None:
    table_result = await session.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """))
    tables = list(table_result.scalars().all())

    writer.write(json.dumps({
        "format": "hrms-db-jsonl-v1",
        "created_at": now.isoformat(),
        "table_count": len(tables),
    }, ensure_ascii=False) + "\n")

    for table_name in tables:
        quoted = _quote_identifier(table_name)
        rows = await session.stream(text(f"SELECT to_jsonb(t) AS data FROM public.{quoted} AS t"))
        async for row in rows:
            writer.write(json.dumps({
                "table": table_name,
                "row": jsonable_encoder(row[0]),
            }, ensure_ascii=False, default=str) + "\n")


async def _run_json_db_backup(session: AsyncSession, config: BackupConfig, now: datetime) -> BackupRunResult:
    object_name = _join_object_key(
        config.target_prefix,
        f"hrms_{_timestamp(now)}.jsonl.gz",
    )
    output_path = _temporary_backup_path(prefix="hrms-db-json-", suffix=".jsonl.gz")
    try:
        with gzip.open(output_path, "wt", encoding="utf-8", compresslevel=9) as gz_file:
            await _write_json_db_snapshot(session, now, gz_file)

        if not output_path.exists() or output_path.stat().st_size <= 0:
            raise RuntimeError("Không tạo được dữ liệu snapshot JSONL.")

        result = _put_file(config, object_name, output_path, "application/gzip")
    finally:
        output_path.unlink(missing_ok=True)

    return BackupRunResult(
        artifact_key=result.artifact_key,
        artifact_bucket=result.artifact_bucket,
        artifact_size_bytes=result.artifact_size_bytes,
        object_count=result.object_count,
        log_excerpt="Không tìm thấy pg_dump trong image; đã tạo snapshot JSONL bằng ứng dụng.",
    )


async def run_database_backup(session: AsyncSession, config: BackupConfig, now: datetime) -> BackupRunResult:
    if shutil.which("pg_dump"):
        return await _run_pg_dump_backup(config, now)
    return await _run_json_db_backup(session, config, now)


def _run_object_storage_backup_sync(config: BackupConfig, now: datetime) -> BackupRunResult:
    source_endpoint, source_bucket, source_secure, source_access_key, source_secret_key = _source_values(config)
    source_client = _minio_client(
        source_endpoint,
        source_access_key,
        source_secret_key,
        source_secure,
    )
    target_client, target_bucket = _target_client(config)

    if not source_client.bucket_exists(source_bucket):
        raise RuntimeError("Không tìm thấy kho lưu trữ nguồn để sao lưu.")

    snapshot_prefix = _join_object_key(
        config.target_prefix,
        f"files-{_timestamp(now)}",
    )
    skipped_prefix = (config.target_prefix or "").strip("/")
    copied = 0
    total_size = 0

    for item in source_client.list_objects(source_bucket, recursive=True):
        object_name = item.object_name
        if source_bucket == target_bucket and skipped_prefix and object_name.startswith(f"{skipped_prefix}/"):
            continue

        response = source_client.get_object(source_bucket, object_name)
        try:
            size = item.size or 0
            target_client.put_object(
                bucket_name=target_bucket,
                object_name=f"{snapshot_prefix}/{object_name}",
                data=response,
                length=size,
                content_type=getattr(item, "content_type", None) or "application/octet-stream",
            )
            copied += 1
            total_size += size
        finally:
            response.close()
            response.release_conn()

    manifest = json.dumps({
        "format": "hrms-object-snapshot-v1",
        "created_at": now.isoformat(),
        "source_bucket": source_bucket,
        "object_count": copied,
        "total_size": total_size,
    }, ensure_ascii=False).encode("utf-8")
    manifest_key = f"{snapshot_prefix}/manifest.json"
    target_client.put_object(
        bucket_name=target_bucket,
        object_name=manifest_key,
        data=BytesIO(manifest),
        length=len(manifest),
        content_type="application/json",
    )

    return BackupRunResult(
        artifact_key=snapshot_prefix,
        artifact_bucket=target_bucket,
        artifact_size_bytes=total_size + len(manifest),
        object_count=copied,
        log_excerpt="Đã tạo snapshot kho tệp ứng dụng và manifest.",
    )


async def run_object_storage_backup(config: BackupConfig, now: datetime) -> BackupRunResult:
    return await asyncio.to_thread(_run_object_storage_backup_sync, config, now)


async def run_backup(session: AsyncSession, config: BackupConfig, now: datetime) -> BackupRunResult:
    if config.kind == "db":
        return await run_database_backup(session, config, now)
    if config.kind == "object_storage":
        return await run_object_storage_backup(config, now)
    raise RuntimeError("Loại cấu hình sao lưu không hợp lệ.")
