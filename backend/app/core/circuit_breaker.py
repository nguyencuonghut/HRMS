"""Circuit Breaker cho external services (H4 — Production Improvements).

Ngăn cascading failure khi MinIO / SMTP bị gián đoạn.

States:
  CLOSED     → hoạt động bình thường, mọi call đều pass
  OPEN       → đang lỗi, fail-fast ngay lập tức (không gọi service)
  HALF-OPEN  → đang thử hồi phục, cho 1 probe call qua

Thread-safe: dùng threading.Lock để tương thích cả FastAPI và Celery workers.
"""
from __future__ import annotations

import logging
import threading
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class _State(str, Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker đơn giản, thread-safe.

    Params:
        name             — tên dịch vụ (hiện trong log)
        failure_threshold — số lần lỗi liên tiếp trước khi OPEN
        recovery_timeout  — giây chờ trước khi thử HALF-OPEN
        expected_exception — exception type(s) được tính là failure
                             (None = bắt tất cả Exception)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] | tuple[type[Exception], ...] | None = None,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception or Exception

        self._state = _State.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state.value

    def call(self, func: F) -> F:
        """Decorator: bọc function với circuit breaker logic."""
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self._before_call()
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as exc:
                self._on_failure(exc)
                raise

        return wrapper  # type: ignore[return-value]

    def is_open(self) -> bool:
        with self._lock:
            return self._state == _State.OPEN and not self._should_attempt_reset()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _before_call(self) -> None:
        with self._lock:
            if self._state == _State.OPEN:
                if self._should_attempt_reset():
                    self._state = _State.HALF_OPEN
                    logger.info("circuit_half_open", extra={"circuit": self.name})
                else:
                    raise CircuitOpenError(
                        f"Circuit '{self.name}' OPEN — service unavailable. "
                        f"Retry in {self._seconds_until_reset():.0f}s."
                    )

    def _on_success(self) -> None:
        with self._lock:
            if self._state in (_State.HALF_OPEN, _State.OPEN):
                logger.info(
                    "circuit_closed",
                    extra={"circuit": self.name, "was_state": self._state.value},
                )
            self._state = _State.CLOSED
            self._failure_count = 0

    def _on_failure(self, exc: Exception) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._failure_count >= self.failure_threshold:
                if self._state != _State.OPEN:
                    logger.warning(
                        "circuit_opened",
                        extra={
                            "circuit": self.name,
                            "failures": self._failure_count,
                            "error": str(exc),
                        },
                    )
                self._state = _State.OPEN

    def _should_attempt_reset(self) -> bool:
        return (time.monotonic() - self._last_failure_time) >= self.recovery_timeout

    def _seconds_until_reset(self) -> float:
        elapsed = time.monotonic() - self._last_failure_time
        return max(self.recovery_timeout - elapsed, 0)


class CircuitOpenError(RuntimeError):
    """Raise khi circuit đang OPEN và call bị chặn."""


# ── Singletons cho từng external service ─────────────────────────────────────

minio_circuit = CircuitBreaker(
    name="minio",
    failure_threshold=3,
    recovery_timeout=30,   # 30s — MinIO thường hồi phục nhanh
)

smtp_circuit = CircuitBreaker(
    name="smtp",
    failure_threshold=2,
    recovery_timeout=120,  # 2 phút — SMTP down thường lâu hơn
)
