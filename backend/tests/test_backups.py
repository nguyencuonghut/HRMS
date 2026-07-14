"""Integration tests cho Backup & Restore Admin Console."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.backup import BackupConfig, BackupJob, BackupSet, RestoreRequest
from app.services import backup_notification_service, backup_service
from app.services.backup_runner_service import BackupRunResult
from app.services import restore_runner_service
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


async def _clear_active_backup_sets() -> None:
    async def work(session):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.execute(
            update(BackupSet)
            .where(BackupSet.status.in_(["queued", "running"]))
            .values(
                status="failed",
                error_summary="Dọn trạng thái kiểm thử.",
                finished_at=now,
                updated_at=now,
            )
        )
        await session.execute(
            update(BackupJob)
            .where(BackupJob.trigger.in_(["manual_full", "scheduled_full"]))
            .where(BackupJob.status.in_(["queued", "running"]))
            .values(
                status="failed",
                error_summary="Dọn trạng thái kiểm thử.",
                finished_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    await _with_isolated_session(work)


async def _clear_backup_sets_for_slot(slot_start: datetime, slot_end: datetime) -> None:
    async def work(session):
        backup_set_ids = (
            await session.execute(
                select(BackupSet.id)
                .where(BackupSet.trigger == "scheduled_full")
                .where(BackupSet.created_at >= slot_start)
                .where(BackupSet.created_at < slot_end)
            )
        ).scalars().all()
        if not backup_set_ids:
            return

        await session.execute(
            update(BackupSet)
            .where(BackupSet.id.in_(backup_set_ids))
            .values(db_job_id=None, object_job_id=None)
        )
        await session.execute(delete(BackupJob).where(BackupJob.backup_set_id.in_(backup_set_ids)))
        await session.execute(delete(BackupSet).where(BackupSet.id.in_(backup_set_ids)))
        await session.commit()

    await _with_isolated_session(work)


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


async def _insert_successful_backup_set() -> tuple[int, str, str]:
    db_key = f"postgres/pytest-full-db-{uuid4().hex}.sql.gz"
    object_key = f"files/pytest-full-files-{uuid4().hex}"

    async def work(session):
        backup_set = BackupSet(
            trigger="manual",
            status="success",
            error_summary=None,
        )
        session.add(backup_set)
        await session.flush()

        db_job = BackupJob(
            kind="db",
            trigger="manual_full",
            status="success",
            backup_set_id=backup_set.id,
            artifact_key=db_key,
            artifact_bucket="hrms-backup",
            artifact_size_bytes=321,
            log_excerpt="Artifact DB kiểm thử.",
        )
        object_job = BackupJob(
            kind="object_storage",
            trigger="manual_full",
            status="success",
            backup_set_id=backup_set.id,
            artifact_key=object_key,
            artifact_bucket="hrms-backup",
            artifact_size_bytes=654,
            object_count=2,
            log_excerpt="Artifact kho tệp kiểm thử.",
        )
        session.add(db_job)
        session.add(object_job)
        await session.flush()

        backup_set.db_job_id = db_job.id
        backup_set.object_job_id = object_job.id
        session.add(backup_set)
        await session.commit()
        await session.refresh(backup_set)
        return backup_set.id, db_key, object_key

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
    assert isinstance(data["latest_backup_sets"], list)
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
    assert {"backup_config", "backup_job", "backup_set", "restore_request"}.issubset(entity_codes)


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


def test_admin_creates_full_backup_set_and_child_jobs(client: TestClient):
    asyncio.run(_clear_active_backup_sets())
    headers = _admin(client)

    resp = client.post(f"{BASE}/sets", headers=headers)

    assert resp.status_code == 201
    data = resp.json()
    assert data["trigger"] == "manual"
    assert data["status"] == "queued"
    assert data["db_job_id"]
    assert data["object_job_id"]
    assert data["db_artifact_key"] is None
    assert data["object_snapshot_key"] is None

    jobs_resp = client.get(f"{BASE}/jobs", headers=headers)
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    child_jobs = [item for item in jobs if item["backup_set_id"] == data["id"]]
    assert {item["kind"] for item in child_jobs} == {"db", "object_storage"}
    assert {item["trigger"] for item in child_jobs} == {"manual_full"}

    audit_resp = client.get(
        "/api/v1/audit-logs",
        params={
            "entity_type": "backup_set",
            "entity_id": data["id"],
            "action": "CREATE",
            "page_size": 10,
        },
        headers=headers,
    )
    assert audit_resp.status_code == 200
    audit_items = audit_resp.json()["items"]
    assert audit_items
    assert audit_items[0]["new_data"]["status"] == "queued"

    serialized_audit = str(audit_items[0]).lower()
    assert "access_key" not in serialized_audit
    assert "secret_key" not in serialized_audit
    assert "password" not in serialized_audit


def test_admin_cannot_create_full_backup_set_while_another_set_is_active(client: TestClient):
    asyncio.run(_clear_active_backup_sets())
    headers = _admin(client)

    first_resp = client.post(f"{BASE}/sets", headers=headers)
    assert first_resp.status_code == 201

    second_resp = client.post(f"{BASE}/sets", headers=headers)

    assert second_resp.status_code == 409
    assert "đang chờ" in second_resp.json()["detail"]


def test_create_full_backup_set_requires_create_permission(client: TestClient):
    resp = client.post(f"{BASE}/sets", headers=_line_manager(client))

    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_scheduled_backup_set_uses_db_cron_and_is_idempotent_per_minute(client: TestClient):
    await _clear_active_backup_sets()
    local_now = datetime(2031, 5, 17, 2, 0, 15, tzinfo=ZoneInfo(settings.APP_TIMEZONE))
    slot_start = local_now.replace(second=0, microsecond=0).astimezone(timezone.utc).replace(tzinfo=None)
    slot_end = local_now.replace(minute=1, second=0, microsecond=0).astimezone(timezone.utc).replace(tzinfo=None)
    await _clear_backup_sets_for_slot(slot_start, slot_end)

    async def work(session):
        await backup_service.ensure_backup_configs(session)
        await session.execute(
            update(BackupConfig)
            .where(BackupConfig.kind == "db")
            .values(enabled=True, cron_expression="0 2 * * *")
        )
        await session.execute(
            update(BackupConfig)
            .where(BackupConfig.kind == "object_storage")
            .values(enabled=True, cron_expression="30 3 * * *")
        )
        await session.commit()

        backup_set = await backup_service.create_scheduled_backup_set_if_due(session, now=local_now)
        assert backup_set is not None
        assert backup_set.trigger == "scheduled_full"
        assert backup_set.status == "queued"
        assert backup_set.db_job_id
        assert backup_set.object_job_id
        await session.commit()

        duplicate = await backup_service.create_scheduled_backup_set_if_due(session, now=local_now)
        assert duplicate is None

        child_jobs = (
            await session.execute(
                select(BackupJob)
                .where(BackupJob.backup_set_id == backup_set.id)
                .order_by(BackupJob.kind)
            )
        ).scalars().all()
        assert {job.kind for job in child_jobs} == {"db", "object_storage"}
        assert {job.trigger for job in child_jobs} == {"scheduled_full"}

    await _with_isolated_session(work)


@pytest.mark.asyncio(loop_scope="session")
async def test_snapshots_list_successful_backup_artifacts_without_secrets(client: TestClient):
    headers = _admin(client)
    db_key = f"postgres/pytest-db-{uuid4().hex}.sql.gz"
    object_key = f"files/pytest-files-{uuid4().hex}"
    await _insert_successful_backup_job("db", db_key)
    await _insert_successful_backup_job("object_storage", object_key, object_count=2)

    resp = client.get(f"{BASE}/snapshots", params={"kind": "db", "limit": 100}, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    keys = {item["artifact_key"] for item in data}
    assert db_key in keys

    object_resp = client.get(f"{BASE}/snapshots", params={"kind": "object_storage", "limit": 100}, headers=headers)
    assert object_resp.status_code == 200
    data.extend(object_resp.json())
    keys = {item["artifact_key"] for item in data}
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
    assert data["status"] == "draft"
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
async def test_admin_approves_restore_request_before_it_is_queued(client: TestClient, monkeypatch):
    headers = _admin(client)
    artifact_key = f"postgres/pytest-approve-{uuid4().hex}.sql.gz"
    await _insert_successful_backup_job("db", artifact_key)
    enqueued_ids: list[int] = []

    create_resp = client.post(
        f"{BASE}/restore-requests",
        json={
            "kind": "db",
            "mode": "verify_only",
            "db_artifact_key": artifact_key,
            "confirmation_text": "TOI XAC NHAN",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    restore_id = create_resp.json()["id"]

    monkeypatch.setattr(
        backup_service,
        "enqueue_restore_request",
        lambda request_id: enqueued_ids.append(request_id) or True,
    )
    approve_resp = client.post(f"{BASE}/restore-requests/{restore_id}/approve", headers=headers)

    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["status"] == "queued"
    assert data["approved_by_id"] is not None
    assert enqueued_ids == [restore_id]


@pytest.mark.asyncio(loop_scope="session")
async def test_restore_request_is_marked_failed_when_enqueue_fails(client: TestClient, monkeypatch):
    headers = _admin(client)
    artifact_key = f"postgres/pytest-enqueue-fail-{uuid4().hex}.sql.gz"
    await _insert_successful_backup_job("db", artifact_key)

    create_resp = client.post(
        f"{BASE}/restore-requests",
        json={
            "kind": "db",
            "mode": "verify_only",
            "db_artifact_key": artifact_key,
            "confirmation_text": "TOI XAC NHAN",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    restore_id = create_resp.json()["id"]

    monkeypatch.setattr(backup_service, "enqueue_restore_request", lambda _request_id: False)

    approve_resp = client.post(f"{BASE}/restore-requests/{restore_id}/approve", headers=headers)

    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["status"] == "failed"
    assert data["notes"] == "Không đưa được yêu cầu khôi phục vào hàng đợi xử lý."


@pytest.mark.asyncio(loop_scope="session")
async def test_admin_can_cancel_draft_restore_request(client: TestClient):
    headers = _admin(client)
    artifact_key = f"postgres/pytest-cancel-{uuid4().hex}.sql.gz"
    await _insert_successful_backup_job("db", artifact_key)

    create_resp = client.post(
        f"{BASE}/restore-requests",
        json={
            "kind": "db",
            "mode": "verify_only",
            "db_artifact_key": artifact_key,
            "confirmation_text": "TOI XAC NHAN",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201

    cancel_resp = client.post(
        f"{BASE}/restore-requests/{create_resp.json()['id']}/cancel",
        headers=headers,
    )

    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio(loop_scope="session")
async def test_admin_retries_failed_restore_request(client: TestClient, monkeypatch):
    headers = _admin(client)
    artifact_key = f"postgres/pytest-retry-{uuid4().hex}.sql.gz"
    await _insert_successful_backup_job("db", artifact_key)

    async def create_failed_request(session):
        row = await backup_service.create_restore_request(
            session,
            kind="db",
            mode="verify_only",
            backup_set_id=None,
            db_artifact_key=artifact_key,
            object_snapshot_key=None,
            target_db_name=None,
            target_bucket=None,
            confirmation_text="TOI XAC NHAN",
            notes=None,
            user_id=None,
        )
        row.status = "failed"
        row.notes = "Lỗi kiểm thử."
        await session.commit()
        return row.id

    restore_id = await _with_isolated_session(create_failed_request)
    enqueued_ids: list[int] = []
    monkeypatch.setattr(
        backup_service,
        "enqueue_restore_request",
        lambda request_id: enqueued_ids.append(request_id) or True,
    )

    retry_resp = client.post(f"{BASE}/restore-requests/{restore_id}/retry", headers=headers)

    assert retry_resp.status_code == 200
    data = retry_resp.json()
    assert data["status"] == "queued"
    assert data["approved_by_id"] is not None
    assert enqueued_ids == [restore_id]


@pytest.mark.asyncio(loop_scope="session")
async def test_admin_creates_full_restore_request_from_backup_set(client: TestClient):
    headers = _admin(client)
    backup_set_id, db_key, object_key = await _insert_successful_backup_set()

    resp = client.post(
        f"{BASE}/restore-requests",
        json={
            "kind": "full",
            "mode": "verify_only",
            "backup_set_id": backup_set_id,
            "confirmation_text": "TOI XAC NHAN",
        },
        headers=headers,
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["kind"] == "full"
    assert data["backup_set_id"] == backup_set_id
    assert data["db_artifact_key"] == db_key
    assert data["object_snapshot_key"] == object_key


def test_full_restore_request_requires_backup_set(client: TestClient):
    resp = client.post(
        f"{BASE}/restore-requests",
        json={
            "kind": "full",
            "mode": "verify_only",
            "db_artifact_key": "postgres/db.sql.gz",
            "object_snapshot_key": "files/files-20260714",
            "confirmation_text": "TOI XAC NHAN",
        },
        headers=_admin(client),
    )

    assert resp.status_code == 422


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
            backup_set_id=None,
            db_artifact_key=artifact_key,
            object_snapshot_key=None,
            target_db_name=None,
            target_bucket=None,
            confirmation_text="TOI XAC NHAN",
            notes=None,
            user_id=None,
        )
        row.status = "queued"
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
            backup_set_id=None,
            db_artifact_key=artifact_key,
            object_snapshot_key=None,
            target_db_name=None,
            target_bucket=None,
            confirmation_text="TOI XAC NHAN",
            notes=None,
            user_id=None,
        )
        row.status = "queued"
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
async def test_restore_verify_db_restores_into_temp_database_and_cleans_up(monkeypatch):
    artifact_key = f"postgres/pytest-verify-db-{uuid4().hex}.sql.gz"
    await _insert_successful_backup_job("db", artifact_key)
    commands: list[list[str]] = []
    restored_targets: list[str] = []

    async def fake_run_pg_client(command, env):
        commands.append(command)
        return 0, ""

    async def fake_restore_sql(bucket, object_name, target_db_name, env):
        assert bucket == "hrms-backup"
        assert object_name == artifact_key
        restored_targets.append(target_db_name)
        return 123

    monkeypatch.setattr(restore_runner_service, "_run_pg_client", fake_run_pg_client)
    monkeypatch.setattr(restore_runner_service, "_restore_sql_object_to_database", fake_restore_sql)

    async def run_verify(session):
        request = RestoreRequest(
            kind="db",
            mode="verify_only",
            status="queued",
            db_artifact_key=artifact_key,
            confirmation_text="TOI XAC NHAN",
        )
        session.add(request)
        await session.flush()
        return await restore_runner_service.run_restore_request(session, request, datetime.now(timezone.utc))

    result = await _with_isolated_session(run_verify)

    assert result.status == "verified"
    assert restored_targets
    assert restored_targets[0].startswith("hrms_restore_verify_")
    assert commands[0][0] == "createdb"
    assert commands[-1][0] == "dropdb"
    assert commands[-1][-1] == restored_targets[0]


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
async def test_backup_set_runner_runs_db_then_object_storage_in_one_set():
    await _clear_active_backup_sets()

    async def create_set(session):
        backup_set = await backup_service.create_manual_backup_set(session, user_id=None)
        await session.commit()
        return backup_set.id

    backup_set_id = await _with_isolated_session(create_set)
    seen_kinds: list[str] = []

    async def runner(_session, config, _now):
        seen_kinds.append(config.kind)
        if config.kind == "db":
            return BackupRunResult(
                artifact_key="postgres/full-set-db.sql.gz",
                artifact_bucket="hrms-backup",
                artifact_size_bytes=111,
                object_count=None,
                log_excerpt="DB OK.",
            )
        return BackupRunResult(
            artifact_key="files/full-set-files",
            artifact_bucket="hrms-backup",
            artifact_size_bytes=222,
            object_count=2,
            log_excerpt="Files OK.",
        )

    async def run_set(session):
        return await backup_service.run_backup_set(
            session,
            backup_set_id=backup_set_id,
            runner=runner,
        )

    backup_set = await _with_isolated_session(run_set)

    assert seen_kinds == ["db", "object_storage"]
    assert backup_set.status == "success"
    assert backup_set.db_job_id is not None
    assert backup_set.object_job_id is not None
    assert backup_set.started_at is not None
    assert backup_set.finished_at is not None


@pytest.mark.asyncio(loop_scope="session")
async def test_running_backup_set_blocks_state_changing_business_requests(client: TestClient):
    async def create_running_set(session):
        backup_set = BackupSet(trigger="manual", status="running")
        session.add(backup_set)
        await session.commit()
        await session.refresh(backup_set)
        return backup_set.id

    async def finish_set(session, backup_set_id: int):
        row = await session.get(BackupSet, backup_set_id)
        if row:
            row.status = "failed"
            session.add(row)
            await session.commit()

    backup_set_id = await _with_isolated_session(create_running_set)
    try:
        resp = client.post("/api/v1/departments", json={"name": "Bị chặn khi backup"}, headers=_admin(client))
    finally:
        await _with_isolated_session(lambda session: finish_set(session, backup_set_id))

    assert resp.status_code == 423
    assert "sao lưu đầy đủ" in resp.json()["detail"].lower()


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
