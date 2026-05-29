# Kế hoạch triển khai — 12.3. Thông báo & Nhắc việc tự động

**Phạm vi:** Email tự động · Mẫu email · Log gửi email  
**Phụ thuộc:** 3.6 Reminders ✅ · Celery + Redis ✅ · SMTP config ✅ · 13.7 Email tuyển dụng (pattern) ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §12.3  
**Đặc điểm:** Infrastructure email (SMTP + smtplib) và reminder_service.py đã có; plan này xây phần automation

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| SMTP config (host, port, user, pass) | ✅ Có | `settings.SMTP_HOST/PORT/USERNAME/PASSWORD` |
| `smtplib` send_email function | ✅ Có | Pattern từ `recruitment_email_service.py` |
| `reminder_service.py` — collect events | ✅ Có | birthday, anniversary, probation_end, contract_expiry |
| Celery beat schedule | ✅ Có | 4 tasks định kỳ, dễ mở rộng |
| Email template HTML | ❌ Chưa có | Chỉ có cho tuyển dụng |
| Gửi email tự động cho reminders | ❌ Chưa có | |
| Model `notification_templates` | ❌ Chưa có | |
| Model `email_logs` | ❌ Chưa có | |
| Celery task `send_daily_reminders` | ❌ Chưa có | |
| Config UI (bật/tắt, sửa template) | ❌ Chưa có | |

---

## Phạm vi 12.3

### Trong phạm vi

1. **6 loại email tự động:**
   - Hợp đồng sắp hết hạn (30 ngày trước → 15 ngày → 7 ngày)
   - Thử việc sắp kết thúc (14 ngày trước → 7 ngày → 3 ngày)
   - Sinh nhật nhân viên (gửi vào ngày sinh nhật)
   - Chứng chỉ sắp hết hạn (60 ngày → 30 ngày)
   - Đánh giá KPI sắp đến hạn (7 ngày trước deadline)
   - Tồn phép sắp hết hạn carryover (30 ngày trước)
2. **Mẫu email (template)** — có thể chỉnh sửa qua UI, merge fields `{{employee_name}}` etc.
3. **Log lịch sử gửi email** — ai nhận, loại email, trạng thái, thời gian
4. **Celery beat task** — chạy mỗi ngày lúc 08:00, collect reminders, gửi email cho HR Manager và/hoặc nhân viên liên quan
5. **Cấu hình per event type** — bật/tắt, ngưỡng ngày, danh sách nhận email

### Ngoài phạm vi

- In-app notification (notification bell trong UI) — sẽ làm riêng sau
- SMS notification
- Push notification (mobile)
- Webhook cho hệ thống bên ngoài
- Email marketing / newsletter

---

## Database Migration

### Bảng `notification_templates`

```sql
CREATE TABLE notification_templates (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(100) NOT NULL UNIQUE,  -- 'contract_expiry_30d', 'birthday', ...
    event_type      VARCHAR(50)  NOT NULL,          -- 'contract_expiry', 'birthday', etc.
    name            VARCHAR(255) NOT NULL,          -- "Hợp đồng sắp hết hạn (30 ngày)"
    subject         VARCHAR(500) NOT NULL,
    body_html       TEXT         NOT NULL,
    body_text       TEXT,
    merge_fields    JSONB        NOT NULL DEFAULT '[]',  -- ["employee_name", "contract_number", ...]
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    is_system       BOOLEAN      NOT NULL DEFAULT true,  -- system templates không xóa được
    days_before     INTEGER,                        -- ngưỡng ngày (null = không áp dụng)
    recipient_type  VARCHAR(50)  NOT NULL DEFAULT 'hr', -- 'hr' | 'employee' | 'both'
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_notif_templates_event_type ON notification_templates(event_type);
CREATE INDEX ix_notif_templates_is_active ON notification_templates(is_active);
```

### Bảng `email_logs`

```sql
CREATE TABLE email_logs (
    id              BIGSERIAL PRIMARY KEY,
    template_code   VARCHAR(100),                  -- FK mềm → notification_templates.code
    event_type      VARCHAR(50)  NOT NULL,
    employee_id     INTEGER      REFERENCES employees(id) ON DELETE SET NULL,
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name  VARCHAR(255),
    subject         VARCHAR(500),
    status          VARCHAR(20)  NOT NULL,          -- 'sent' | 'failed' | 'skipped'
    error_message   TEXT,
    sent_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    celery_task_id  VARCHAR(255)
);

CREATE INDEX ix_email_logs_event_type ON email_logs(event_type);
CREATE INDEX ix_email_logs_employee_id ON email_logs(employee_id);
CREATE INDEX ix_email_logs_sent_at ON email_logs(sent_at DESC);
CREATE INDEX ix_email_logs_status ON email_logs(status);
```

### Bảng `notification_config`

```sql
CREATE TABLE notification_config (
    id              SERIAL PRIMARY KEY,
    event_type      VARCHAR(50)  NOT NULL UNIQUE,
    is_enabled      BOOLEAN      NOT NULL DEFAULT true,
    days_before     INTEGER[],                      -- [30, 15, 7] ngày cảnh báo
    extra_recipients TEXT[],                        -- Email CC thêm (ngoài HR)
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

---

## Merge Fields — Danh sách per event type

| Event type | Merge fields |
|---|---|
| `contract_expiry` | `{{employee_name}}`, `{{employee_code}}`, `{{contract_number}}`, `{{expiry_date}}`, `{{days_until}}`, `{{department}}` |
| `probation_end` | `{{employee_name}}`, `{{employee_code}}`, `{{probation_end_date}}`, `{{days_until}}`, `{{department}}` |
| `birthday` | `{{employee_name}}`, `{{employee_code}}`, `{{birth_date}}`, `{{age}}`, `{{department}}` |
| `certificate_expiry` | `{{employee_name}}`, `{{certificate_name}}`, `{{expiry_date}}`, `{{days_until}}` |
| `kpi_deadline` | `{{employee_name}}`, `{{period}}`, `{{deadline}}`, `{{days_until}}` |
| `carryover_expiry` | `{{employee_name}}`, `{{leave_type}}`, `{{remaining_days}}`, `{{expiry_date}}`, `{{days_until}}` |

---

## Service Logic

### `notification_service.py` (file mới)

```python
"""Service gửi email thông báo tự động (12.3)."""

async def get_pending_notifications(
    session: AsyncSession,
    reference_date: date | None = None,
) -> list[NotificationTask]:
    """
    Collect tất cả sự kiện cần gửi email hôm nay:
    1. Contract expiry: effective_to IN (today+7, today+15, today+30)
    2. Probation end: probation_end_date IN (today+3, today+7, today+14)
    3. Birthday: birthday = today (month + day match)
    4. Certificate expiry: expires_at IN (today+30, today+60)
    5. Carryover expiry: carryover_expires IN (today+30)
    Return list NotificationTask với merge_data đã fill
    """

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
    """
    1. Load template từ DB (hoặc default nếu không có)
    2. Render body với merge_data (replace {{field}} → value)
    3. Gọi _send_email_smtp() (đồng bộ trong thread executor)
    4. Ghi EmailLog (status='sent'|'failed')
    Return True nếu gửi thành công
    """

async def get_hr_recipients(session: AsyncSession) -> list[str]:
    """Trả về email của tất cả User có role HR Manager hoặc Admin."""

def _render_template(body_html: str, merge_data: dict) -> str:
    """Replace {{field}} với giá trị trong merge_data."""
    for key, value in merge_data.items():
        body_html = body_html.replace(f"{{{{{key}}}}}", str(value or ""))
    return body_html
```

### Tái dùng `_send_email_smtp()` từ `recruitment_email_service.py`

Copy hàm gốc (không import trực tiếp để tránh circular dependency):

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

def _send_email_smtp(to_email: str, subject: str, body_html: str, body_text: str = "") -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM_EMAIL))
    msg["To"] = to_email
    if body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    with (smtplib.SMTP_SSL if settings.SMTP_USE_TLS else smtplib.SMTP)(
        settings.SMTP_HOST, settings.SMTP_PORT, timeout=10
    ) as server:
        if settings.SMTP_USE_STARTTLS:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
```

---

## Celery Task

### `backend/app/workers/tasks.py` — bổ sung task mới

```python
@celery_app.task(name="workers.send_daily_notifications")
def send_daily_notifications() -> None:
    """Gửi tất cả email nhắc việc hàng ngày lúc 08:00."""
    async def _run():
        async with _make_session()() as session:
            tasks = await notification_service.get_pending_notifications(session)
            hr_emails = await notification_service.get_hr_recipients(session)

            sent, failed, skipped = 0, 0, 0
            for task in tasks:
                # Kiểm tra đã gửi hôm nay chưa (tránh duplicate)
                if await _already_sent_today(session, task):
                    skipped += 1
                    continue

                recipients = hr_emails if task.recipient_type == "hr" else [task.employee_email]
                for email in recipients:
                    ok = await notification_service.send_notification_email(
                        template_code=task.template_code,
                        recipient_email=email,
                        recipient_name=task.recipient_name,
                        merge_data=task.merge_data,
                        session=session,
                        employee_id=task.employee_id,
                        celery_task_id=current_task.request.id,
                    )
                    (sent if ok else failed).__iadd__(1)

    asyncio.run(_run())
```

### Beat schedule — thêm vào `celery_app.py`

```python
beat_schedule = {
    # ... existing tasks ...
    "send-daily-notifications": {
        "task": "workers.send_daily_notifications",
        "schedule": crontab(hour=8, minute=0),     # 08:00 mỗi ngày
        "options": {"queue": "default"},
    },
}
```

### Chống duplicate gửi email

Trước khi gửi, kiểm tra `email_logs`:

```python
async def _already_sent_today(session, task: NotificationTask) -> bool:
    today = date.today()
    result = await session.execute(
        select(EmailLog)
        .where(
            EmailLog.template_code == task.template_code,
            EmailLog.employee_id == task.employee_id,
            func.date(EmailLog.sent_at) == today,
            EmailLog.status == "sent",
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
```

---

## Seed Templates mặc định

```python
# backend/app/seeds/notification_templates.py

SYSTEM_TEMPLATES = [
    {
        "code": "contract_expiry_30d",
        "event_type": "contract_expiry",
        "name": "Hợp đồng sắp hết hạn (30 ngày)",
        "days_before": 30,
        "recipient_type": "hr",
        "subject": "[HRMS] Hợp đồng {{employee_name}} sắp hết hạn",
        "body_html": """
<p>Kính gửi Phòng Nhân sự,</p>
<p>Hợp đồng lao động của <strong>{{employee_name}}</strong> ({{employee_code}})
sẽ hết hạn sau <strong>{{days_until}} ngày</strong> ({{expiry_date}}).</p>
<p>Số hợp đồng: <strong>{{contract_number}}</strong><br>
Phòng ban: {{department}}</p>
<p>Vui lòng xem xét gia hạn hoặc chấm dứt hợp đồng trước ngày hết hạn.</p>
<p>Trân trọng,<br>Hệ thống HRMS {{company_name}}</p>
""",
    },
    # ... thêm cho các event types khác
]
```

---

## API Endpoints mới

### Prefix `/api/v1/notifications`

```
GET  /notifications/templates                  → Danh sách tất cả templates
GET  /notifications/templates/{code}           → Chi tiết template
PUT  /notifications/templates/{code}           → Cập nhật template (subject, body_html)
POST /notifications/templates/{code}/preview   → Xem trước với data mẫu → trả HTML

GET  /notifications/config                     → Config per event type
PUT  /notifications/config/{event_type}        → Bật/tắt, sửa days_before, extra_recipients

GET  /notifications/logs                       → Lịch sử gửi (phân trang)
     ?event_type=...&status=...&from=...&to=...
POST /notifications/test-send                  → Gửi test email ngay (cho admin)
     Body: { template_code, recipient_email }
```

### Permissions

| Endpoint | Permission |
|---|---|
| Templates (đọc/sửa), Config, Logs | `notifications:manage` (role: HR Manager, Admin) |
| Test send | `notifications:manage` |

---

## Frontend Design

### Route mới

```
/settings/notifications   →   NotificationSettingsView.vue
```

### Layout

```
┌─ Cài đặt thông báo ──────────────────────────────────────────────┐
│  [Tab: Mẫu email] [Tab: Cấu hình sự kiện] [Tab: Lịch sử gửi]   │
├──────────────────────────────────────────────────────────────────┤
│ TAB: Mẫu email                                                   │
│                                                                  │
│ ┌─ Card: Hợp đồng sắp hết hạn (30 ngày) ──────────────────────┐ │
│ │ [● Đang bật]  Gửi cho: HR Manager                           │ │
│ │ Tiêu đề: [Hợp đồng {{employee_name}} sắp hết hạn...]       │ │
│ │ Nội dung: [Editor HTML...]                                   │ │
│ │ Merge fields: {{employee_name}} {{contract_number}} ...      │ │
│ │ [Xem trước]  [Gửi test email]  [Lưu]                        │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ TAB: Cấu hình sự kiện                                           │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ Sự kiện           │ Bật/tắt │ Ngưỡng ngày │ Email bổ sung │   │
│ ├───────────────────┼─────────┼─────────────┼───────────────┤   │
│ │ Hợp đồng hết hạn  │ [✓]     │ 30, 15, 7   │ hr@...        │   │
│ │ Thử việc kết thúc │ [✓]     │ 14, 7, 3    │               │   │
│ │ Sinh nhật NV      │ [  ]    │ —           │               │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│ TAB: Lịch sử gửi                                                │
│ [Filter: sự kiện, trạng thái, từ ngày, đến ngày]               │
│ DataTable: NV | Loại email | Người nhận | Trạng thái | Thời gian│
└──────────────────────────────────────────────────────────────────┘
```

**PrimeVue components:** `TabView`, `Editor` (rich text), `ToggleButton`, `DataTable`, `Tag`

### Service `notificationService.ts` (file mới)

```typescript
const BASE = '/notifications'

export default {
  getTemplates: () => api.get<NotifTemplate[]>(`${BASE}/templates`),
  getTemplate: (code: string) => api.get<NotifTemplate>(`${BASE}/templates/${code}`),
  updateTemplate: (code: string, data: UpdateTemplateDto) =>
    api.put<NotifTemplate>(`${BASE}/templates/${code}`, data),
  previewTemplate: (code: string, sampleData: Record<string, string>) =>
    api.post<{ html: string }>(`${BASE}/templates/${code}/preview`, { sample_data: sampleData }),
  testSend: (templateCode: string, recipientEmail: string) =>
    api.post(`${BASE}/test-send`, { template_code: templateCode, recipient_email: recipientEmail }),
  getConfig: () => api.get<NotifConfig[]>(`${BASE}/config`),
  updateConfig: (eventType: string, data: UpdateConfigDto) =>
    api.put<NotifConfig>(`${BASE}/config/${eventType}`, data),
  getLogs: (params: LogParams) => api.get<LogsResponse>(`${BASE}/logs`, { params }),
}
```

---

## Cấu trúc file

```
backend/
├── app/schemas/
│   └── notification.py                     ← NEW — schemas Pydantic
├── app/services/
│   └── notification_service.py             ← NEW — collect + send + log
├── app/models/
│   └── notification.py                     ← NEW — NotificationTemplate, EmailLog, NotifConfig
├── app/api/v1/endpoints/
│   └── notifications.py                    ← NEW — 8 endpoints
├── app/workers/tasks.py                    ← UPDATE — thêm send_daily_notifications
├── app/core/celery_app.py                  ← UPDATE — thêm beat schedule 08:00
├── app/seeds/
│   └── notification_templates.py           ← NEW — 6 system templates
└── alembic/versions/
    └── xxxx_add_notification_tables.py     ← NEW

frontend/src/
├── services/
│   └── notificationService.ts              ← NEW
├── views/settings/
│   └── NotificationSettingsView.vue        ← NEW
└── router/index.ts                         ← UPDATE
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend Models + Templates + Email Service

**Việc cần làm:**
1. Tạo migration `xxxx_add_notification_tables.py` — 3 bảng
2. Tạo models `notification.py`
3. Tạo `notification_service.py`:
   - `get_pending_notifications()` — 6 event types
   - `send_notification_email()` — render template + gửi SMTP + log
   - `get_hr_recipients()` — lấy email HR từ DB
   - `_render_template()` — merge fields
   - `_already_sent_today()` — chống duplicate
4. Seed `notification_templates.py` — 6 template mặc định
5. Tạo `app/api/v1/endpoints/notifications.py` — template CRUD + preview
6. Tests:
   - `test_render_template_replaces_fields` — unit test
   - `test_pending_notifications_contract_expiry` — seed contract sắp hết hạn → có trong list
   - `test_already_sent_dedup` — log sent hôm nay → skip
   - `test_templates_crud` — CRUD endpoints
   - `test_preview_returns_html` — preview endpoint

**Verify:** `pytest tests/test_notifications.py -v` pass.

---

### Slice 2 — Celery Task + Config + Logs

**Việc cần làm:**
1. Thêm `send_daily_notifications` task vào `workers/tasks.py`
2. Thêm beat schedule `08:00` vào `celery_app.py`
3. Bổ sung config endpoints: `GET/PUT /notifications/config`
4. Bổ sung logs endpoint: `GET /notifications/logs` (phân trang)
5. Bổ sung `POST /notifications/test-send`
6. Tests:
   - `test_send_daily_task_calls_service` — mock notification_service, verify called
   - `test_config_toggle_enable_disable`
   - `test_logs_pagination`
   - `test_test_send_endpoint`

**Verify:** Chạy task thủ công `celery -A app.core.celery_app call workers.send_daily_notifications` → email log được ghi.

---

### Slice 3 — Frontend Config UI

**Việc cần làm:**
1. Tạo `notificationService.ts`
2. Tạo `NotificationSettingsView.vue`:
   - Tab 1: Danh sách templates, mỗi card có editor + preview + test send
   - Tab 2: Config table (toggle, days_before editable)
   - Tab 3: Log DataTable với filter
3. Cập nhật router + AppMenu (Settings menu)
4. `vue-tsc --noEmit` clean

**Verify:** Sửa template → xem preview đúng merge fields → gửi test email.

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| SMTP không cấu hình (dev env) | Check `SMTP_HOST != 'localhost'` trước khi gửi; nếu chưa cấu hình → log warning, không fail task |
| Email HR không có trong DB | `get_hr_recipients()` trả [] → không gửi, log warning |
| Celery worker bị tắt → task không chạy | Alert: beat schedule vẫn ghi task vào Redis; monitor queue length |
| Gửi spam do bug (nhiều event cùng ngày) | `_already_sent_today()` kiểm tra per (template_code, employee_id, date) |
| Template HTML có XSS | Render template chỉ trên backend; không eval dynamic code |
| `contract_expiry` và `probation_end` có nhiều mốc (7/15/30 ngày) | Mỗi mốc là một template_code riêng (contract_expiry_30d, _15d, _7d) |

---

## Checklist

### Backend
- [ ] Migration 3 bảng chạy `alembic upgrade head` không lỗi
- [ ] Seed 6 system templates chạy thành công
- [ ] `pytest tests/test_notifications.py` pass
- [ ] Celery beat task `send_daily_notifications` đăng ký đúng
- [ ] `_already_sent_today()` ngăn duplicate trong cùng ngày

### Frontend
- [ ] `vue-tsc --noEmit` clean
- [ ] Editor hiển thị HTML preview đúng merge fields
- [ ] Gửi test email → nhận được email thực
- [ ] Log hiển thị đúng sent/failed status
