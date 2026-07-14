from __future__ import annotations

import asyncio
from dataclasses import dataclass
import gzip
from io import BytesIO
import json
import os
import time

from minio import Minio
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession
from urllib3 import PoolManager, Timeout

from app.core.config import settings
from app.models.backup import BackupJob, RestoreRequest

RESTORE_STREAM_CHUNK_SIZE = 1024 * 1024
OBJECT_RESTORE_MAX_ATTEMPTS = 3
RESTORE_MARKER_PREFIX = ".hrms-restore"


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


def _is_unsupported_pg_line(line: bytes) -> bool:
    unsupported_prefixes = (b"SET transaction_timeout ",)
    return line.lstrip().startswith(unsupported_prefixes)


def _prepare_sql_dump_for_restore(payload: bytes) -> bytes:
    # pg_dump mới hơn có thể sinh directive này, nhưng server PostgreSQL cũ hơn
    # không nhận tham số transaction_timeout. Dòng này chỉ đặt cấu hình phiên.
    return b"".join(
        line
        for line in payload.splitlines(keepends=True)
        if not _is_unsupported_pg_line(line)
    )


def _iter_backup_sql_lines(bucket: str, object_name: str):
    client = _backup_target_client()
    response = client.get_object(bucket, object_name)
    try:
        if object_name.endswith(".gz"):
            try:
                with gzip.GzipFile(fileobj=response) as gz_file:
                    yield from gz_file
            except gzip.BadGzipFile as exc:
                raise RuntimeError("Artifact cơ sở dữ liệu không phải file gzip hợp lệ.") from exc
            return

        pending = b""
        for chunk in response.stream(RESTORE_STREAM_CHUNK_SIZE):
            if not chunk:
                continue
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                yield line + b"\n"
        if pending:
            yield pending
    finally:
        response.close()
        response.release_conn()


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


async def _read_process_stream(reader: asyncio.StreamReader | None) -> bytes:
    if reader is None:
        return b""
    return await reader.read()


async def _stream_backup_sql_to_writer(bucket: str, object_name: str, writer: asyncio.StreamWriter) -> int:
    iterator = _iter_backup_sql_lines(bucket, object_name)
    sentinel = object()
    written = 0
    try:
        while True:
            line = await asyncio.to_thread(next, iterator, sentinel)
            if line is sentinel:
                break
            if not isinstance(line, bytes):
                continue
            if _is_unsupported_pg_line(line):
                continue
            if not line.strip():
                writer.write(line)
                await writer.drain()
                continue
            writer.write(line)
            await writer.drain()
            written += len(line)
    finally:
        await asyncio.to_thread(iterator.close)
    return written


async def _run_psql_with_backup_object(
    command: list[str],
    env: dict[str, str],
    bucket: str,
    object_name: str,
) -> tuple[int, str, int]:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout_task = asyncio.create_task(_read_process_stream(process.stdout))
    stderr_task = asyncio.create_task(_read_process_stream(process.stderr))

    try:
        if process.stdin is None:
            raise RuntimeError("Không mở được stdin cho psql.")
        bytes_written = await _stream_backup_sql_to_writer(bucket, object_name, process.stdin)
        process.stdin.close()
        await process.stdin.wait_closed()
    except Exception:
        if process.returncode is None:
            process.kill()
        await process.wait()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        raise

    returncode = await process.wait()
    stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
    detail = (stderr or stdout).decode("utf-8", errors="replace").strip()
    return returncode, detail, bytes_written


async def _restore_sql_object_to_database(
    bucket: str,
    object_name: str,
    target_db_name: str,
    env: dict[str, str],
) -> int:
    pg_base, _ = _pg_command_base()
    psql_command = [
        "psql",
        *pg_base,
        "--set",
        "ON_ERROR_STOP=on",
        "-d",
        target_db_name,
    ]
    returncode, detail, bytes_written = await _run_psql_with_backup_object(
        psql_command,
        env,
        bucket,
        object_name,
    )
    if bytes_written <= 0:
        raise RuntimeError("Artifact cơ sở dữ liệu rỗng.")
    if returncode != 0:
        raise RuntimeError(f"Không khôi phục được cơ sở dữ liệu đích mới: {detail or 'psql thất bại'}")
    return bytes_written


def _verify_database_name(request: RestoreRequest, now) -> str:
    raw_id = request.id or 0
    raw_timestamp = int(getattr(now, "timestamp", lambda: time.time())())
    return f"hrms_restore_verify_{raw_id}_{raw_timestamp}"[:63]


async def _drop_database_if_exists(db_name: str, pg_base: list[str], env: dict[str, str]) -> tuple[int, str]:
    return await _run_pg_client(["dropdb", "--if-exists", *pg_base, db_name], env)


async def _verify_db_snapshot(session: AsyncSession, request: RestoreRequest, now) -> str:
    if not request.db_artifact_key:
        raise RuntimeError("Thiếu artifact cơ sở dữ liệu.")
    job = await _snapshot_job(session, "db", request.db_artifact_key)
    target_db_name = _verify_database_name(request, now)
    pg_base, env = _pg_command_base()
    createdb_command = ["createdb", *pg_base, target_db_name]
    returncode, detail = await _run_pg_client(createdb_command, env)
    if returncode != 0:
        raise RuntimeError(f"Không tạo được cơ sở dữ liệu kiểm tra tạm: {detail or 'createdb thất bại'}")

    try:
        await _restore_sql_object_to_database(job.artifact_bucket, job.artifact_key, target_db_name, env)
    finally:
        drop_returncode, drop_detail = await _drop_database_if_exists(target_db_name, pg_base, env)
        if drop_returncode != 0:
            raise RuntimeError(f"Không dọn được cơ sở dữ liệu kiểm tra tạm: {drop_detail or 'dropdb thất bại'}")

    return "Đã kiểm tra artifact cơ sở dữ liệu bằng restore thử vào cơ sở dữ liệu tạm."


async def _restore_db_snapshot(session: AsyncSession, request: RestoreRequest) -> str:
    if not request.db_artifact_key:
        raise RuntimeError("Thiếu artifact cơ sở dữ liệu.")
    if not request.target_db_name:
        raise RuntimeError("Thiếu cơ sở dữ liệu đích mới.")

    job = await _snapshot_job(session, "db", request.db_artifact_key)

    pg_base, env = _pg_command_base()
    createdb_command = ["createdb", *pg_base, request.target_db_name]
    returncode, detail = await _run_pg_client(createdb_command, env)
    if returncode != 0:
        raise RuntimeError(f"Không tạo được cơ sở dữ liệu đích mới: {detail or 'createdb thất bại'}")

    try:
        await _restore_sql_object_to_database(job.artifact_bucket, job.artifact_key, request.target_db_name, env)
    except Exception:
        await _drop_database_if_exists(request.target_db_name, pg_base, env)
        raise

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


def _restore_marker_key(request_id: int | None) -> str:
    return f"{RESTORE_MARKER_PREFIX}/request-{request_id or 0}.json"


def _put_restore_marker(client: Minio, bucket: str, request_id: int | None, job: BackupJob, status: str) -> None:
    payload = json.dumps(
        {
            "format": "hrms-object-restore-v1",
            "restore_request_id": request_id,
            "source_bucket": job.artifact_bucket,
            "source_prefix": job.artifact_key,
            "status": status,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    client.put_object(
        bucket,
        _restore_marker_key(request_id),
        BytesIO(payload),
        len(payload),
        content_type="application/json",
    )


def _ensure_restore_target_bucket(target_client: Minio, target_bucket: str, request_id: int | None) -> None:
    marker_key = _restore_marker_key(request_id)
    if not target_client.bucket_exists(target_bucket):
        target_client.make_bucket(target_bucket)
        return
    try:
        target_client.stat_object(target_bucket, marker_key)
    except Exception as exc:
        raise RuntimeError("Kho tệp đích đã tồn tại; hãy chọn kho mới.") from exc


def _copy_restore_object_with_retry(
    backup_client: Minio,
    target_client: Minio,
    source_bucket: str,
    source_object: str,
    target_bucket: str,
    target_object: str,
    size: int,
    content_type: str,
) -> None:
    last_exc: Exception | None = None
    for attempt in range(1, OBJECT_RESTORE_MAX_ATTEMPTS + 1):
        response = None
        try:
            response = backup_client.get_object(source_bucket, source_object)
            target_client.put_object(
                target_bucket,
                target_object,
                response,
                length=size,
                content_type=content_type,
            )
            return
        except Exception as exc:
            last_exc = exc
            if attempt >= OBJECT_RESTORE_MAX_ATTEMPTS:
                break
            time.sleep(min(attempt, 3))
        finally:
            if response is not None:
                response.close()
                response.release_conn()
    raise RuntimeError(f"Không copy được tệp {target_object} sau {OBJECT_RESTORE_MAX_ATTEMPTS} lần thử.") from last_exc


def _restore_object_snapshot_sync(job: BackupJob, target_bucket: str, request_id: int | None) -> tuple[int, int]:
    backup_client = _backup_target_client()
    target_client = _source_client()
    _ensure_restore_target_bucket(target_client, target_bucket, request_id)
    _put_restore_marker(target_client, target_bucket, request_id, job, "running")

    snapshot_prefix = job.artifact_key.rstrip("/")
    copied = 0
    total_size = 0
    for item in backup_client.list_objects(job.artifact_bucket, prefix=f"{snapshot_prefix}/", recursive=True):
        if not item.object_name:
            continue
        relative_name = item.object_name[len(snapshot_prefix) + 1:]
        if not relative_name or relative_name == "manifest.json":
            continue

        size = item.size or 0
        _copy_restore_object_with_retry(
            backup_client,
            target_client,
            job.artifact_bucket,
            item.object_name,
            target_bucket,
            relative_name,
            size,
            getattr(item, "content_type", None) or "application/octet-stream",
        )
        copied += 1
        total_size += size

    if copied == 0:
        raise RuntimeError("Snapshot kho tệp ứng dụng không có object dữ liệu để khôi phục.")
    _put_restore_marker(target_client, target_bucket, request_id, job, "restored")
    return copied, total_size


async def _restore_object_snapshot(session: AsyncSession, request: RestoreRequest) -> str:
    if not request.object_snapshot_key:
        raise RuntimeError("Thiếu snapshot kho tệp ứng dụng.")
    if not request.target_bucket:
        raise RuntimeError("Thiếu kho tệp đích mới.")
    job = await _snapshot_job(session, "object_storage", request.object_snapshot_key)
    copied, total_size = await asyncio.to_thread(_restore_object_snapshot_sync, job, request.target_bucket, request.id)
    return f"Đã khôi phục {copied} tệp vào kho mới {request.target_bucket}, tổng {total_size} byte."


async def run_restore_request(session: AsyncSession, request: RestoreRequest, now) -> RestoreRunResult:
    notes: list[str] = []
    if request.mode == "verify_only":
        if request.kind in {"db", "full"}:
            notes.append(await _verify_db_snapshot(session, request, now))
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
