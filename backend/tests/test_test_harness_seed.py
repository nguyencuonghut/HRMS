"""Regression tests cho test harness auth identities."""

from fastapi.testclient import TestClient


def test_client_fixture_has_seeded_admin_identity(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@hrms.local", "password": "Hrms@2026"},
        headers={"X-Forwarded-For": "198.18.250.10"},
    )
    assert resp.status_code == 200, resp.text

