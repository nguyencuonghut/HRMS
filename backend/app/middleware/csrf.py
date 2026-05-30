"""CSRF Protection Middleware (M1 — Production Improvements).

Hệ thống dùng JWT Bearer token trong Authorization header → CSRF truyền thống
KHÔNG áp dụng (browser không tự gửi Authorization header cross-origin).

Tuy nhiên, để defense-in-depth, middleware này validate Origin/Referer header
cho state-changing requests (POST/PUT/PATCH/DELETE) từ browser.

Cho phép:
  - Requests không có Origin header (API clients, mobile apps, curl, Postman)
  - Requests từ trusted origins (CORS_ORIGINS config)

Từ chối:
  - Requests có Origin header NHƯNG origin không nằm trong whitelist
    → trả 403 để ngăn cross-origin state mutation từ browser
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

# HTTP methods cần kiểm tra
_STATE_CHANGING = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Paths được miễn (auth endpoints cần accept từ bất kỳ đâu)
_EXEMPT_PATHS = frozenset({
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/health",
    "/health/live",
    "/health/ready",
})


def _extract_origin(url: str) -> str:
    """Trích origin (scheme + host + port) từ URL string."""
    try:
        p = urlparse(url)
        origin = f"{p.scheme}://{p.netloc}"
        return origin.rstrip("/")
    except Exception:
        return ""


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Origin validation cho state-changing requests từ browser.

    Không ảnh hưởng đến:
    - GET, HEAD, OPTIONS requests
    - Requests không có Origin header (API clients, Postman, curl)
    - Requests từ trusted origins (CORS_ORIGINS)
    """

    async def dispatch(self, request: Request, call_next):
        if request.method not in _STATE_CHANGING:
            return await call_next(request)

        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # Lấy Origin header (browser gửi khi cross-origin request)
        origin = request.headers.get("Origin", "").strip()

        # Không có Origin → API client / mobile / server-to-server → cho qua
        if not origin:
            return await call_next(request)

        # Có Origin → kiểm tra whitelist
        trusted = [o.rstrip("/") for o in settings.CORS_ORIGINS]

        # Cũng kiểm tra Referer nếu Origin không có
        if not origin:
            referer = request.headers.get("Referer", "")
            origin = _extract_origin(referer)

        if origin not in trusted:
            logger.warning(
                "csrf_origin_rejected",
                extra={
                    "origin": origin,
                    "method": request.method,
                    "path": request.url.path,
                    "trusted": trusted,
                },
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        f"Origin '{origin}' không được phép thực hiện "
                        f"thao tác này. Nếu đây là lỗi, kiểm tra cấu hình CORS_ORIGINS."
                    )
                },
            )

        return await call_next(request)
