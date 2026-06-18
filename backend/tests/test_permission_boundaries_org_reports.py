"""Regression tests cho ranh giới view/edit ở các endpoint FE đang dùng để ẩn/hiện theo quyền."""

from fastapi.testclient import TestClient

_PASSWORD = "Hrms@2026"


def _bearer(client: TestClient, email: str) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_line_manager_can_view_org_but_cannot_edit_job_titles(client: TestClient):
    headers = _bearer(client, "linemanager@hrms.local")

    list_resp = client.get("/api/v1/job-titles", headers=headers)
    assert list_resp.status_code == 200, list_resp.text

    create_resp = client.post(
        "/api/v1/job-titles",
        json={"code": "PERM_LM_JT", "name": "Should Fail", "level": 1},
        headers=headers,
    )
    assert create_resp.status_code == 403, create_resp.text


def test_line_manager_can_view_org_history(client: TestClient):
    headers = _bearer(client, "linemanager@hrms.local")
    resp = client.get("/api/v1/org-history", headers=headers)
    assert resp.status_code == 200, resp.text


def test_line_manager_can_view_onboarding_list_but_cannot_create_task_template(client: TestClient):
    headers = _bearer(client, "linemanager@hrms.local")

    list_resp = client.get("/api/v1/onboarding", headers=headers)
    assert list_resp.status_code == 200, list_resp.text

    create_task_resp = client.post(
        "/api/v1/onboarding/tasks",
        json={
            "code": "PERM_OB_TASK",
            "name": "Should Fail",
            "group": "it",
            "due_offset_days": 1,
        },
        headers=headers,
    )
    assert create_task_resp.status_code == 403, create_task_resp.text


def test_line_manager_can_view_employee_code_sequences(client: TestClient):
    headers = _bearer(client, "linemanager@hrms.local")
    resp = client.get("/api/v1/employee-code-sequences", headers=headers)
    assert resp.status_code == 200, resp.text
    assert [item["code"] for item in resp.json()] == ["SYS1", "SYS2", "SYS3"]


def test_finance_can_view_export_history(client: TestClient):
    headers = _bearer(client, "finance@hrms.local")
    resp = client.get("/api/v1/reports/export/history", headers=headers)
    assert resp.status_code == 200, resp.text


def test_finance_can_view_job_positions_for_insurance_config(client: TestClient):
    headers = _bearer(client, "finance@hrms.local")
    resp = client.get("/api/v1/job-positions", headers=headers)
    assert resp.status_code == 200, resp.text


