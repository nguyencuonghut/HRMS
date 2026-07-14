"""Celery tasks cho tác vụ sao lưu thủ công."""
from __future__ import annotations

import asyncio

import structlog

from app.core.celery_app import celery_app
from app.workers.tasks import _make_engine_and_session
from app.services import backup_service

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.workers.backup_tasks.dispatch_scheduled_backup_set_task",
    acks_late=True,
    time_limit=300,
    soft_time_limit=240,
    ignore_result=True,
)
def dispatch_scheduled_backup_set_task() -> None:
    asyncio.run(_dispatch_scheduled_backup_set_task_async())


async def _dispatch_scheduled_backup_set_task_async() -> None:
    engine, SessionLocal = _make_engine_and_session()
    try:
        async with SessionLocal() as session:
            backup_set = await backup_service.create_scheduled_backup_set_if_due(session)
            if backup_set is None:
                await session.rollback()
                return

            backup_set_id = backup_set.id
            await session.commit()
            logger.info("scheduled_backup_set_created", backup_set_id=backup_set_id)
            backup_service.enqueue_backup_set(backup_set_id)
    finally:
        await engine.dispose()


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


@celery_app.task(
    name="app.workers.backup_tasks.run_backup_set_task",
    acks_late=True,
    time_limit=14400,
    soft_time_limit=14300,
    ignore_result=True,
)
def run_backup_set_task(backup_set_id: int) -> None:
    asyncio.run(_run_backup_set_task_async(backup_set_id))


async def _run_backup_set_task_async(backup_set_id: int) -> None:
    engine, SessionLocal = _make_engine_and_session()
    try:
        async with SessionLocal() as session:
            await backup_service.run_backup_set(session, backup_set_id=backup_set_id)
    except backup_service.BackupSetNotFound:
        logger.warning("backup_set_not_found", backup_set_id=backup_set_id)
    finally:
        await engine.dispose()


@celery_app.task(
    name="app.workers.backup_tasks.run_restore_request_task",
    acks_late=True,
    time_limit=7200,
    soft_time_limit=7100,
    ignore_result=True,
)
def run_restore_request_task(restore_request_id: int) -> None:
    asyncio.run(_run_restore_request_task_async(restore_request_id))


async def _run_restore_request_task_async(restore_request_id: int) -> None:
    engine, SessionLocal = _make_engine_and_session()
    try:
        async with SessionLocal() as session:
            await backup_service.run_restore_request(session, restore_request_id=restore_request_id)
    except backup_service.RestoreRequestNotFound:
        logger.warning("restore_request_not_found", restore_request_id=restore_request_id)
    finally:
        await engine.dispose()
