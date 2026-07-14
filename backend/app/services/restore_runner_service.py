from __future__ import annotations

import asyncio
from dataclasses import dataclass
import gzip
from io import BytesIO
import os

from minio import Minio
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession
from urllib3 import PoolManager, Timeout

from app.core.config import settings
from app.models.backup import BackupJob, RestoreRequest


@dataclass(frozen=True)
class RestoreRunResult:
    status: str
    notes: str


def _normalize_endpoint(raw: str | None) -> str:
    return (raw or "").strip().replace("http://", "").replace("https://", "").rstrip("/")


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
            timeout=Timeout(connect=5.0, read=180.0),
            retries=False,
        ),
    )


def _backup_target_client() -> Minio:
    return _minio_client(
        _normalize_endpoint(settings.BACKUP_STORAGE_ENDPOINT),
        settings.BACKUP_STORAGE_ACCESS_KEY.strip(),
        settings.BACKUP_STORAGE_SECRET_KEY.strip(),
        settings.BACKUP_STORAGE_SECURE,
    )


def _source_client() -> Minio:
    return _minio_client(
        _normalize_endpoint(settings.SOURCE_STORAGE_ENDPOINT or settings.MINIO_ENDPOINT),
        (settings.SOURCE_STORAGE_ACCESS_KEY or settings.MINIO_ACCESS_KEY).strip(),
        (settings.SOURCE_STORAGE_SECRET_KEY or settings.MINIO_SECRET_KEY).strip(),
        _source_secure_fallback(),
    )


async def _snapshot_job(session: AsyncSession, kind: str, artifact_key: str) -> BackupJob:
    row = (
        await session.execute(
            select(BackupJob)
            .where(BackupJob.kind == kind)
            .where(BackupJob.status == "success")
            .where(BackupJob.artifact_key == artifact_key)
            .order_by(BackupJob.created_at.desc())
        )
    ).scalars().first()
    if row is None:
        raise RuntimeError("Không tìm thấy artifact sao lưu để khôi phục.")
    if not row.artifact_bucket:
        raise RuntimeError("Artifact sao lưu thiếu thông tin kho lưu trữ.")
    return row


def _read_backup_object(bucket: str, object_name: str) -> bytes:
    client = _backup_target_client()
    response = client.get_object(bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def _dump_payload(bucket: str, object_name: str) -> bytes:
    raw = _read_backup_object(bucket, object_name)
    if object_name.endswith(".gz"):
        try:
            return gzip.decompress(raw)
        except gzip.BadGzipFile as exc:
            raise RuntimeError("Artifact cơ sở dữ liệu không phải file gzip hợp lệ.") from exc
    return raw


def _prepare_sql_dump_for_restore(payload: bytes) -> bytes:
    # pg_dump mới hơn có thể sinh directive này, nhưng server PostgreSQL cũ hơn
    # không nhận tham số transaction_timeout. Dòng này chỉ đặt cấu hình phiên.
    unsupported_prefixes = (b"SET transaction_timeout ",)
    return b"".join(
        line
        for line in payload.splitlines(keepends=True)
        if not line.lstrip().startswith(unsupported_prefixes)
    )


async def _verify_db_snapshot(session: AsyncSession, request: RestoreRequest) -> str:
    if not request.db_artifact_key:
        raise RuntimeError("Thiếu artifact cơ sở dữ liệu.")
    job = await _snapshot_job(session, "db", request.db_artifact_key)
    payload = await asyncio.to_thread(_dump_payload, job.artifact_bucket, job.artifact_key)
    payload = _prepare_sql_dump_for_restore(payload)
    if not payload.strip():
        raise RuntimeError("Artifact cơ sở dữ liệu rỗng.")
    return "Đã kiểm tra artifact cơ sở dữ liệu."


def _pg_command_base() -> tuple[list[str], dict[str, str]]:
    url = make_url(settings.DATABASE_URL)
    command: list[str] = []
    if url.host:
        command.extend(["-h", url.host])
    if url.port:
        command.extend(["-p", str(url.port)])
    if url.username:
        command.extend(["-U", url.username])

    env = {**os.environ, "PGCONNECT_TIMEOUT": "10"}
    if url.password:
        env["PGPASSWORD"] = url.password
    return command, env


async def _run_pg_client(command: list[str], env: dict[str, str], stdin: bytes | None = None) -> tuple[int, str]:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE if stdin is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await process.communicate(stdin)
    detail = (stderr or stdout).decode("utf-8", errors="replace").strip()
    return process.returncode, detail


async def _restore_db_snapshot(session: AsyncSession, request: RestoreRequest) -> str:
    if not request.db_artifact_key:
        raise RuntimeError("Thiếu artifact cơ sở dữ liệu.")
    if not request.target_db_name:
        raise RuntimeError("Thiếu cơ sở dữ liệu đích mới.")

    job = await _snapshot_job(session, "db", request.db_artifact_key)
    payload = await asyncio.to_thread(_dump_payload, job.artifact_bucket, job.artifact_key)
    payload = _prepare_sql_dump_for_restore(payload)
    if not payload.strip():
        raise RuntimeError("Artifact cơ sở dữ liệu rỗng.")

    pg_base, env = _pg_command_base()
    createdb_command = ["createdb", *pg_base, request.target_db_name]
    returncode, detail = await _run_pg_client(createdb_command, env)
    if returncode != 0:
        raise RuntimeError(f"Không tạo được cơ sở dữ liệu đích mới: {detail or 'createdb thất bại'}")

    psql_command = [
        "psql",
        *pg_base,
        "--set",
        "ON_ERROR_STOP=on",
        "-d",
        request.target_db_name,
    ]
    returncode, detail = await _run_pg_client(psql_command, env, payload)
    if returncode != 0:
        raise RuntimeError(f"Không khôi phục được cơ sở dữ liệu đích mới: {detail or 'psql thất bại'}")

    return f"Đã khôi phục cơ sở dữ liệu vào đích mới {request.target_db_name}."


async def _verify_object_snapshot(session: AsyncSession, request: RestoreRequest) -> str:
    if not request.object_snapshot_key:
        raise RuntimeError("Thiếu snapshot kho tệp ứng dụng.")
    job = await _snapshot_job(session, "object_storage", request.object_snapshot_key)
    client = _backup_target_client()
    manifest_key = f"{job.artifact_key.rstrip('/')}/manifest.json"
    await asyncio.to_thread(client.stat_object, job.artifact_bucket, manifest_key)
    objects = await asyncio.to_thread(
        lambda: list(client.list_objects(job.artifact_bucket, prefix=f"{job.artifact_key.rstrip('/')}/", recursive=True))
    )
    if not objects:
        raise RuntimeError("Snapshot kho tệp ứng dụng không có object nào.")
    return "Đã kiểm tra snapshot kho tệp ứng dụng."


def _restore_object_snapshot_sync(job: BackupJob, target_bucket: str) -> tuple[int, int]:
    backup_client = _backup_target_client()
    target_client = _source_client()
    if target_client.bucket_exists(target_bucket):
        raise RuntimeError("Kho tệp đích đã tồn tại; hãy chọn kho mới.")
    target_client.make_bucket(target_bucket)

    snapshot_prefix = job.artifact_key.rstrip("/")
    copied = 0
    total_size = 0
    for item in backup_client.list_objects(job.artifact_bucket, prefix=f"{snapshot_prefix}/", recursive=True):
        if not item.object_name:
            continue
        relative_name = item.object_name[len(snapshot_prefix) + 1:]
        if not relative_name or relative_name == "manifest.json":
            continue

        response = backup_client.get_object(job.artifact_bucket, item.object_name)
        try:
            size = item.size or 0
            target_client.put_object(
                target_bucket,
                relative_name,
                response,
                length=size,
                content_type=getattr(item, "content_type", None) or "application/octet-stream",
            )
            copied += 1
            total_size += size
        finally:
            response.close()
            response.release_conn()

    if copied == 0:
        raise RuntimeError("Snapshot kho tệp ứng dụng không có object dữ liệu để khôi phục.")
    return copied, total_size


async def _restore_object_snapshot(session: AsyncSession, request: RestoreRequest) -> str:
    if not request.object_snapshot_key:
        raise RuntimeError("Thiếu snapshot kho tệp ứng dụng.")
    if not request.target_bucket:
        raise RuntimeError("Thiếu kho tệp đích mới.")
    job = await _snapshot_job(session, "object_storage", request.object_snapshot_key)
    copied, total_size = await asyncio.to_thread(_restore_object_snapshot_sync, job, request.target_bucket)
    return f"Đã khôi phục {copied} tệp vào kho mới {request.target_bucket}, tổng {total_size} byte."


async def run_restore_request(session: AsyncSession, request: RestoreRequest, now) -> RestoreRunResult:
    notes: list[str] = []
    if request.mode == "verify_only":
        if request.kind in {"db", "full"}:
            notes.append(await _verify_db_snapshot(session, request))
        if request.kind in {"object_storage", "full"}:
            notes.append(await _verify_object_snapshot(session, request))
        return RestoreRunResult(status="verified", notes=" ".join(notes))

    if request.mode == "restore_to_new_target":
        if request.kind in {"db", "full"}:
            notes.append(await _restore_db_snapshot(session, request))
        if request.kind in {"object_storage", "full"}:
            notes.append(await _restore_object_snapshot(session, request))
        return RestoreRunResult(status="restored", notes=" ".join(notes))

    raise RuntimeError("Chế độ khôi phục không hợp lệ.")
