"""Celery application — khởi tạo và cấu hình beat schedule."""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

_redis_url = settings.effective_redis_url

celery_app = Celery(
    "hrms",
    broker=_redis_url,
    backend=_redis_url,
    include=["app.workers.tasks", "app.workers.export_tasks", "app.workers.backup_tasks"],
)

celery_app.conf.update(
    timezone=settings.APP_TIMEZONE,
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # ── Reliability ─────────────────────────────────────────────────────────
    # acks_late=True: task chỉ được ACK sau khi hoàn thành (không mất khi worker crash)
    task_acks_late=True,
    # Reject (not requeue) task nếu worker bị SIGKILL giữa chừng
    task_reject_on_worker_lost=True,
    # Kết quả giữ 24h trong Redis
    result_expires=86400,

    # ── Routing ─────────────────────────────────────────────────────────────
    task_routes={
        "app.workers.export_tasks.run_export_task": {"queue": "exports"},
        "app.workers.backup_tasks.run_backup_job_task": {"queue": "backups"},
        "app.workers.backup_tasks.run_backup_set_task": {"queue": "backups"},
        "app.workers.backup_tasks.run_restore_request_task": {"queue": "backups"},
        "app.workers.backup_tasks.dispatch_scheduled_backup_set_task": {"queue": "backups"},
    },

    # ── RedBeat distributed scheduler ───────────────────────────────────────
    # Ngăn duplicate schedule khi scale nhiều celery_beat instance.
    # Chỉ 1 instance giữ lock tại một thời điểm.
    redbeat_redis_url=_redis_url,
    redbeat_lock_timeout=60 * 5,   # 5 phút — tự động giải phóng nếu beat crash

    beat_schedule={
        "expire-overdue-contracts": {
            "task": "app.workers.tasks.expire_overdue_contracts",
            "schedule": crontab(hour=0, minute=5),
        },
        "reset-expired-carryover": {
            "task": "app.workers.tasks.reset_expired_carryover",
            "schedule": crontab(hour=0, minute=5, day_of_month=1, month_of_year=4),
        },
        "expire-stale-postings": {
            "task": "app.workers.tasks.expire_stale_postings",
            "schedule": crontab(hour=0, minute=10),
        },
        "cleanup-expired-exports": {
            "task": "app.workers.export_tasks.cleanup_expired_exports",
            "schedule": crontab(hour=1, minute=0),
        },
        "send-daily-notifications": {
            "task": "app.workers.tasks.send_daily_notifications",
            "schedule": crontab(hour=8, minute=0),
        },
        "ping-healthcheck": {
            "task": "app.workers.tasks.ping_healthcheck",
            "schedule": 60.0,
        },
        "dispatch-scheduled-full-backup": {
            "task": "app.workers.backup_tasks.dispatch_scheduled_backup_set_task",
            "schedule": 60.0,
        },
    },
)
