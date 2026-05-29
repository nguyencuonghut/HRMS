"""Seed dữ liệu mặc định cho notification_templates và notification_config."""
from __future__ import annotations

import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_TEMPLATES = [
    {
        "code": "contract_expiry_30d",
        "event_type": "contract_expiry",
        "name": "Hợp đồng sắp hết hạn (30 ngày)",
        "days_before": 30,
        "recipient_type": "hr",
        "subject": "[HRMS] Hợp đồng {{employee_name}} sắp hết hạn",
        "merge_fields": json.dumps(
            ["employee_name", "contract_number", "expiry_date", "days_until", "department", "company_name"]
        ),
        "body_html": (
            "<p>Kính gửi Phòng Nhân sự,</p>"
            "<p>Hợp đồng của <strong>{{employee_name}}</strong> hết hạn sau <strong>{{days_until}} ngày</strong> ({{expiry_date}}).</p>"
            "<p>Số HĐ: {{contract_number}} | Phòng ban: {{department}}</p>"
            "<p>Trân trọng,<br>HRMS {{company_name}}</p>"
        ),
        "body_text": None,
    },
    {
        "code": "contract_expiry_15d",
        "event_type": "contract_expiry",
        "name": "Hợp đồng sắp hết hạn (15 ngày)",
        "days_before": 15,
        "recipient_type": "hr",
        "subject": "[HRMS] Khẩn: Hợp đồng {{employee_name}} còn {{days_until}} ngày",
        "merge_fields": json.dumps(
            ["employee_name", "contract_number", "expiry_date", "days_until", "department", "company_name"]
        ),
        "body_html": (
            "<p>Hợp đồng của <strong>{{employee_name}}</strong> sắp hết hạn (<strong>{{days_until}} ngày</strong>). "
            "Số HĐ: {{contract_number}}.</p>"
        ),
        "body_text": None,
    },
    {
        "code": "contract_expiry_7d",
        "event_type": "contract_expiry",
        "name": "Hợp đồng sắp hết hạn (7 ngày)",
        "days_before": 7,
        "recipient_type": "hr",
        "subject": "[HRMS] CẤP THIẾT: Hợp đồng {{employee_name}} còn 7 ngày",
        "merge_fields": json.dumps(
            ["employee_name", "contract_number", "expiry_date", "days_until", "department", "company_name"]
        ),
        "body_html": (
            "<p>Hợp đồng <strong>{{contract_number}}</strong> của {{employee_name}} HẾT HẠN sau 7 ngày.</p>"
        ),
        "body_text": None,
    },
    {
        "code": "probation_end_14d",
        "event_type": "probation_end",
        "name": "Thử việc kết thúc (14 ngày)",
        "days_before": 14,
        "recipient_type": "hr",
        "subject": "[HRMS] Thử việc {{employee_name}} kết thúc sau 14 ngày",
        "merge_fields": json.dumps(
            ["employee_name", "probation_end_date", "days_until", "department", "company_name"]
        ),
        "body_html": (
            "<p>Thời gian thử việc của <strong>{{employee_name}}</strong> sẽ kết thúc ngày "
            "<strong>{{probation_end_date}}</strong>.</p>"
        ),
        "body_text": None,
    },
    {
        "code": "probation_end_7d",
        "event_type": "probation_end",
        "name": "Thử việc kết thúc (7 ngày)",
        "days_before": 7,
        "recipient_type": "hr",
        "subject": "[HRMS] Thử việc {{employee_name}} kết thúc sau 7 ngày",
        "merge_fields": json.dumps(
            ["employee_name", "probation_end_date", "days_until", "company_name"]
        ),
        "body_html": (
            "<p>Thử việc của {{employee_name}} kết thúc ngày {{probation_end_date}}.</p>"
        ),
        "body_text": None,
    },
    {
        "code": "probation_end_3d",
        "event_type": "probation_end",
        "name": "Thử việc kết thúc (3 ngày)",
        "days_before": 3,
        "recipient_type": "hr",
        "subject": "[HRMS] Khẩn: Thử việc {{employee_name}} kết thúc sau 3 ngày",
        "merge_fields": json.dumps(
            ["employee_name", "probation_end_date", "days_until", "company_name"]
        ),
        "body_html": (
            "<p>Thử việc của <strong>{{employee_name}}</strong> kết thúc ngày <strong>{{probation_end_date}}</strong>. "
            "Còn {{days_until}} ngày.</p>"
        ),
        "body_text": None,
    },
    {
        "code": "birthday",
        "event_type": "birthday",
        "name": "Sinh nhật nhân viên",
        "days_before": None,
        "recipient_type": "hr",
        "subject": "[HRMS] Sinh nhật hôm nay: {{employee_name}}",
        "merge_fields": json.dumps(["employee_name", "birth_date", "age", "company_name"]),
        "body_html": (
            "<p>Hôm nay là sinh nhật của <strong>{{employee_name}}</strong> ({{birth_date}}). "
            "Chúc mừng sinh nhật!</p>"
        ),
        "body_text": None,
    },
    {
        "code": "carryover_expiry",
        "event_type": "carryover_expiry",
        "name": "Tồn phép sắp hết hạn (30 ngày)",
        "days_before": 30,
        "recipient_type": "hr",
        "subject": "[HRMS] Tồn phép {{employee_name}} sắp hết hạn",
        "merge_fields": json.dumps(
            ["employee_name", "remaining_days", "expiry_date", "days_until", "company_name"]
        ),
        "body_html": (
            "<p>Nhân viên <strong>{{employee_name}}</strong> còn <strong>{{remaining_days}} ngày phép</strong> "
            "tồn sẽ hết hạn ngày {{expiry_date}}.</p>"
        ),
        "body_text": None,
    },
]

_CONFIGS = [
    {"event_type": "contract_expiry", "is_enabled": True, "days_before": [30, 15, 7]},
    {"event_type": "probation_end", "is_enabled": True, "days_before": [14, 7, 3]},
    {"event_type": "birthday", "is_enabled": True, "days_before": None},
    {"event_type": "carryover_expiry", "is_enabled": True, "days_before": [30]},
]


async def seed_notification_templates(session: AsyncSession) -> None:
    """Upsert templates và configs. Idempotent — an toàn khi gọi nhiều lần."""
    for t in _TEMPLATES:
        await session.execute(
            text("""
                INSERT INTO notification_templates
                    (code, event_type, name, subject, body_html, body_text,
                     merge_fields, is_active, is_system, days_before, recipient_type,
                     created_at, updated_at)
                VALUES
                    (:code, :event_type, :name, :subject, :body_html, :body_text,
                     CAST(:merge_fields AS jsonb), true, true, :days_before, :recipient_type,
                     now(), now())
                ON CONFLICT (code) DO UPDATE SET
                    event_type     = EXCLUDED.event_type,
                    name           = EXCLUDED.name,
                    subject        = EXCLUDED.subject,
                    body_html      = EXCLUDED.body_html,
                    merge_fields   = EXCLUDED.merge_fields,
                    days_before    = EXCLUDED.days_before,
                    recipient_type = EXCLUDED.recipient_type,
                    updated_at     = now()
            """),
            {
                "code": t["code"],
                "event_type": t["event_type"],
                "name": t["name"],
                "subject": t["subject"],
                "body_html": t["body_html"],
                "body_text": t["body_text"],
                "merge_fields": t["merge_fields"],
                "days_before": t["days_before"],
                "recipient_type": t["recipient_type"],
            },
        )

    for c in _CONFIGS:
        days = c["days_before"]
        # asyncpg requires a Python list for array columns; None stays None
        await session.execute(
            text("""
                INSERT INTO notification_config
                    (event_type, is_enabled, days_before, updated_at)
                VALUES
                    (:event_type, :is_enabled, :days_before, now())
                ON CONFLICT (event_type) DO UPDATE SET
                    is_enabled  = EXCLUDED.is_enabled,
                    days_before = EXCLUDED.days_before,
                    updated_at  = now()
            """),
            {
                "event_type": c["event_type"],
                "is_enabled": c["is_enabled"],
                "days_before": days,
            },
        )

    await session.commit()
