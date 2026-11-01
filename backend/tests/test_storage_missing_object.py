"""Tải tệp khi object không còn trong kho (LD-003 trong docs/known_issues.md).

Trước đây `get_object_stream` là generator nên việc mở object chạy sau khi `StreamingResponse` đã gửi dòng trạng thái
200: người dùng nhận tệp rỗng thay vì 404. Đồng thời `NoSuchKey` bị mạch ngắt của kho tính là sự cố, nên 3 lần tải
tệp thiếu liên tiếp làm mọi thao tác kho trả 503 trong 30 giây.

Máy chủ S3 giả là một máy chủ HTTP thật (đóng vai hệ thống bên ngoài, giống test_s3_client_region.py); kiểm tra qua
hành vi quan sát được của `app.core.storage`. Không cần cơ sở dữ liệu và không cần Garage.
"""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi import HTTPException
from minio.error import S3Error

from app.core import storage
from app.core.circuit_breaker import storage_circuit
from app.core.config import settings

_BUCKET = "test-bucket"
_PRESENT_KEY = "present/file.pdf"
_PRESENT_BODY = b"%PDF-still-here"


def _error_xml(code: str, message: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Error><Code>{code}</Code><Message>{message}</Message>"
        "<RequestId>test</RequestId></Error>"
    ).encode()


class _FakeS3:
    """Có đúng một object (`_PRESENT_KEY`); khóa bắt đầu bằng `denied/` bị từ chối; còn lại là NoSuchKey."""

    def __init__(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                key = self.path.split("?")[0].lstrip("/").split("/", 1)[-1]
                if key == _PRESENT_KEY:
                    self._send(200, _PRESENT_BODY, "application/pdf")
                elif key.startswith("denied/"):
                    self._send(403, _error_xml("AccessDenied", "Access denied"), "application/xml")
                else:
                    self._send(404, _error_xml("NoSuchKey", "Key not found"), "application/xml")

            def _send(self, code: int, body: bytes, content_type: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args) -> None:
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.endpoint = f"127.0.0.1:{self._server.server_port}"
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture
def s3(monkeypatch):
    server = _FakeS3()
    monkeypatch.setattr(settings, "S3_ENDPOINT", server.endpoint)
    monkeypatch.setattr(settings, "S3_ACCESS_KEY", "GKtestaccess")
    monkeypatch.setattr(settings, "S3_SECRET_KEY", "test-secret-value-1234567890")
    monkeypatch.setattr(settings, "S3_SECURE", False)
    monkeypatch.setattr(settings, "S3_REGION", "garage")
    monkeypatch.setattr(settings, "S3_BUCKET", _BUCKET)
    yield server
    server.close()


@pytest.fixture(autouse=True)
def fresh_storage_circuit():
    """Mạch ngắt của kho là singleton dùng chung cả tiến trình; mỗi test bắt đầu và kết thúc ở trạng thái đóng."""

    def reset() -> None:
        storage_circuit._state = type(storage_circuit._state)("closed")
        storage_circuit._failure_count = 0

    reset()
    yield
    reset()


def test_missing_object_is_a_404_raised_before_any_streaming(s3):
    """Lỗi phải nổ ngay lúc gọi hàm, không đợi tới lúc StreamingResponse bắt đầu đọc thân."""
    with pytest.raises(HTTPException) as exc:
        storage.get_object_stream("employees/1/gone.pdf")

    assert exc.value.status_code == 404


def test_existing_object_still_streams_its_content(s3):
    assert b"".join(storage.get_object_stream(_PRESENT_KEY)) == _PRESENT_BODY


def test_get_object_bytes_of_a_missing_object_is_a_404(s3):
    with pytest.raises(HTTPException) as exc:
        storage.get_object_bytes("templates/gone.docx")

    assert exc.value.status_code == 404


def test_missing_objects_do_not_trip_the_storage_circuit(s3):
    for _ in range(storage_circuit.failure_threshold + 1):
        with pytest.raises(HTTPException) as exc:
            storage.get_object_stream("employees/1/gone.pdf")
        assert exc.value.status_code == 404

    assert b"".join(storage.get_object_stream(_PRESENT_KEY)) == _PRESENT_BODY


def test_a_real_storage_failure_still_trips_the_circuit(s3):
    """Ngoại lệ miễn trừ chỉ dành cho NoSuchKey: lỗi kho thật (ở đây AccessDenied) vẫn phải mở mạch ngắt."""
    for _ in range(storage_circuit.failure_threshold):
        with pytest.raises(S3Error):
            storage.get_object_stream("denied/x.pdf")

    with pytest.raises(HTTPException) as exc:
        storage.get_object_stream(_PRESENT_KEY)

    assert exc.value.status_code == 503
