"""Celery tasks — tác vụ nền định kỳ."""
from __future__ import annotations

import asyncio
from datetime import date

import structlog
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.employee_contract import EmployeeContract
from app.models.recruitment import JobPosting

logger = structlog.get_logger(__name__)

# ── Shared task kwargs cho beat tasks ─────────────────────────────────────────
# Áp dụng cho các tác vụ định kỳ (idempotent, không cần retry):
# - acks_late: ACK sau khi xong, không mất nếu worker crash
# - time_limit: hard kill sau 1 giờ (phòng zombie tasks)
# - soft_time_limit: graceful shutdown 100s trước hard kill
_BEAT_TASK_OPTS = dict(
    acks_late=True,
    time_limit=3600,
    soft_time_limit=3500,
    ignore_result=True,   # Beat tasks không cần lưu kết quả trong Redis
)


def _make_engine_and_session():
    """Tạo DB engine và sessionmaker riêng cho mỗi Celery task."""
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(name="app.workers.tasks.expire_overdue_contracts", **_BEAT_TASK_OPTS)
def expire_overdue_contracts() -> int:
    """
    Cập nhật status = 'expired' cho tất cả hợp đồng đã quá ngày effective_to.
    Chạy hàng ngày lúc 00:05. Idempotent — an toàn khi chạy nhiều lần.
    Trả về số bản ghi đã cập nhật.
    """
    return asyncio.run(_expire_overdue_contracts_async())


async def _expire_overdue_contracts_async() -> int:
    engine, SessionLocal = _make_engine_and_session()
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
            count = result.rowcount
            if count:
                logger.info("contracts_expired", count=count)
            return count
    finally:
        await engine.dispose()


@celery_app.task(name="app.workers.tasks.reset_expired_carryover", **_BEAT_TASK_OPTS)
def reset_expired_carryover() -> dict:
    """
    Hủy carryover phép đã hết hạn (FIFO: chỉ phần chưa dùng hết).
    Chạy 00:05 ngày 01/04 hàng năm. Idempotent.
    """
    return asyncio.run(_reset_expired_carryover_async())


@celery_app.task(name="app.workers.tasks.expire_stale_postings", **_BEAT_TASK_OPTS)
def expire_stale_postings() -> int:
    """
    Cập nhật status = 'expired' cho tin tuyển dụng đã quá hạn deadline.
    Chạy hàng ngày lúc 00:10. Idempotent.
    """
    return asyncio.run(_expire_stale_postings_async())


async def _expire_stale_postings_async() -> int:
    engine, SessionLocal = _make_engine_and_session()
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
            count = result.rowcount
            if count:
                logger.info("postings_expired", count=count)
            return count
    finally:
        await engine.dispose()


@celery_app.task(name="app.workers.tasks.send_daily_notifications", **_BEAT_TASK_OPTS)
def send_daily_notifications() -> dict:
    """Gửi email nhắc việc hàng ngày lúc 08:00."""
    return asyncio.run(_send_daily_notifications_async())


async def _send_daily_notifications_async() -> dict:
    from app.services import notification_service

    engine, SessionLocal = _make_engine_and_session()
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
    logger.info("notifications_sent", sent=sent, failed=failed, skipped=skipped)
    return {"sent": sent, "failed": failed, "skipped": skipped}


async def _reset_expired_carryover_async() -> dict:
    engine, SessionLocal = _make_engine_and_session()
    try:
        async with SessionLocal() as session:
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
            count = result.rowcount
            if count:
                logger.info("carryover_reset", count=count)
            return {"reset_rows": count}
    finally:
        await engine.dispose()


@celery_app.task(
    name="app.workers.tasks.ping_healthcheck",
    acks_late=True,
    time_limit=30,          # ping timeout ngắn
    ignore_result=True,
)
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
        logger.warning("healthcheck_ping_failed", url=settings.HEALTHCHECK_PING_URL, error=str(exc))
        return f"failed: {exc}"
