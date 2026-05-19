"""Celery tasks — tác vụ nền định kỳ."""
from __future__ import annotations

import asyncio
from datetime import date

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.employee_contract import EmployeeContract


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
