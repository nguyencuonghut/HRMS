"""Các client S3 của ứng dụng phải ký yêu cầu bằng region được cấu hình (kế hoạch 15.7, Slice 1).

Garage từ chối chữ ký có region khác `s3_region` và SDK `minio` không tự sửa được, nên mọi chỗ tạo client
phải truyền `region`. Máy chủ S3 giả ở đây là một máy chủ HTTP thật chỉ ghi lại yêu cầu nhận được (đóng vai
hệ thống bên ngoài); kiểm tra dựa trên phạm vi chữ ký (`Credential=<khóa>/<ngày>/<region>/s3/aws4_request`),
đúng thứ Garage so sánh, nên không giả lập SDK và không phụ thuộc cấu trúc nội bộ của nó.
Không cần cơ sở dữ liệu.
"""
from __future__ import annotations

import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from app.core import storage
from app.core.config import settings

_LOCATION_XML = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<LocationConstraint xmlns="http://s3.amazonaws.com/doc/2006-03-01/"></LocationConstraint>'
)


def _signing_region(authorization: str) -> str | None:
    match = re.search(r"Credential=[^/]+/\d{8}/([^/]+)/s3/aws4_request", authorization)
    return match.group(1) if match else None


class _RecordingS3:
    def __init__(self) -> None:
        self.requests: list[dict[str, str | None]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _record(self) -> None:
                parts = urlsplit(self.path)
                outer.requests.append(
                    {
                        "method": self.command,
                        "path": parts.path,
                        "query": parts.query,
                        "region": _signing_region(self.headers.get("Authorization", "")),
                    }
                )

            def do_GET(self) -> None:
                self._record()
                self.send_response(200)
                self.send_header("Content-Type", "application/xml")
                self.send_header("Content-Length", str(len(_LOCATION_XML)))
                self.end_headers()
                self.wfile.write(_LOCATION_XML)

            def do_HEAD(self) -> None:
                self._record()
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args) -> None:
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.endpoint = f"127.0.0.1:{self._server.server_port}"
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture
def s3():
    server = _RecordingS3()
    yield server
    server.close()


def _methods_and_regions(s3: _RecordingS3) -> list[tuple[str | None, str | None]]:
    return [(r["method"], r["region"]) for r in s3.requests]


def test_app_storage_signs_with_the_configured_region_without_probing_for_it(monkeypatch, s3):
    monkeypatch.setattr(settings, "S3_ENDPOINT", s3.endpoint)
    monkeypatch.setattr(settings, "S3_ACCESS_KEY", "GKtestaccess")
    monkeypatch.setattr(settings, "S3_SECRET_KEY", "test-secret-value-1234567890")
    monkeypatch.setattr(settings, "S3_SECURE", False)
    monkeypatch.setattr(settings, "S3_REGION", "garage")

    storage._client().bucket_exists("any-bucket")

    assert _methods_and_regions(s3) == [("HEAD", "garage")]


def test_app_storage_without_a_region_still_lets_the_sdk_discover_it(monkeypatch, s3):
    """Không đặt S3_REGION thì giữ hành vi cũ (MinIO tự dò), để không làm hỏng các triển khai MinIO."""
    monkeypatch.setattr(settings, "S3_ENDPOINT", s3.endpoint)
    monkeypatch.setattr(settings, "S3_ACCESS_KEY", "GKtestaccess")
    monkeypatch.setattr(settings, "S3_SECRET_KEY", "test-secret-value-1234567890")
    monkeypatch.setattr(settings, "S3_SECURE", False)
    monkeypatch.setattr(settings, "S3_REGION", "")

    storage._client().bucket_exists("any-bucket")

    assert s3.requests[0]["method"] == "GET"
    assert s3.requests[0]["query"] == "location="


def test_backup_target_probe_signs_with_the_backup_storage_region(monkeypatch, s3):
    from app.services import backup_service

    monkeypatch.setattr(settings, "BACKUP_STORAGE_ACCESS_KEY", "GKbackupaccess")
    monkeypatch.setattr(settings, "BACKUP_STORAGE_SECRET_KEY", "backup-secret-value-1234567890")
    monkeypatch.setattr(settings, "BACKUP_STORAGE_REGION", "garage")

    ok, _ = backup_service._probe_target_bucket(s3.endpoint, "hrms-backup", False)

    assert ok
    assert _methods_and_regions(s3) == [("HEAD", "garage")]


def _backup_config(endpoint: str) -> SimpleNamespace:
    return SimpleNamespace(
        target_endpoint=endpoint,
        target_bucket="hrms-backup",
        target_secure=False,
        source_endpoint=endpoint,
        source_bucket="hrms-attachments-dev",
        source_secure=False,
    )


def test_backup_runner_writes_to_the_target_with_the_backup_storage_region(monkeypatch, s3):
    from app.services import backup_runner_service as runner

    monkeypatch.setattr(settings, "BACKUP_STORAGE_ACCESS_KEY", "GKbackupaccess")
    monkeypatch.setattr(settings, "BACKUP_STORAGE_SECRET_KEY", "backup-secret-value-1234567890")
    monkeypatch.setattr(settings, "BACKUP_STORAGE_REGION", "garage")

    runner._target_client(_backup_config(s3.endpoint))

    assert _methods_and_regions(s3) == [("HEAD", "garage")]


def test_backup_runner_reads_the_source_with_the_app_storage_region(monkeypatch, s3):
    from app.services import backup_runner_service as runner

    monkeypatch.setattr(settings, "S3_ACCESS_KEY", "GKtestaccess")
    monkeypatch.setattr(settings, "S3_SECRET_KEY", "test-secret-value-1234567890")
    monkeypatch.setattr(settings, "SOURCE_STORAGE_ACCESS_KEY", "")
    monkeypatch.setattr(settings, "SOURCE_STORAGE_SECRET_KEY", "")
    monkeypatch.setattr(settings, "S3_REGION", "garage")

    client, bucket = runner._source_client(_backup_config(s3.endpoint))
    client.bucket_exists(bucket)

    assert _methods_and_regions(s3) == [("HEAD", "garage")]


def test_restore_runner_reads_the_backup_with_the_backup_storage_region(monkeypatch, s3):
    from app.services import restore_runner_service as restore

    monkeypatch.setattr(settings, "BACKUP_STORAGE_ENDPOINT", s3.endpoint)
    monkeypatch.setattr(settings, "BACKUP_STORAGE_ACCESS_KEY", "GKbackupaccess")
    monkeypatch.setattr(settings, "BACKUP_STORAGE_SECRET_KEY", "backup-secret-value-1234567890")
    monkeypatch.setattr(settings, "BACKUP_STORAGE_SECURE", False)
    monkeypatch.setattr(settings, "BACKUP_STORAGE_REGION", "garage")

    restore._backup_target_client().bucket_exists("hrms-backup")

    assert _methods_and_regions(s3) == [("HEAD", "garage")]


def test_restore_runner_writes_the_files_back_with_the_app_storage_region(monkeypatch, s3):
    from app.services import restore_runner_service as restore

    monkeypatch.setattr(settings, "SOURCE_STORAGE_ENDPOINT", "")
    monkeypatch.setattr(settings, "SOURCE_STORAGE_ACCESS_KEY", "")
    monkeypatch.setattr(settings, "SOURCE_STORAGE_SECRET_KEY", "")
    monkeypatch.setattr(settings, "SOURCE_STORAGE_SECURE", "false")
    monkeypatch.setattr(settings, "S3_ENDPOINT", s3.endpoint)
    monkeypatch.setattr(settings, "S3_ACCESS_KEY", "GKtestaccess")
    monkeypatch.setattr(settings, "S3_SECRET_KEY", "test-secret-value-1234567890")
    monkeypatch.setattr(settings, "S3_REGION", "garage")

    restore._source_client().bucket_exists("hrms-attachments-dev")

    assert _methods_and_regions(s3) == [("HEAD", "garage")]
