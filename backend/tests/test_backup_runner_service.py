from __future__ import annotations

import gzip
from datetime import datetime

import pytest

from app.core.config import settings
from app.models.backup import BackupConfig
from app.services import backup_runner_service


class _ChunkedReader:
    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks

    async def read(self, _size: int = -1) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class _ScalarsResult:
    def all(self) -> list[str]:
        return ["employees"]


class _TableResult:
    def scalars(self) -> _ScalarsResult:
        return _ScalarsResult()


class _AsyncRows:
    def __init__(self, rows: list[tuple[dict[str, object]]]):
        self._rows = rows

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._rows:
            raise StopAsyncIteration
        return self._rows.pop(0)


@pytest.mark.asyncio
async def test_database_backup_streams_pg_dump_without_buffering_full_dump(monkeypatch, tmp_path):
    dump_chunks = [
        b"CREATE TABLE employees(id integer);\n",
        b"INSERT INTO employees VALUES (1);\n",
    ]
    uploaded: dict[str, object] = {}

    class FakeProcess:
        stdout = _ChunkedReader(dump_chunks.copy())
        stderr = _ChunkedReader([])
        returncode: int | None = None

        async def wait(self) -> int:
            self.returncode = 0
            return 0

        async def communicate(self):
            raise AssertionError("communicate buffers the whole pg_dump output")

    class FakeTargetClient:
        def put_object(self, *, bucket_name, object_name, data, length, content_type):
            uploaded.update({
                "bucket_name": bucket_name,
                "object_name": object_name,
                "payload": data.read(),
                "length": length,
                "content_type": content_type,
            })

    async def fake_create_subprocess_exec(*_args, **_kwargs):
        return FakeProcess()

    monkeypatch.setattr(backup_runner_service.shutil, "which", lambda _name: "/usr/bin/pg_dump")
    monkeypatch.setattr(
        backup_runner_service.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )
    monkeypatch.setattr(
        backup_runner_service,
        "_target_client",
        lambda _config: (FakeTargetClient(), "hrms-backup"),
    )
    monkeypatch.setattr(settings, "BACKUP_TEMP_DIR", str(tmp_path), raising=False)

    config = BackupConfig(
        kind="db",
        enabled=True,
        cron_expression="0 2 * * *",
        retention_days=90,
        target_bucket="hrms-backup",
        target_prefix="postgres",
        target_secure=False,
    )

    result = await backup_runner_service.run_database_backup(
        None,
        config,
        datetime(2026, 7, 14, 1, 0, 0),
    )

    assert result.artifact_key == "postgres/hrms_20260714_010000.sql.gz"
    assert result.artifact_bucket == "hrms-backup"
    assert result.artifact_size_bytes == uploaded["length"]
    assert uploaded["content_type"] == "application/gzip"
    assert gzip.decompress(uploaded["payload"]) == b"".join(dump_chunks)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_database_json_fallback_streams_temp_file_without_full_gzip_buffer(monkeypatch, tmp_path):
    uploaded: dict[str, object] = {}

    class FakeSession:
        async def execute(self, _statement):
            return _TableResult()

        async def stream(self, _statement):
            return _AsyncRows([
                ({"id": 1, "name": "Nguyen Van A"},),
                ({"id": 2, "name": "Tran Thi B"},),
            ])

    class FakeTargetClient:
        def put_object(self, *, bucket_name, object_name, data, length, content_type):
            uploaded.update({
                "bucket_name": bucket_name,
                "object_name": object_name,
                "payload": data.read(),
                "length": length,
                "content_type": content_type,
            })

    def fail_gzip_compress(*_args, **_kwargs):
        raise AssertionError("gzip.compress buffers the whole JSON fallback output")

    monkeypatch.setattr(backup_runner_service.shutil, "which", lambda _name: None)
    monkeypatch.setattr(backup_runner_service.gzip, "compress", fail_gzip_compress)
    monkeypatch.setattr(
        backup_runner_service,
        "_target_client",
        lambda _config: (FakeTargetClient(), "hrms-backup"),
    )
    monkeypatch.setattr(settings, "BACKUP_TEMP_DIR", str(tmp_path), raising=False)

    config = BackupConfig(
        kind="db",
        enabled=True,
        cron_expression="0 2 * * *",
        retention_days=90,
        target_bucket="hrms-backup",
        target_prefix="postgres",
        target_secure=False,
    )

    result = await backup_runner_service.run_database_backup(
        FakeSession(),
        config,
        datetime(2026, 7, 14, 1, 0, 0),
    )

    payload = gzip.decompress(uploaded["payload"]).decode("utf-8")

    assert result.artifact_key == "postgres/hrms_20260714_010000.jsonl.gz"
    assert result.artifact_bucket == "hrms-backup"
    assert result.artifact_size_bytes == uploaded["length"]
    assert uploaded["content_type"] == "application/gzip"
    assert '"format": "hrms-db-jsonl-v1"' in payload
    assert '"table": "employees"' in payload
    assert "Nguyen Van A" in payload
    assert list(tmp_path.iterdir()) == []
