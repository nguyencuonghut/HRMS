import os

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services import backup_notification_service


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


def test_format_timestamp_removes_iso_t_separator():
    assert backup_notification_service._format_timestamp("2026-05-30T02:00:00+07:00") == "2026-05-30 02:00:00 +07:00"
    assert backup_notification_service._format_timestamp("2026-05-30 02:00:00") == "2026-05-30 02:00:00"


@pytest.mark.asyncio
async def test_resolve_backup_recipients_prefers_env(monkeypatch):
    monkeypatch.setenv("BACKUP_NOTIFY_EMAILS", "ops@example.com, admin@example.com ")
    Session = _make_session()
    async with Session() as session:
        recipients = await backup_notification_service.resolve_backup_recipients(session)
    assert recipients == ["ops@example.com", "admin@example.com"]


@pytest.mark.asyncio
async def test_send_backup_status_email_uses_hr_recipients(monkeypatch):
    sent_calls: list[tuple[str, str, str]] = []

    monkeypatch.delenv("BACKUP_NOTIFY_EMAILS", raising=False)
    monkeypatch.setattr(backup_notification_service, "_smtp_configured", lambda: True)
    async def _fake_get_hr_recipients(session):
        return ["admin@hrms.local", "hr@hrms.local"]

    monkeypatch.setattr(
        backup_notification_service,
        "get_hr_recipients",
        _fake_get_hr_recipients,
    )
    monkeypatch.setattr(
        backup_notification_service,
        "_send_email_smtp",
        lambda to_email, subject, body_html: sent_calls.append((to_email, subject, body_html)),
    )

    Session = _make_session()
    async with Session() as session:
        result = await backup_notification_service.send_backup_status_email(
            session,
            job_name="PostgreSQL backup",
            status="success",
            summary="Backup created",
            details="file=/backups/postgres/hrms_20260530.sql.gz",
            started_at="2026-05-30T02:00:00+07:00",
            finished_at="2026-05-30T02:01:00+07:00",
            hostname="backup-host",
        )

    assert result["status"] == "sent"
    assert [item[0] for item in sent_calls] == ["admin@hrms.local", "hr@hrms.local"]
    assert "[HRMS][Backup][THÀNH CÔNG] PostgreSQL backup" == sent_calls[0][1]
    assert "Backup created" in sent_calls[0][2]
    assert "backup-host" in sent_calls[0][2]
    assert "2026-05-30 02:00:00 +07:00" in sent_calls[0][2]
    assert "2026-05-30T02:00:00+07:00" not in sent_calls[0][2]


@pytest.mark.asyncio
async def test_send_backup_status_email_skips_when_smtp_not_configured(monkeypatch):
    monkeypatch.setenv("BACKUP_NOTIFY_EMAILS", "ops@example.com")
    monkeypatch.setattr(backup_notification_service, "_smtp_configured", lambda: False)

    Session = _make_session()
    async with Session() as session:
        result = await backup_notification_service.send_backup_status_email(
            session,
            job_name="MinIO backup",
            status="failed",
            summary="Mirror failed",
            details="mc ls backup/ returned non-zero",
            started_at="2026-05-30T03:00:00+07:00",
            finished_at="2026-05-30T03:01:00+07:00",
        )

    assert result == {
        "status": "skipped",
        "reason": "smtp_not_configured",
        "recipients": ["ops@example.com"],
    }
