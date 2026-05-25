# Kế hoạch triển khai — 13.7. Giao tiếp với ứng viên

**Phạm vi:** Email template · Gửi email tự động/thủ công · Nhật ký giao tiếp  
**Phụ thuộc:** `13.3 Candidates + Applications` · `13.4 Pipeline` · `13.5 Offers` · `reminder_service` ✅ · SMTP ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §13.7

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| SMTP / email service | ✅ Hoàn thành | Tái dụng infrastructure hiện có |
| `reminder_service` | ✅ Hoàn thành | Tái dụng gửi email nội bộ |
| `recruitment_email_templates` | ❌ Chưa có | |
| `candidate_communications` | ❌ Chưa có | |
| API + Frontend | ❌ Chưa có | |

---

## Phạm vi

**Trong phạm vi:**
- Thư viện email template tuyển dụng (thêm/sửa/xóa template)
- Merge fields động: tên ứng viên, vị trí, phòng ban, ngày giờ PV, địa điểm, HR contact
- Gửi email tự động khi pipeline stage thay đổi (trigger)
- Gửi email thủ công từ hồ sơ ứng viên
- Nhật ký giao tiếp: lưu toàn bộ email gửi đi, trạng thái gửi
- Preview email trước khi gửi (render merge fields)

**Ngoài phạm vi:**
- Email marketing / nurturing campaign
- Inbox nhận email phản hồi từ ứng viên
- SMS / Zalo / WhatsApp
- Ký nhận xác nhận lịch phỏng vấn online (ứng viên tự confirm)

---

## Data Model

### Bảng `recruitment_email_templates`

```sql
CREATE TABLE recruitment_email_templates (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,
    name            VARCHAR(300) NOT NULL,      -- "Mời phỏng vấn vòng 1"
    trigger_event   VARCHAR(50),
    -- Giá trị NULL = chỉ gửi thủ công
    -- stage_moved:screening | stage_moved:interview | stage_moved:offer
    -- | offer_sent | offer_accepted | offer_rejected | hired | rejected

    subject         TEXT NOT NULL,              -- Hỗ trợ merge fields {{tên_ứng_viên}} v.v.
    body_html       TEXT NOT NULL,              -- HTML body
    body_text       TEXT,                       -- Plain-text fallback

    -- Merge fields được dùng trong template (tự động detect)
    merge_fields    TEXT[],                     -- ["ten_ung_vien", "vi_tri", "ngay_phong_van"]

    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_system       BOOLEAN NOT NULL DEFAULT FALSE,  -- template hệ thống, không xóa được
    created_by_id   INTEGER REFERENCES users(id),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
```

Seed template mặc định:

| code | name | trigger_event |
|---|---|---|
| invite_screening | Mời tham gia sàng lọc | stage_moved:screening |
| invite_interview | Mời phỏng vấn | stage_moved:interview |
| offer_sent | Thông báo gửi Offer | offer_sent |
| offer_accepted_confirm | Xác nhận chấp nhận offer | offer_accepted |
| rejection_early | Thông báo không phù hợp (sớm) | stage_moved:rejected |
| rejection_after_interview | Cảm ơn sau phỏng vấn | rejected |
| hired_welcome | Chào mừng nhân viên mới | hired |

### Bảng `candidate_communications`

```sql
CREATE TABLE candidate_communications (
    id                  SERIAL PRIMARY KEY,
    candidate_id        INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    application_id      INTEGER REFERENCES candidate_applications(id),

    -- Loại giao tiếp
    channel             VARCHAR(20) NOT NULL DEFAULT 'email',  -- email | note
    direction           VARCHAR(10) NOT NULL DEFAULT 'outbound',  -- outbound | inbound | internal

    -- Nội dung
    template_id         INTEGER REFERENCES recruitment_email_templates(id),
    subject             TEXT,
    body_html           TEXT,
    body_text           TEXT,

    -- Trạng thái gửi
    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending | sent | failed | bounced

    sent_at             TIMESTAMP,
    error_message       TEXT,           -- lỗi nếu gửi thất bại

    -- Metadata
    trigger_event       VARCHAR(100),   -- event đã trigger gửi (tự động hay thủ công)
    merge_context       JSONB,          -- snapshot context đã dùng để render

    sent_by_id          INTEGER REFERENCES users(id),   -- NULL nếu auto-send
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_comm_candidate ON candidate_communications(candidate_id);
CREATE INDEX ix_comm_application ON candidate_communications(application_id);
CREATE INDEX ix_comm_status ON candidate_communications(status);
CREATE INDEX ix_comm_sent_at ON candidate_communications(sent_at);
```

### Alembic migration

File: `0039_add_candidate_communications.py`

---

## Merge Fields

Danh sách merge fields hỗ trợ và nguồn dữ liệu:

| Field | Mô tả | Nguồn |
|---|---|---|
| `{{ten_ung_vien}}` | Họ tên đầy đủ | `candidates.full_name` |
| `{{ho_ung_vien}}` | Họ | Tách từ `full_name` |
| `{{vi_tri}}` | Tên vị trí tuyển dụng | `job_positions.name` |
| `{{phong_ban}}` | Tên phòng ban | `departments.name` |
| `{{ten_cong_ty}}` | Tên công ty | system config |
| `{{ngay_phong_van}}` | Ngày phỏng vấn | `interview_sessions.scheduled_at` (date) |
| `{{gio_phong_van}}` | Giờ phỏng vấn | `interview_sessions.scheduled_at` (time) |
| `{{dia_diem_phong_van}}` | Địa điểm / link meeting | `interview_sessions.location` |
| `{{ten_hr}}` | Tên người phụ trách HR | `users.full_name` (sender) |
| `{{email_hr}}` | Email HR | `users.email` |
| `{{sdt_hr}}` | SĐT HR | `users.phone` |
| `{{ngay_bat_dau}}` | Ngày bắt đầu làm việc | `hiring_decisions.start_date` |
| `{{luong_thu_viec}}` | Lương thử việc | `offers.probation_salary` (formatted) |
| `{{thoi_gian_thu_viec}}` | Thời gian thử việc | `offers.probation_days` ngày |
| `{{han_phan_hoi_offer}}` | Hạn phản hồi offer | `offers.expires_at` |

---

## API Design

### Email Templates

```
GET    /recruitment/email-templates               -- danh sách template
POST   /recruitment/email-templates              -- tạo template mới
GET    /recruitment/email-templates/{id}
PUT    /recruitment/email-templates/{id}         -- không được sửa is_system=True từ UI
DELETE /recruitment/email-templates/{id}         -- chỉ template không phải is_system

POST   /recruitment/email-templates/{id}/preview  -- render preview với context mẫu
```

### Giao tiếp ứng viên

```
GET    /recruitment/candidates/{id}/communications          -- lịch sử giao tiếp
POST   /recruitment/candidates/{id}/communications/send    -- gửi email thủ công
       body: { template_id, application_id?, custom_subject?, custom_body? }

GET    /recruitment/applications/{app_id}/communications   -- lịch sử theo application
```

### Permissions

| Action | Permission |
|---|---|
| Xem lịch sử giao tiếp | `recruitment:view` |
| Gửi email thủ công | `recruitment:manage` |
| Quản lý template | `recruitment:manage` |

---

## Schemas

```python
class EmailTemplateCreate(BaseModel):
    code: str
    name: str
    trigger_event: Optional[str] = None
    subject: str
    body_html: str
    body_text: Optional[str] = None

class EmailTemplateRead(BaseModel):
    id: int
    code: str
    name: str
    trigger_event: Optional[str]
    subject: str
    body_html: str
    merge_fields: List[str]       -- auto-detect từ body_html
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

class EmailTemplatePreviewRequest(BaseModel):
    application_id: Optional[int] = None   -- để load context thực
    use_sample_data: bool = True            -- nếu không có application_id

class SendEmailRequest(BaseModel):
    template_id: int
    application_id: Optional[int] = None
    custom_subject: Optional[str] = None   -- ghi đè subject template
    custom_body: Optional[str] = None      -- ghi đè body (text tự do)
    extra_context: Optional[dict] = None   -- merge fields bổ sung

class CommunicationRead(BaseModel):
    id: int
    channel: str
    direction: str
    template_name: Optional[str]
    subject: Optional[str]
    status: str
    sent_at: Optional[datetime]
    sent_by_name: Optional[str]     -- NULL nếu auto-send
    trigger_event: Optional[str]
    created_at: datetime
```

---

## Service Logic

### `recruitment_email_service.py`

**`render_template(template_id, context: dict) → (subject: str, body_html: str)`**
- Load template từ DB
- Thay thế tất cả `{{field}}` bằng giá trị từ `context`
- Field không có trong context → giữ nguyên placeholder (hiển thị rõ lỗi thiếu data)

**`build_context(application_id?, candidate_id?, user_id) → dict`**
- Collect data từ: candidate, application, job_requisition, job_position, department, offer, interview_session, sender user
- Return dict đầy đủ merge fields
- Các field optional (interview location, offer dates) để None nếu không có

**`send_email(candidate_id, template_id, application_id?, user_id, custom_override?) → CommunicationRead`**
1. Build context từ application/candidate
2. Render template → subject + body
3. Gọi SMTP service gửi đến `candidate.personal_email`
4. Tạo `CandidateCommunication` record với status = sent/failed
5. Ghi `sent_by_id = user_id`

**`auto_send_on_stage_change(application_id, new_stage, triggered_by_user_id)`**
- Tìm template có `trigger_event = f"stage_moved:{new_stage}"`
- Nếu tìm được và `candidate.personal_email` không rỗng → gọi `send_email` với `sent_by_id = None` (auto)
- Lỗi gửi mail KHÔNG rollback pipeline transition — log error, tiếp tục

**`detect_merge_fields(body_html: str) → List[str]`**
- Regex tìm tất cả `{{field_name}}`
- Dùng khi save template để cập nhật `merge_fields[]`

**`preview_template(template_id, application_id?, use_sample_data) → (subject, body_html)`**
- Nếu `use_sample_data = True`: dùng context mẫu (tên, vị trí, ngày giờ giả)
- Nếu `application_id` có: dùng context thực từ DB

### Integration với pipeline_service

Trong `pipeline_service.move_stage()`:
```python
# Sau khi commit stage transition thành công
await auto_send_on_stage_change(application_id, new_stage, user_id)
```

Integration với `offer_service`:
```python
# Trong send_offer(): trigger event "offer_sent"
# Trong accept_offer(): trigger event "offer_accepted"
# Trong reject_offer(): trigger event "offer_rejected"
```

---

## Thiết kế Frontend

### Tab "Giao tiếp" trong `CandidateDetailView.vue`

**Timeline danh sách email đã gửi:**
- Mỗi item: icon email, subject, ngày giờ, người gửi (HR / Tự động), trạng thái badge
- Click item → expand xem body (HTML preview trong panel)

**Button "Gửi email"** → mở `SendEmailDialog.vue`

### `SendEmailDialog.vue`

- Select template (dropdown có tên + trigger_event label)
- Preview tab: render kết quả merge fields
- Option "Tùy chỉnh nội dung" → textarea override
- Button "Gửi ngay"

### `EmailTemplateListView.vue` (trang quản lý template)

Trong module Recruitment → tab "Cài đặt" → sub-tab "Email Templates":
- DataTable: code, name, trigger_event, is_active, is_system
- Button "Tạo template" → inline form / dialog
- Xem/sửa template: Rich text editor (Quill / TipTap)
- Badge "System" cho is_system = True (không xóa được)
- Button "Preview" → hiển thị render với data mẫu

---

## Cấu trúc file

```
backend/
  alembic/versions/0039_add_candidate_communications.py  (NEW)
  app/models/recruitment.py                               (EDIT: EmailTemplate, CandidateCommunication)
  app/schemas/recruitment.py                              (EDIT)
  app/services/recruitment_email_service.py              (NEW)
  app/api/v1/endpoints/recruitment.py                    (EDIT: email template + send endpoints)
  tests/test_recruitment_email.py                        (NEW)

frontend/
  src/services/recruitmentService.ts                     (EDIT: email template + send API)
  src/views/recruitment/components/CommunicationTab.vue (NEW — tab trong CandidateDetailView)
  src/views/recruitment/components/SendEmailDialog.vue  (NEW)
  src/views/recruitment/components/EmailTemplateListTab.vue (NEW)
  src/views/employees/CandidateDetailView.vue            (EDIT: thêm tab Giao tiếp)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend: Models + Migration + Seed templates

### Slice 2 — Backend: Template CRUD + Render engine
- `recruitment_email_service.py`: render_template, detect_merge_fields, build_context, preview
- Endpoints: CRUD template, preview

### Slice 3 — Backend: Send + Auto-trigger
- `send_email()`: gửi qua SMTP, ghi log
- `auto_send_on_stage_change()`: hook vào pipeline_service
- Hook vào offer_service

### Slice 4 — Backend: Tests

### Slice 5 — Frontend
- `CommunicationTab.vue` trong CandidateDetailView
- `SendEmailDialog.vue`
- `EmailTemplateListTab.vue`

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| Ứng viên không có email | Trung bình | Kiểm tra `candidate.personal_email` trước khi send; bỏ qua auto-send nếu thiếu, cảnh báo nếu thủ công |
| SMTP fail làm rollback pipeline | Cao | Email service fail ≠ rollback pipeline; log lỗi, status = failed trong communication log |
| Merge field sai (thiếu data) | Trung bình | Render giữ nguyên `{{field}}` nếu thiếu → HR thấy ngay khi preview |
| Spam / gửi trùng | Thấp | Check: cùng template + cùng application, trong vòng 1 giờ → warn trước khi gửi lại |
| Rich text editor XSS | Trung bình | Sanitize HTML body bằng `bleach` / `nh3` trước khi lưu và trước khi gửi |
