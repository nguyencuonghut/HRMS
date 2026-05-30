from __future__ import annotations

import asyncio
import json
import os
import sys

from app.core.database import AsyncSessionLocal
from app.services.backup_notification_service import send_backup_status_email


async def _main() -> int:
    job_name = os.getenv("BACKUP_NOTIFY_JOB_NAME", "").strip()
    status = os.getenv("BACKUP_NOTIFY_STATUS", "").strip()
    summary = os.getenv("BACKUP_NOTIFY_SUMMARY", "").strip()
    details = os.getenv("BACKUP_NOTIFY_DETAILS", "").strip()
    started_at = os.getenv("BACKUP_NOTIFY_STARTED_AT", "").strip()
    finished_at = os.getenv("BACKUP_NOTIFY_FINISHED_AT", "").strip()
    hostname = os.getenv("BACKUP_NOTIFY_HOSTNAME", "").strip() or None
    recipients_env = os.getenv("BACKUP_NOTIFY_RECIPIENTS", "").strip()
    override_recipients = [item.strip() for item in recipients_env.split(",") if item.strip()] if recipients_env else None

    missing = [
        name for name, value in [
            ("BACKUP_NOTIFY_JOB_NAME", job_name),
            ("BACKUP_NOTIFY_STATUS", status),
            ("BACKUP_NOTIFY_SUMMARY", summary),
            ("BACKUP_NOTIFY_DETAILS", details),
            ("BACKUP_NOTIFY_STARTED_AT", started_at),
            ("BACKUP_NOTIFY_FINISHED_AT", finished_at),
        ] if not value
    ]
    if missing:
        print(json.dumps({"status": "error", "missing_env": missing}), file=sys.stderr)
        return 2

    async with AsyncSessionLocal() as session:
        result = await send_backup_status_email(
            session,
            job_name=job_name,
            status=status,
            summary=summary,
            details=details,
            started_at=started_at,
            finished_at=finished_at,
            hostname=hostname,
            override_recipients=override_recipients,
        )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in {"sent", "partial", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
