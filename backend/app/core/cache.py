"""Redis application cache helpers (15.2 Hiệu năng).

TTL mặc định 1 giờ cho danh mục (departments, job_titles, leave_types).
Invalidation được gọi khi có write operation trên entity tương ứng.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: aioredis.Redis | None = None


def get_cache_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
    return _client


async def cache_get(key: str) -> Any | None:
    """Lấy giá trị từ cache. Trả None nếu miss hoặc lỗi Redis."""
    try:
        raw = await get_cache_client().get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("cache_get failed key=%s: %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    """Lưu giá trị vào cache. Lỗi Redis không raise — degraded gracefully."""
    try:
        await get_cache_client().setex(
            key,
            ttl,
            json.dumps(value, ensure_ascii=False, default=str),
        )
    except Exception as exc:
        logger.warning("cache_set failed key=%s: %s", key, exc)


async def cache_delete(key: str) -> None:
    try:
        await get_cache_client().delete(key)
    except Exception as exc:
        logger.warning("cache_delete failed key=%s: %s", key, exc)


async def cache_delete_pattern(pattern: str) -> None:
    """Xóa tất cả keys khớp pattern (dùng SCAN để không block Redis)."""
    try:
        client = get_cache_client()
        async for key in client.scan_iter(match=pattern, count=100):
            await client.delete(key)
    except Exception as exc:
        logger.warning("cache_delete_pattern failed pattern=%s: %s", pattern, exc)
