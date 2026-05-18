"""Celery application — khởi tạo và cấu hình beat schedule."""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "hrms",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    beat_schedule={
        "expire-overdue-contracts": {
            "task": "app.workers.tasks.expire_overdue_contracts",
            "schedule": crontab(hour=0, minute=5),  # 00:05 hàng ngày
        },
    },
)
