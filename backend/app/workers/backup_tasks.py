"""Celery tasks cho tác vụ sao lưu thủ công."""
from __future__ import annotations

import asyncio

import structlog

from app.core.celery_app import celery_app
from app.workers.tasks import _make_engine_and_session
from app.services import backup_service

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.workers.backup_tasks.run_backup_job_task",
    acks_late=True,
    time_limit=7200,
    soft_time_limit=7100,
    ignore_result=True,
)
def run_backup_job_task(job_id: int) -> None:
    asyncio.run(_run_backup_job_task_async(job_id))


async def _run_backup_job_task_async(job_id: int) -> None:
    engine, SessionLocal = _make_engine_and_session()
    try:
        async with SessionLocal() as session:
            await backup_service.run_backup_job(session, job_id=job_id)
    except backup_service.BackupJobNotFound:
        logger.warning("backup_job_not_found", job_id=job_id)
    finally:
        await engine.dispose()
