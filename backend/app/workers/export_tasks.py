from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.core.celery_app import celery_app
from app.services.export_service import cleanup_expired_exports_async, run_export_job_by_id


@celery_app.task(name="app.workers.export_tasks.run_export_task", bind=True, max_retries=2, default_retry_delay=10, acks_late=True)
def run_export_task(self, job_id: str, request_dict: dict[str, Any]) -> dict[str, Any]:
    asyncio.run(run_export_job_by_id(uuid.UUID(job_id), request_dict))
    return {"job_id": job_id, "status": "done"}


@celery_app.task(name="app.workers.export_tasks.cleanup_expired_exports")
def cleanup_expired_exports() -> dict[str, int]:
    return asyncio.run(cleanup_expired_exports_async())
