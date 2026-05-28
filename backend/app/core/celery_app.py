"""Celery application — khởi tạo và cấu hình beat schedule."""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "hrms",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks", "app.workers.export_tasks"],
)

celery_app.conf.update(
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_routes={
        "app.workers.export_tasks.run_export_task": {"queue": "exports"},
    },
    beat_schedule={
        "expire-overdue-contracts": {
            "task": "app.workers.tasks.expire_overdue_contracts",
            "schedule": crontab(hour=0, minute=5),              # 00:05 hàng ngày
        },
        "reset-expired-carryover": {
            "task": "app.workers.tasks.reset_expired_carryover",
            "schedule": crontab(hour=0, minute=5, day_of_month=1, month_of_year=4),  # 00:05 ngày 01/04
        },
        "expire-stale-postings": {
            "task": "app.workers.tasks.expire_stale_postings",
            "schedule": crontab(hour=0, minute=10),  # 00:10 hàng ngày
        },
        "cleanup-expired-exports": {
            "task": "app.workers.export_tasks.cleanup_expired_exports",
            "schedule": crontab(hour=1, minute=0),
        },
    },
)
