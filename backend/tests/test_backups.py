"""Integration tests cho Backup & Restore Admin Console slices 1-2."""
from __future__ import annotations

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

