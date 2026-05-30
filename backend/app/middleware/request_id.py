"""Request ID + Access Log Middleware (H3 — Production Improvements).

Mỗi request nhận một ID ngắn gọn (8 hex chars).
Tất cả structlog calls trong request tự động đính kèm request_id vào JSON log.
Response thêm header X-Request-ID để client/FE có thể trace.
"""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)

# Các path không cần log chi tiết (liveness probe, health, static)
_SKIP_LOG_PATHS = frozenset({"/health", "/health/live", "/health/ready", "/health/live", "/metrics", "/favicon.ico"})


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Gán X-Request-ID cho mỗi request và log access log JSON."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Tái dùng ID nếu client gửi lên (tracing từ FE → BE), ngược lại tạo mới
        request_id = (request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8])

        # Bind vào structlog context — tất cả logger.xxx() trong cùng request
        # sẽ tự động có {"request_id": "..."} trong JSON output
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            t0 = time.monotonic()
            response = await call_next(request)
            duration_ms = int((time.monotonic() - t0) * 1000)

            # Gắn request_id vào response header để FE có thể đọc
            response.headers["X-Request-ID"] = request_id

            # Bỏ qua log cho các path probe/health
            if request.url.path not in _SKIP_LOG_PATHS:
                _log_access(request, response.status_code, duration_ms)

        return response


def _log_access(request: Request, status_code: int, duration_ms: int) -> None:
    """Log một dòng access log JSON chuẩn."""
    # Xác định user_id từ token mà không cần DB round-trip
    user_id = _extract_user_id(request)

    log_fn = logger.warning if status_code >= 400 else logger.info
    log_fn(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=status_code,
        duration_ms=duration_ms,
        user_id=user_id,
        client_ip=_client_ip(request),
    )


def _extract_user_id(request: Request) -> int | None:
    """Decode JWT payload (không verify signature) chỉ để lấy user_id cho log."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        from jose import jwt as _jwt
        payload = _jwt.get_unverified_claims(auth[7:])
        return payload.get("user_id")
    except Exception:  # noqa: BLE001 — JWT decode không bắt buộc thành công
        return None


def _client_ip(request: Request) -> str:
    """Lấy real IP, ưu tiên X-Forwarded-For (qua nginx/proxy)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
