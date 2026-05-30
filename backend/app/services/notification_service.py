"""Notification service — quản lý template email, gửi thông báo tự động."""
from __future__ import annotations

import asyncio
import re
import smtplib
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.circuit_breaker import smtp_circuit
from app.core.config import settings
from app.models.auth import Role, User, UserRole
from app.models.employee import Employee
from app.models.employee_contract import EmployeeContract
from app.models.employee_job import EmployeeJobRecord
from app.models.leave_entitlement import LeaveEntitlement
from app.models.notification import EmailLog, NotificationTemplate, NotifConfig


# ─── Dataclass ────────────────────────────────────────────────────────────────

@dataclass
class NotificationTask:
    template_code: str
    event_type: str
    employee_id: int | None
    employee_email: str | None
    recipient_name: str
    merge_data: dict
    recipient_type: str = "hr"


# ─── Template rendering ───────────────────────────────────────────────────────

def _render_template(text: str, merge_data: dict) -> str:
    """Replace {{field}} placeholders với giá trị trong merge_data."""
    def _replace(m: re.Match) -> str:
        key = m.group(1).strip()
        return str(merge_data.get(key, m.group(0)))

    return re.sub(r"\{\{(.+?)\}\}", _replace, text)


# ─── SMTP ─────────────────────────────────────────────────────────────────────

@smtp_circuit.call
def _send_email_smtp(to_email: str, subject: str, body_html: str) -> None:
    """Gửi email qua SMTP. Circuit-protected — raise CircuitOpenError khi SMTP đang down."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM_EMAIL))
    msg["To"] = to_email
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    smtp_cls = smtplib.SMTP_SSL if settings.SMTP_USE_TLS else smtplib.SMTP
    with smtp_cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        if settings.SMTP_USE_STARTTLS:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())


def _smtp_configured() -> bool:
    """Kiểm tra xem SMTP đã được cấu hình thực sự chưa."""
    return bool(settings.SMTP_HOST) and settings.SMTP_HOST not in ("localhost", "")


# ─── Core send ────────────────────────────────────────────────────────────────

async def send_notification_email(
    template_code: str,
    recipient_email: str,
    recipient_name: str,
    merge_data: dict,
    session: AsyncSession,
    *,
    employee_id: int | None = None,
    celery_task_id: str | None = None,
) -> bool:
    """Render template, gửi email, ghi log. Return True nếu sent/skipped."""
    # 1. Load template
    template = (
        await session.execute(
            select(NotificationTemplate).where(NotificationTemplate.code == template_code)
        )
    ).scalar_one_or_none()

    if template is None:
        await _write_log(
            session,
            template_code=template_code,
            event_type=template_code,
            employee_id=employee_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=None,
            status="failed",
            error_message=f"Template '{template_code}' not found",
            celery_task_id=celery_task_id,
        )
        return False

    if not template.is_active:
        await _write_log(
            session,
            template_code=template_code,
            event_type=template.event_type,
            employee_id=employee_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=template.subject,
            status="skipped",
            error_message="Template inactive",
            celery_task_id=celery_task_id,
        )
        return True

    # 2. Render
    rendered_subject = _render_template(template.subject, merge_data)
    rendered_body = _render_template(template.body_html, merge_data)

    # 3. Nếu SMTP chưa config → log skipped
    if not _smtp_configured():
        await _write_log(
            session,
            template_code=template_code,
            event_type=template.event_type,
            employee_id=employee_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=rendered_subject,
            status="skipped",
            error_message="SMTP not configured",
            celery_task_id=celery_task_id,
        )
        return True

    # 4. Gửi email (circuit-protected — fail-fast nếu SMTP đang down)
    from app.core.circuit_breaker import CircuitOpenError
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send_email_smtp, recipient_email, rendered_subject, rendered_body)
        status = "sent"
        error_message = None
    except CircuitOpenError as exc:
        # Circuit đang OPEN → không retry, log skipped để không block Celery task
        status = "skipped"
        error_message = f"SMTP circuit open: {exc}"
    except Exception as exc:
        status = "failed"
        error_message = str(exc)

    # 5. Ghi log
    await _write_log(
        session,
        template_code=template_code,
        event_type=template.event_type,
        employee_id=employee_id,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=rendered_subject,
        status=status,
        error_message=error_message,
        celery_task_id=celery_task_id,
    )

    return status in ("sent", "skipped")


async def _write_log(
    session: AsyncSession,
    *,
    template_code: str | None,
    event_type: str,
    employee_id: int | None,
    recipient_email: str,
    recipient_name: str | None,
    subject: str | None,
    status: str,
    error_message: str | None,
    celery_task_id: str | None = None,
) -> None:
    log = EmailLog(
        template_code=template_code,
        event_type=event_type,
        employee_id=employee_id,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=subject,
        status=status,
        error_message=error_message,
        celery_task_id=celery_task_id,
        sent_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(log)
    await session.flush()


# ─── Dedup check ──────────────────────────────────────────────────────────────

async def _already_sent_today(
    session: AsyncSession,
    template_code: str,
    employee_id: int | None,
) -> bool:
    """Kiểm tra đã gửi template này cho nhân viên này hôm nay chưa."""
    today = date.today()
    q = select(EmailLog.id).where(
        EmailLog.template_code == template_code,
        EmailLog.status == "sent",
        func.date(EmailLog.sent_at) == today,
    )
    if employee_id is not None:
        q = q.where(EmailLog.employee_id == employee_id)
    result = (await session.execute(q.limit(1))).scalar_one_or_none()
    return result is not None


# ─── HR recipients ────────────────────────────────────────────────────────────

async def get_hr_recipients(session: AsyncSession) -> list[str]:
    """Trả về danh sách email HR/admin để nhận thông báo."""
    # Superusers
    superuser_emails = (
        await session.execute(
            select(User.email).where(
                User.is_active.is_(True),
                User.is_superuser.is_(True),
            )
        )
    ).scalars().all()

    # Users có role admin hoặc hr_manager
    role_emails = (
        await session.execute(
            select(User.email)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                User.is_active.is_(True),
                Role.code.in_(["admin", "hr_manager"]),
            )
        )
    ).scalars().all()

    # Deduplicate, preserve order
    seen: set[str] = set()
    result: list[str] = []
    for email in list(superuser_emails) + list(role_emails):
        if email not in seen:
            seen.add(email)
            result.append(email)
    return result


# ─── Pending notifications ────────────────────────────────────────────────────

async def get_pending_notifications(
    session: AsyncSession,
    reference_date: date | None = None,
) -> list[NotificationTask]:
    """Thu thập tất cả thông báo cần gửi theo ngày tham chiếu."""
    ref = reference_date or date.today()
    tasks: list[NotificationTask] = []

    # Kiểm tra config
    configs: dict[str, NotifConfig] = {}
    cfg_rows = (
        await session.execute(select(NotifConfig).where(NotifConfig.is_enabled.is_(True)))
    ).scalars().all()
    for cfg in cfg_rows:
        configs[cfg.event_type] = cfg

    # ── 1. contract_expiry ────────────────────────────────────────────────────
    if "contract_expiry" in configs:
        days_list = configs["contract_expiry"].days_before or [30, 15, 7]
        target_dates = {ref + timedelta(days=d): d for d in days_list}
        if target_dates:
            contracts = (
                await session.execute(
                    select(EmployeeContract, Employee)
                    .join(Employee, Employee.id == EmployeeContract.employee_id)
                    .where(
                        EmployeeContract.status == "active",
                        EmployeeContract.parent_contract_id.is_(None),
                        EmployeeContract.effective_to.isnot(None),
                        EmployeeContract.effective_to.in_(list(target_dates.keys())),
                        Employee.is_active.is_(True),
                    )
                )
            ).all()
            for contract, emp in contracts:
                days_until = target_dates[contract.effective_to]
                template_code = f"contract_expiry_{days_until}d"
                tasks.append(
                    NotificationTask(
                        template_code=template_code,
                        event_type="contract_expiry",
                        employee_id=emp.id,
                        employee_email=None,
                        recipient_name=emp.full_name,
                        merge_data={
                            "employee_name": emp.full_name,
                            "contract_number": contract.contract_number,
                            "expiry_date": str(contract.effective_to),
                            "days_until": str(days_until),
                            "department": "",
                            "company_name": settings.COMPANY_NAME,
                        },
                        recipient_type="hr",
                    )
                )

    # ── 2. probation_end ──────────────────────────────────────────────────────
    if "probation_end" in configs:
        days_list = configs["probation_end"].days_before or [14, 7, 3]
        target_dates = {ref + timedelta(days=d): d for d in days_list}
        if target_dates:
            job_records = (
                await session.execute(
                    select(EmployeeJobRecord, Employee)
                    .join(Employee, Employee.id == EmployeeJobRecord.employee_id)
                    .where(
                        EmployeeJobRecord.is_current.is_(True),
                        EmployeeJobRecord.probation_end_date.isnot(None),
                        EmployeeJobRecord.probation_end_date.in_(list(target_dates.keys())),
                        Employee.is_active.is_(True),
                    )
                )
            ).all()
            for job, emp in job_records:
                days_until = target_dates[job.probation_end_date]
                template_code = f"probation_end_{days_until}d"
                tasks.append(
                    NotificationTask(
                        template_code=template_code,
                        event_type="probation_end",
                        employee_id=emp.id,
                        employee_email=None,
                        recipient_name=emp.full_name,
                        merge_data={
                            "employee_name": emp.full_name,
                            "probation_end_date": str(job.probation_end_date),
                            "days_until": str(days_until),
                            "department": "",
                            "company_name": settings.COMPANY_NAME,
                        },
                        recipient_type="hr",
                    )
                )

    # ── 3. birthday ───────────────────────────────────────────────────────────
    if "birthday" in configs:
        birthday_emps = (
            await session.execute(
                select(Employee).where(
                    Employee.is_active.is_(True),
                    Employee.date_of_birth.isnot(None),
                    func.extract("month", Employee.date_of_birth) == ref.month,
                    func.extract("day", Employee.date_of_birth) == ref.day,
                )
            )
        ).scalars().all()
        for emp in birthday_emps:
            age = ref.year - emp.date_of_birth.year
            tasks.append(
                NotificationTask(
                    template_code="birthday",
                    event_type="birthday",
                    employee_id=emp.id,
                    employee_email=None,
                    recipient_name=emp.full_name,
                    merge_data={
                        "employee_name": emp.full_name,
                        "birth_date": str(emp.date_of_birth),
                        "age": str(age),
                        "company_name": settings.COMPANY_NAME,
                    },
                    recipient_type="hr",
                )
            )

    # ── 4. carryover_expiry ───────────────────────────────────────────────────
    if "carryover_expiry" in configs:
        days_list = configs["carryover_expiry"].days_before or [30]
        target_dates = {ref + timedelta(days=d): d for d in days_list}
        if target_dates:
            entitlements = (
                await session.execute(
                    select(LeaveEntitlement, Employee)
                    .join(Employee, Employee.id == LeaveEntitlement.employee_id)
                    .where(
                        LeaveEntitlement.carryover_expires.isnot(None),
                        LeaveEntitlement.carryover_expires.in_(list(target_dates.keys())),
                        (LeaveEntitlement.allocated_days + LeaveEntitlement.carryover_days - LeaveEntitlement.used_days) > 0,
                        Employee.is_active.is_(True),
                    )
                )
            ).all()
            for ent, emp in entitlements:
                days_until = target_dates[ent.carryover_expires]
                remaining = float(ent.allocated_days + ent.carryover_days - ent.used_days)
                tasks.append(
                    NotificationTask(
                        template_code="carryover_expiry",
                        event_type="carryover_expiry",
                        employee_id=emp.id,
                        employee_email=None,
                        recipient_name=emp.full_name,
                        merge_data={
                            "employee_name": emp.full_name,
                            "remaining_days": str(remaining),
                            "expiry_date": str(ent.carryover_expires),
                            "days_until": str(days_until),
                            "company_name": settings.COMPANY_NAME,
                        },
                        recipient_type="hr",
                    )
                )

    return tasks
