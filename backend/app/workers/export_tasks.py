from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from celery.exceptions import SoftTimeLimitExceeded

from app.core.celery_app import celery_app
from app.services.export_service import cleanup_expired_exports_async, run_export_job_by_id

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.workers.export_tasks.run_export_task",
    bind=True,
    # Retry với exponential backoff: 1s → 2s → 4s (max 3 lần)
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,         # 1s, 2s, 4s
    retry_backoff_max=60,       # không vượt quá 60s
    retry_jitter=True,          # tránh thundering herd
    acks_late=True,
    time_limit=600,             # hard kill sau 10 phút
    soft_time_limit=550,        # graceful shutdown 50s trước hard kill
)
def run_export_task(self, job_id: str, request_dict: dict[str, Any]) -> dict[str, Any]:
    try:
        asyncio.run(run_export_job_by_id(uuid.UUID(job_id), request_dict))
        return {"job_id": job_id, "status": "done"}
    except SoftTimeLimitExceeded:
        logger.warning("export_task_timeout", job_id=job_id)
        raise


@celery_app.task(
    name="app.workers.export_tasks.cleanup_expired_exports",
    acks_late=True,
    time_limit=300,
    ignore_result=True,
)
def cleanup_expired_exports() -> dict[str, int]:
    return asyncio.run(cleanup_expired_exports_async())
