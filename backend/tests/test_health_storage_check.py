"""`/health/ready` báo trạng thái kho tệp ứng dụng ở khóa `storage` (kế hoạch 15.7, Slice 10).

Khóa của kho tệp là `storage`, không nêu tên công nghệ; chỉ `main.py` ghi các khóa này và không nơi nào trong repo đọc khóa cũ.
"""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core import storage


def test_ready_reports_the_app_storage_under_the_storage_key(client: TestClient, monkeypatch):
    monkeypatch.setattr(storage, "_client", lambda: SimpleNamespace(bucket_exists=lambda bucket: True))

    response = client.get("/health/ready")

    checks = response.json()["checks"]
    assert checks["storage"] == "ok"
    assert set(checks) == {"database", "redis", "storage"}
    assert response.status_code == 200


def test_ready_fails_with_the_storage_error_when_the_bucket_cannot_be_checked(client: TestClient, monkeypatch):
    def broken_client():
        raise RuntimeError("không nối được kho")

    monkeypatch.setattr(storage, "_client", broken_client)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["storage"] == "error: không nối được kho"
