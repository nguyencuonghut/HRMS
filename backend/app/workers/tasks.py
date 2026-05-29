"""Celery tasks — tác vụ nền định kỳ."""
from __future__ import annotations

import asyncio
import logging
from datetime import date

logger = logging.getLogger(__name__)

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.employee_contract import EmployeeContract
from app.models.recruitment import JobPosting


@celery_app.task(name="app.workers.tasks.expire_overdue_contracts")
def expire_overdue_contracts() -> int:
    """
    Cập nhật status = 'expired' cho tất cả hợp đồng đã quá ngày effective_to.
    Chạy hàng ngày lúc 00:05. Idempotent — an toàn khi chạy nhiều lần.
    Trả về số bản ghi đã cập nhật.
    """
    return asyncio.run(_expire_overdue_contracts_async())


async def _expire_overdue_contracts_async() -> int:
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with SessionLocal() as session:
            result = await session.execute(
                update(EmployeeContract)
                .where(
                    EmployeeContract.effective_to.isnot(None),
                    EmployeeContract.effective_to < date.today(),
                    EmployeeContract.status.in_(["active", "draft"]),
                )
                .values(status="expired")
                .execution_options(synchronize_session=False)
            )
            await session.commit()
            return result.rowcount
    finally:
        await engine.dispose()


@celery_app.task(name="app.workers.tasks.reset_expired_carryover")
def reset_expired_carryover() -> dict:
    """
    Hủy carryover phép đã hết hạn (FIFO: chỉ phần chưa dùng hết).
    Chạy 00:05 ngày 01/04 hàng năm. Idempotent.
    """
    return asyncio.run(_reset_expired_carryover_async())


@celery_app.task(name="app.workers.tasks.expire_stale_postings")
def expire_stale_postings() -> int:
    """
    Cập nhật status = 'expired' cho tin tuyển dụng đã quá hạn deadline.
    Chạy hàng ngày lúc 00:10. Idempotent.
    """
    return asyncio.run(_expire_stale_postings_async())


async def _expire_stale_postings_async() -> int:
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with SessionLocal() as session:
            result = await session.execute(
                update(JobPosting)
                .where(
                    JobPosting.status == "active",
                    JobPosting.deadline.isnot(None),
                    JobPosting.deadline < date.today(),
                )
                .values(status="expired")
                .execution_options(synchronize_session=False)
            )
            await session.commit()
            return result.rowcount
    finally:
        await engine.dispose()


@celery_app.task(name="app.workers.tasks.send_daily_notifications")
def send_daily_notifications() -> dict:
    """Gửi email nhắc việc hàng ngày lúc 08:00."""
    return asyncio.run(_send_daily_notifications_async())


async def _send_daily_notifications_async() -> dict:
    from app.services import notification_service

    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    sent = failed = skipped = 0
    try:
        async with SessionLocal() as session:
            tasks = await notification_service.get_pending_notifications(session)
            hr_emails = await notification_service.get_hr_recipients(session)
            for task in tasks:
                if await notification_service._already_sent_today(
                    session, task.template_code, task.employee_id
                ):
                    skipped += 1
                    continue
                recipients = (
                    hr_emails
                    if task.recipient_type == "hr"
                    else ([task.employee_email] if task.employee_email else hr_emails)
                )
                for email in recipients:
                    ok = await notification_service.send_notification_email(
                        task.template_code,
                        email,
                        task.recipient_name,
                        task.merge_data,
                        session,
                        employee_id=task.employee_id,
                    )
                    if ok:
                        sent += 1
                    else:
                        failed += 1
    finally:
        await engine.dispose()
    return {"sent": sent, "failed": failed, "skipped": skipped}


async def _reset_expired_carryover_async() -> dict:
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with SessionLocal() as session:
            # Chỉ reset hàng còn carryover_days > used_days (phần carryover chưa dùng hết)
            result = await session.execute(
                text("""
                    UPDATE leave_entitlements
                    SET carryover_days = 0,
                        updated_at     = now(),
                        note           = COALESCE(note || ' | ', '')
                                         || 'Hủy ' || GREATEST(0, carryover_days - used_days)::text
                                         || ' ngày dư [' || CURRENT_DATE || ']'
                    WHERE carryover_expires IS NOT NULL
                      AND carryover_expires < CURRENT_DATE
                      AND carryover_days > used_days
                """)
            )
            await session.commit()
            return {"reset_rows": result.rowcount}
    finally:
        await engine.dispose()


@celery_app.task(name="app.workers.tasks.ping_healthcheck")
def ping_healthcheck() -> str:
    """Ping uptime monitoring service (healthchecks.io).
    Chạy mỗi 60 giây — nếu bị gián đoạn hơn 5 phút → alert.
    """
    if not settings.HEALTHCHECK_PING_URL:
        return "skipped: HEALTHCHECK_PING_URL not set"
    import httpx
    try:
        httpx.get(settings.HEALTHCHECK_PING_URL, timeout=10)
        return "ok"
    except Exception as exc:
        logger.warning("healthcheck_ping_failed url=%s err=%s", settings.HEALTHCHECK_PING_URL, exc)
        return f"failed: {exc}"
