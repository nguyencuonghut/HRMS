"""Integration tests cho Backup & Restore Admin Console."""
from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

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
