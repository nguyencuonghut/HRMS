from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

BASE = "/api/v1/employees"


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@hrms.local", "password": "Hrms@2026"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_attachment_preview_url_returns_inline_stream(client: TestClient):
    headers = _admin(client)
    upload = client.post(
        f"{BASE}/1/attachments",
        headers=headers,
        data={"document_type": "avatar"},
        files={"file": ("preview-inline.png", b"png-bytes", "image/png")},
    )
    assert upload.status_code == 201
    att_id = upload.json()["id"]

    preview_url_res = client.get(f"{BASE}/1/attachments/{att_id}/preview-url", headers=headers)
    assert preview_url_res.status_code == 200
    payload = preview_url_res.json()
    assert payload["expires_in_seconds"] == 300
    assert f"/api/v1/employees/1/attachments/{att_id}/preview?token=" in payload["url"]

    preview_res = client.get(payload["url"])
    assert preview_res.status_code == 200
    assert preview_res.headers["content-type"].startswith("image/png")
    assert "inline;" in preview_res.headers["content-disposition"]


def test_attachment_preview_rejects_invalid_token(client: TestClient):
    headers = _admin(client)
    upload = client.post(
        f"{BASE}/1/attachments",
        headers=headers,
        data={"document_type": "avatar"},
        files={"file": ("preview-inline.png", b"png-bytes", "image/png")},
    )
    assert upload.status_code == 201
    att_id = upload.json()["id"]

    preview_url_res = client.get(f"{BASE}/1/attachments/{att_id}/preview-url", headers=headers)
    tokenized_url = preview_url_res.json()["url"]
    parsed = urlparse(tokenized_url)
    token = parse_qs(parsed.query)["token"][0]
    invalid_url = tokenized_url.replace(token, f"{token}tampered")

    preview_res = client.get(invalid_url)
    assert preview_res.status_code == 401


def test_checklist_preview_url_returns_inline_stream(client: TestClient):
    headers = _admin(client)

    checklist_res = client.get(f"{BASE}/1/document-checklist", headers=headers)
    assert checklist_res.status_code == 200
    items = checklist_res.json()
    if not items:
        init_res = client.post(f"{BASE}/1/document-checklist/init", headers=headers)
        assert init_res.status_code == 200
        items = init_res.json()
    assert items
    item_id = items[0]["id"]

    upload = client.post(
        f"{BASE}/1/document-checklist/{item_id}/upload",
        headers=headers,
        files={"file": ("preview-checklist-inline.png", b"png-bytes", "image/png")},
    )
    assert upload.status_code == 200

    preview_url_res = client.get(f"{BASE}/1/document-checklist/{item_id}/preview-url", headers=headers)
    assert preview_url_res.status_code == 200
    payload = preview_url_res.json()
    assert payload["expires_in_seconds"] == 300
    assert f"/api/v1/employees/1/document-checklist/{item_id}/preview?token=" in payload["url"]

    preview_res = client.get(payload["url"])
    assert preview_res.status_code == 200
    assert preview_res.headers["content-type"].startswith("image/png")
    assert "inline;" in preview_res.headers["content-disposition"]
