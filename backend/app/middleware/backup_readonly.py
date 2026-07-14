"""Chế độ chỉ đọc tạm thời khi đang chạy bộ sao lưu đầy đủ."""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

_STATE_CHANGING = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_EXEMPT_PREFIXES = (
    "/api/v1/backups",
    "/api/v1/auth",
    "/api/docs",
    "/api/openapi.json",
    "/health",
)


def _is_exempt_path(path: str) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in _EXEMPT_PREFIXES)


class BackupReadOnlyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in _STATE_CHANGING or _is_exempt_path(request.url.path):
            return await call_next(request)

        try:
            async with AsyncSessionLocal() as session:
                active_backup_set_id = (
                    await session.execute(
                        text("""
                            SELECT id
                            FROM backup_sets
                            WHERE status = 'running'
                            ORDER BY started_at DESC NULLS LAST, created_at DESC
                            LIMIT 1
                        """)
                    )
                ).scalar_one_or_none()
        except SQLAlchemyError as exc:
            logger.warning("backup_readonly_check_failed", extra={"error": str(exc)})
            return await call_next(request)

        if active_backup_set_id is None:
            return await call_next(request)

        return JSONResponse(
            status_code=423,
            content={
                "detail": (
                    "Hệ thống đang chạy sao lưu đầy đủ nên tạm thời khóa các thao tác ghi. "
                    "Vui lòng thử lại sau khi sao lưu hoàn tất."
                ),
                "backup_set_id": active_backup_set_id,
            },
        )
