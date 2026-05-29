"""Structured logging setup (Plan 15.5 Vận hành).

Dùng structlog để output JSON — dễ ship sang Loki/CloudWatch/ELK.
Gọi setup_logging() một lần khi khởi động app (trong main.py).
"""
from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO

    # Root Python logging → stdout
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
