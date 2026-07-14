"""Integration tests cho Backup & Restore Admin Console."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.backup import BackupJob
from app.services import backup_notification_service, backup_service
from app.services.backup_runner_service import BackupRunResult
from app.services.restore_runner_service import RestoreRunResult, _prepare_sql_dump_for_restore

BASE = "/api/v1/backups"

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"
_LINE_MANAGER_EMAIL = "linemanager@hrms.local"


def _bearer_for(client: TestClient, email: str) -> dict[str, str]:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient) -> dict[str, str]:
    return _bearer_for(client, _ADMIN_EMAIL)


def _line_manager(client: TestClient) -> dict[str, str]:
    return _bearer_for(client, _LINE_MANAGER_EMAIL)


def _configs(client: TestClient, headers: dict[str, str]) -> list[dict]:
    resp = client.get(f"{BASE}/config", headers=headers)
    assert resp.status_code == 200
    return resp.json()


def _config(client: TestClient, headers: dict[str, str], kind: str = "db") -> dict:
    return next(item for item in _configs(client, headers) if item["kind"] == kind)


def _update_payload(config: dict) -> dict:
    return {
        "enabled": config["enabled"],
        "cron_expression": config["cron_expression"],
        "retention_days": config["retention_days"],
        "source_endpoint": config["source_endpoint"],
        "source_bucket": config["source_bucket"],
        "source_secure": config["source_secure"],
        "target_endpoint": config["target_endpoint"],
        "target_bucket": config["target_bucket"],
        "target_prefix": config["target_prefix"],
        "target_secure": config["target_secure"],
        "notify_emails": config["notify_emails"],
    }


async def _with_isolated_session(work):
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    Session = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with Session() as session:
            return await work(session)
    finally:
        await engine.dispose()


async def _insert_successful_backup_job(kind: str, artifact_key: str, *, object_count: int | None = None) -> int:
    async def work(session):
        row = BackupJob(
            kind=kind,
            trigger="manual",
            status="success",
            artifact_key=artifact_key,
            artifact_bucket="hrms-backup",
            artifact_size_bytes=321,
            object_count=object_count,
            log_excerpt="Artifact kiểm thử.",
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row.id

    return await _with_isolated_session(work)


def test_backup_config_requires_backup_permission(client: TestClient):
    resp = client.get(f"{BASE}/config", headers=_line_manager(client))
    assert resp.status_code == 403


def test_backup_config_lists_db_and_object_storage_without_secrets(client: TestClient):
    resp = client.get(f"{BASE}/config", headers=_admin(client))
    assert resp.status_code == 200

    data = resp.json()
    assert {item["kind"] for item in data} == {"db", "object_storage"}
    assert all(item["secret_source"] == "env" for item in data)

    serialized = str(data).lower()
    assert "access_key" not in serialized
    assert "secret_key" not in serialized
    assert "password" not in serialized


def test_backup_overview_contract(client: TestClient):
    resp = client.get(f"{BASE}/overview", headers=_admin(client))
    assert resp.status_code == 200

    data = resp.json()
    assert data["config_count"] == 2
    assert {item["kind"] for item in data["configs"]} == {"db", "object_storage"}
    assert isinstance(data["latest_jobs"], list)
    assert isinstance(data["latest_restore_requests"], list)


def test_backup_meta_contract(client: TestClient):
    resp = client.get(f"{BASE}/meta", headers=_admin(client))
    assert resp.status_code == 200

    data = resp.json()
    assert [item["code"] for item in data["kinds"]] == ["db", "object_storage"]
    assert [item["code"] for item in data["job_statuses"]] == [
        "queued",
        "running",
        "success",
        "failed",
        "cancelled",
    ]


def test_restore_runner_ignores_unsupported_pg_dump_session_setting():
    payload = (
        b"SET statement_timeout = 0;\n"
        b"SET transaction_timeout = 0;\n"
        b"CREATE TABLE public.example (id integer);\n"
    )

    prepared = _prepare_sql_dump_for_restore(payload)

    assert b"SET statement_timeout = 0;" in prepared
    assert b"SET transaction_timeout" not in prepared
    assert b"CREATE TABLE public.example" in prepared


def test_audit_log_meta_includes_backup_entities(client: TestClient):
    resp = client.get("/api/v1/audit-logs/meta", headers=_admin(client))
    assert resp.status_code == 200

    entity_codes = {item["code"] for item in resp.json()["entity_types"]}
    assert {"backup_config", "backup_job", "restore_request"}.issubset(entity_codes)


def test_update_backup_config_requires_edit_permission(client: TestClient):
    admin_headers = _admin(client)
    payload = _update_payload(_config(client, admin_headers, "db"))

    resp = client.put(f"{BASE}/config/db", json=payload, headers=_line_manager(client))

    assert resp.status_code == 403


def test_admin_updates_backup_config_and_writes_safe_audit_log(client: TestClient):
    headers = _admin(client)
    original = _config(client, headers, "db")
    original_payload = _update_payload(original)
    unique_prefix = f"pytest-slice4-{uuid4().hex[:8]}"
    payload = {
        **original_payload,
        "enabled": True,
        "cron_expression": "15 4 * * *",
        "retention_days": 37 if original["retention_days"] != 37 else 38,
        "target_bucket": "hrms-backup",
        "target_prefix": unique_prefix,
        "notify_emails": ["backup-admin@hrms.local"],
    }

    try:
        resp = client.put(f"{BASE}/config/db", json=payload, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["kind"] == "db"
        assert data["cron_expression"] == "15 4 * * *"
        assert data["retention_days"] == payload["retention_days"]
        assert data["target_prefix"] == unique_prefix
        assert data["notify_emails"] == ["backup-admin@hrms.local"]

        audit_resp = client.get(
            "/api/v1/audit-logs",
            params={
                "entity_type": "backup_config",
                "entity_id": data["id"],
                "action": "UPDATE",
                "page_size": 10,
            },
            headers=headers,
        )
        assert audit_resp.status_code == 200
        audit_items = audit_resp.json()["items"]
        matching = [
            item for item in audit_items
            if item["new_data"] and item["new_data"].get("target_prefix") == unique_prefix
        ]
        assert matching

        serialized_audit = str(matching[0]).lower()
        assert "access_key" not in serialized_audit
        assert "secret_key" not in serialized_audit
        assert "password" not in serialized_audit
    finally:
        client.put(f"{BASE}/config/db", json=original_payload, headers=headers)


def test_update_backup_config_validates_cron_retention_email_and_bucket(client: TestClient):
    headers = _admin(client)
    payload = _update_payload(_config(client, headers, "db"))

    cases = [
        {**payload, "cron_expression": "not a cron"},
        {**payload, "retention_days": 0},
        {**payload, "notify_emails": ["khong-phai-email"]},
        {**payload, "target_bucket": "Bad Bucket!"},
        {**payload, "target_prefix": "../escape"},
    ]

    for invalid_payload in cases:
        resp = client.put(f"{BASE}/config/db", json=invalid_payload, headers=headers)
        assert resp.status_code == 422


def test_validate_target_requires_edit_permission(client: TestClient):
    resp = client.post(
        f"{BASE}/validate-target",
        json={"kind": "db"},
        headers=_line_manager(client),
    )

    assert resp.status_code == 403


def test_validate_target_updates_validation_state_without_exposing_secrets(client: TestClient):
    headers = _admin(client)

    resp = client.post(f"{BASE}/validate-target", json={"kind": "db"}, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] == "db"
    assert data["status"] in {"success", "failed"}
    assert data["checked_at"]
    assert data["message"]

    config = _config(client, headers, "db")
    assert config["last_validated_at"] is not None
    assert config["last_validation_status"] == data["status"]

    serialized = str(data).lower()
    assert "access_key" not in serialized
    assert "secret_key" not in serialized
    assert "password" not in serialized


def test_create_manual_backup_job_requires_create_permission(client: TestClient):
    resp = client.post(
        f"{BASE}/jobs",
        json={"kind": "db"},
        headers=_line_manager(client),
    )

    assert resp.status_code == 403


def test_admin_creates_manual_backup_job_and_writes_safe_audit_log(client: TestClient):
    headers = _admin(client)

    resp = client.post(f"{BASE}/jobs", json={"kind": "db"}, headers=headers)

    assert resp.status_code == 201
    data = resp.json()
    assert data["kind"] == "db"
    assert data["trigger"] == "manual"
    assert data["status"] == "queued"
    assert data["created_at"]

    overview_resp = client.get(f"{BASE}/overview", headers=headers)
    assert overview_resp.status_code == 200
    overview_jobs = overview_resp.json()["latest_jobs"]
    assert any(item["id"] == data["id"] for item in overview_jobs)

    audit_resp = client.get(
        "/api/v1/audit-logs",
        params={
            "entity_type": "backup_job",
            "entity_id": data["id"],
            "action": "CREATE",
            "page_size": 10,
        },
        headers=headers,
    )
    assert audit_resp.status_code == 200
    audit_items = audit_resp.json()["items"]
    assert audit_items
    assert audit_items[0]["new_data"]["kind"] == "db"
    assert audit_items[0]["new_data"]["trigger"] == "manual"
    assert audit_items[0]["new_data"]["status"] == "queued"

    serialized_audit = str(audit_items[0]).lower()
    assert "access_key" not in serialized_audit
    assert "secret_key" not in serialized_audit
    assert "password" not in serialized_audit


@pytest.mark.asyncio(loop_scope="session")
async def test_snapshots_list_successful_backup_artifacts_without_secrets(client: TestClient):
    headers = _admin(client)
    db_key = f"postgres/pytest-db-{uuid4().hex}.sql.gz"
    object_key = f"files/pytest-files-{uuid4().hex}"
    await _insert_successful_backup_job("db", db_key)
    await _insert_successful_backup_job("object_storage", object_key, object_count=2)

    resp = client.get(f"{BASE}/snapshots", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    keys = {item["artifact_key"] for item in data}
    assert db_key in keys
    assert object_key in keys

    serialized = str(data).lower()
    assert "access_key" not in serialized
    assert "secret_key" not in serialized
    assert "password" not in serialized


def test_restore_request_requires_create_permission(client: TestClient):
    resp = client.post(
        f"{BASE}/restore-requests",
        json={
            "kind": "db",
            "mode": "verify_only",
            "db_artifact_key": "postgres/missing.sql.gz",
            "confirmation_text": "TOI XAC NHAN",
        },
        headers=_line_manager(client),
    )

    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_admin_creates_verify_restore_request_and_writes_safe_audit_log(client: TestClient):
    headers = _admin(client)
    db_key = f"postgres/pytest-restore-{uuid4().hex}.sql.gz"
    await _insert_successful_backup_job("db", db_key)

    resp = client.post(
        f"{BASE}/restore-requests",
        json={
            "kind": "db",
            "mode": "verify_only",
            "db_artifact_key": db_key,
            "confirmation_text": "TOI XAC NHAN",
        },
        headers=headers,
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["kind"] == "db"
    assert data["mode"] == "verify_only"
    assert data["status"] == "queued"
    assert data["db_artifact_key"] == db_key

    audit_resp = client.get(
        "/api/v1/audit-logs",
        params={
            "entity_type": "restore_request",
            "entity_id": data["id"],
            "action": "CREATE",
            "page_size": 10,
        },
        headers=headers,
    )
    assert audit_resp.status_code == 200
    audit_items = audit_resp.json()["items"]
    assert audit_items
    assert audit_items[0]["new_data"]["kind"] == "db"
    assert audit_items[0]["new_data"]["mode"] == "verify_only"

    serialized_audit = str(audit_items[0]).lower()
    assert "access_key" not in serialized_audit
    assert "secret_key" not in serialized_audit
    assert "password" not in serialized_audit


@pytest.mark.asyncio(loop_scope="session")
async def test_restore_request_rejects_missing_snapshot_and_unsafe_targets(client: TestClient):
    headers = _admin(client)
    db_name = settings.DATABASE_URL.rsplit("/", 1)[-1].split("?", 1)[0]
    existing_key = f"postgres/pytest-safe-{uuid4().hex}.sql.gz"
    await _insert_successful_backup_job("db", existing_key)

    missing_resp = client.post(
        f"{BASE}/restore-requests",
        json={
            "kind": "db",
            "mode": "verify_only",
            "db_artifact_key": "postgres/not-found.sql.gz",
            "confirmation_text": "TOI XAC NHAN",
        },
        headers=headers,
    )
    assert missing_resp.status_code == 404

    unsafe_db_resp = client.post(
        f"{BASE}/restore-requests",
        json={
            "kind": "db",
            "mode": "restore_to_new_target",
            "db_artifact_key": existing_key,
            "target_db_name": db_name,
            "confirmation_text": "TOI XAC NHAN",
        },
        headers=headers,
    )
    assert unsafe_db_resp.status_code == 400
    assert "production" in unsafe_db_resp.json()["detail"].lower()

    missing_confirmation_resp = client.post(
        f"{BASE}/restore-requests",
        json={
            "kind": "db",
            "mode": "verify_only",
            "db_artifact_key": existing_key,
        },
        headers=headers,
    )
    assert missing_confirmation_resp.status_code == 422


@pytest.mark.asyncio(loop_scope="session")
async def test_restore_runner_marks_request_verified_and_failed_without_exposing_secrets():
    artifact_key = f"postgres/pytest-runner-{uuid4().hex}.sql.gz"
    await _insert_successful_backup_job("db", artifact_key)

    async def create_request(session):
        row = await backup_service.create_restore_request(
            session,
            kind="db",
            mode="verify_only",
            db_artifact_key=artifact_key,
            object_snapshot_key=None,
            target_db_name=None,
            target_bucket=None,
            confirmation_text="TOI XAC NHAN",
            notes=None,
            user_id=None,
        )
        await session.commit()
        return row.id

    restore_id = await _with_isolated_session(create_request)

    async def runner(_session, request, _now):
        assert request.kind == "db"
        return RestoreRunResult(
            status="verified",
            notes="Đã kiểm tra artifact DB.",
        )

    async def run_request(session):
        return await backup_service.run_restore_request(
            session,
            restore_request_id=restore_id,
            runner=runner,
        )

    row = await _with_isolated_session(run_request)

    assert row.status == "verified"
    assert row.notes == "Đã kiểm tra artifact DB."

    async def create_failing_request(session):
        row = await backup_service.create_restore_request(
            session,
            kind="db",
            mode="verify_only",
            db_artifact_key=artifact_key,
            object_snapshot_key=None,
            target_db_name=None,
            target_bucket=None,
            confirmation_text="TOI XAC NHAN",
            notes=None,
            user_id=None,
        )
        await session.commit()
        return row.id

    failing_id = await _with_isolated_session(create_failing_request)

    async def failing_runner(_session, _request, _now):
        raise RuntimeError(f"Lỗi restore {settings.BACKUP_STORAGE_SECRET_KEY}")

    async def run_failing_request(session):
        return await backup_service.run_restore_request(
            session,
            restore_request_id=failing_id,
            runner=failing_runner,
        )

    failed = await _with_isolated_session(run_failing_request)

    assert failed.status == "failed"
    assert failed.notes
    assert settings.BACKUP_STORAGE_SECRET_KEY not in failed.notes
    assert "secret_key" not in failed.notes.lower()


@pytest.mark.asyncio(loop_scope="session")
async def test_backup_runner_marks_job_success_with_artifact_metadata():
    async def create_job(session):
        job = await backup_service.create_manual_backup_job(session, kind="db", user_id=None)
        await session.commit()
        return job.id

    job_id = await _with_isolated_session(create_job)

    async def runner(_session, config, _now):
        assert config.kind == "db"
        return BackupRunResult(
            artifact_key="postgres/test-db.jsonl.gz",
            artifact_bucket="hrms-backup",
            artifact_size_bytes=1234,
            object_count=None,
            log_excerpt="Đã tạo artifact kiểm thử.",
        )

    async def run_job(session):
        return await backup_service.run_backup_job(session, job_id=job_id, runner=runner)

    row = await _with_isolated_session(run_job)

    assert row.status == "success"
    assert row.artifact_key == "postgres/test-db.jsonl.gz"
    assert row.artifact_bucket == "hrms-backup"
    assert row.artifact_size_bytes == 1234
    assert row.started_at is not None
    assert row.finished_at is not None
    assert row.error_summary is None


@pytest.mark.asyncio(loop_scope="session")
async def test_backup_runner_sends_status_email_to_configured_recipients(monkeypatch):
    notify_email = "backup-admin@hrms.local"
    original_notify_emails: list[str] | None = None
    sent_payloads: list[dict] = []

    async def fake_send_status_email(_session, **payload):
        sent_payloads.append(payload)
        return {"status": "sent", "sent": payload["override_recipients"]}

    monkeypatch.setattr(
        backup_notification_service,
        "send_backup_status_email",
        fake_send_status_email,
    )

    async def create_job(session):
        nonlocal original_notify_emails
        config = await backup_service.get_backup_config_row(session, "object_storage")
        original_notify_emails = list(config.notify_emails or []) if config.notify_emails else None
        config.notify_emails = [notify_email]
        session.add(config)
        job = await backup_service.create_manual_backup_job(session, kind="object_storage", user_id=None)
        await session.commit()
        return job.id

    job_id = await _with_isolated_session(create_job)

    async def runner(_session, config, _now):
        assert config.kind == "object_storage"
        return BackupRunResult(
            artifact_key="files/test-minio.tar.gz",
            artifact_bucket="hrms-backup",
            artifact_size_bytes=5678,
            object_count=3,
            log_excerpt="Đã tạo bản sao MinIO kiểm thử.",
        )

    async def run_job(session):
        return await backup_service.run_backup_job(session, job_id=job_id, runner=runner)

    async def restore_config(session):
        config = await backup_service.get_backup_config_row(session, "object_storage")
        config.notify_emails = original_notify_emails
        session.add(config)
        await session.commit()

    try:
        row = await _with_isolated_session(run_job)
    finally:
        await _with_isolated_session(restore_config)

    assert row.status == "success"
    assert sent_payloads
    assert sent_payloads[0]["job_name"] == "Kho tệp ứng dụng trên MinIO"
    assert sent_payloads[0]["status"] == "success"
    assert sent_payloads[0]["started_at"].endswith("+07:00")
    assert sent_payloads[0]["finished_at"].endswith("+07:00")
    assert sent_payloads[0]["override_recipients"] == [notify_email]
    assert "files/test-minio.tar.gz" in sent_payloads[0]["details"]


def test_backup_notification_timestamp_uses_configured_timezone():
    value = backup_service._notification_timestamp(datetime(2026, 7, 13, 18, 0, 0))

    assert value == "2026-07-14T01:00:00+07:00"


@pytest.mark.asyncio(loop_scope="session")
async def test_backup_runner_marks_job_failed_without_exposing_secrets():
    async def create_job(session):
        job = await backup_service.create_manual_backup_job(session, kind="db", user_id=None)
        await session.commit()
        return job.id

    job_id = await _with_isolated_session(create_job)

    async def runner(_session, _config, _now):
        raise RuntimeError(f"Lỗi kiểm thử {settings.BACKUP_STORAGE_SECRET_KEY}")

    async def run_job(session):
        return await backup_service.run_backup_job(session, job_id=job_id, runner=runner)

    row = await _with_isolated_session(run_job)

    assert row.status == "failed"
    assert row.finished_at is not None
    assert row.error_summary
    assert settings.BACKUP_STORAGE_SECRET_KEY not in row.error_summary
    assert "secret_key" not in row.error_summary.lower()
