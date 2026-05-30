"""Backup notification helpers for backup/restore scripts."""
from __future__ import annotations

import asyncio
import html
import os
import socket
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notification_service import _send_email_smtp, _smtp_configured, get_hr_recipients


def _env_recipients() -> list[str]:
    raw = os.getenv("BACKUP_NOTIFY_EMAILS", "")
    if not raw.strip():
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


async def resolve_backup_recipients(
    session: AsyncSession,
    override_recipients: Sequence[str] | None = None,
) -> list[str]:
    if override_recipients:
        return [item.strip() for item in override_recipients if item and item.strip()]

    env_recipients = _env_recipients()
    if env_recipients:
        return env_recipients

    return await get_hr_recipients(session)


def _subject_for(job_name: str, status: str) -> str:
    status_label = "THÀNH CÔNG" if status == "success" else "THẤT BẠI"
    return f"[HRMS][Backup][{status_label}] {job_name}"


def _format_timestamp(value: str) -> str:
    raw = value.strip()
    if not raw:
        return raw
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return raw.replace("T", " ")

    formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
    offset = dt.strftime("%z")
    if offset:
        offset = f"{offset[:3]}:{offset[3:]}"
        return f"{formatted} {offset}"
    return formatted


def _html_body(
    *,
    job_name: str,
    status: str,
    summary: str,
    details: str,
    started_at: str,
    finished_at: str,
    hostname: str,
    ) -> str:
    status_label = "Thành công" if status == "success" else "Thất bại"
    status_color = "#15803d" if status == "success" else "#b91c1c"
    started_at_display = _format_timestamp(started_at)
    finished_at_display = _format_timestamp(finished_at)
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #111827;">
        <h2 style="margin-bottom: 12px;">Thông báo backup HRMS</h2>
        <table cellpadding="6" cellspacing="0" border="0">
          <tr><td><strong>Tác vụ</strong></td><td>{html.escape(job_name)}</td></tr>
          <tr><td><strong>Trạng thái</strong></td><td style="color:{status_color};"><strong>{status_label}</strong></td></tr>
          <tr><td><strong>Máy chạy</strong></td><td>{html.escape(hostname)}</td></tr>
          <tr><td><strong>Bắt đầu</strong></td><td>{html.escape(started_at_display)}</td></tr>
          <tr><td><strong>Kết thúc</strong></td><td>{html.escape(finished_at_display)}</td></tr>
          <tr><td><strong>Tóm tắt</strong></td><td>{html.escape(summary)}</td></tr>
        </table>
        <p style="margin-top: 16px;"><strong>Chi tiết</strong></p>
        <pre style="background:#f3f4f6; padding:12px; border-radius:8px; white-space:pre-wrap;">{html.escape(details)}</pre>
      </body>
    </html>
    """.strip()


async def send_backup_status_email(
    session: AsyncSession,
    *,
    job_name: str,
    status: str,
    summary: str,
    details: str,
    started_at: str,
    finished_at: str,
    hostname: str | None = None,
    override_recipients: Sequence[str] | None = None,
) -> dict:
    if status not in {"success", "failed"}:
        raise ValueError("status must be 'success' or 'failed'")

    recipients = await resolve_backup_recipients(session, override_recipients)
    if not recipients:
        return {"status": "skipped", "reason": "no_recipients", "recipients": []}

    if not _smtp_configured():
        return {"status": "skipped", "reason": "smtp_not_configured", "recipients": recipients}

    host = hostname or socket.gethostname()
    subject = _subject_for(job_name, status)
    body_html = _html_body(
        job_name=job_name,
        status=status,
        summary=summary,
        details=details,
        started_at=started_at,
        finished_at=finished_at,
        hostname=host,
    )

    loop = asyncio.get_running_loop()
    sent: list[str] = []
    failed: dict[str, str] = {}

    for recipient in recipients:
        try:
            await loop.run_in_executor(None, _send_email_smtp, recipient, subject, body_html)
            sent.append(recipient)
        except Exception as exc:  # pragma: no cover - exercised via integration seam
            failed[recipient] = str(exc)

    result_status = "sent" if sent and not failed else "partial" if sent else "failed"
    return {
        "status": result_status,
        "job_name": job_name,
        "recipients": recipients,
        "sent": sent,
        "failed": failed,
        "subject": subject,
    }
