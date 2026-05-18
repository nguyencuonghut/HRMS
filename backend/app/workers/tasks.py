"""Celery tasks — tác vụ nền định kỳ."""
from __future__ import annotations

import asyncio
from datetime import date

from sqlalchemy import update
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
