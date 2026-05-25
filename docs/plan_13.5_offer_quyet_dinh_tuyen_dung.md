# Kế hoạch triển khai — 13.5. Offer & Quyết định tuyển dụng

**Phạm vi:** Offer Letter · Theo dõi trạng thái offer · Quyết định tuyển dụng · Chuyển đổi ứng viên → nhân viên  
**Phụ thuộc:** `13.3 Candidates + Applications` · `13.4 Pipeline` · `employees` ✅ · `employee_job_records` ✅ · `employee_contracts` ✅ · `contract_templates` ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §13.5  
**Căn cứ pháp lý:** Điều 24, 26 BLLĐ 2019 (thời hạn & lương thử việc)

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `candidate_applications` | ❌ Xây ở 13.3 | `current_stage` sẽ chuyển → `offer` |
| `contract_templates` | ✅ Hoàn thành | Tái dụng cho Offer Letter |
| `contract_generate_service` | ✅ Hoàn thành | Tái dụng sinh file Word/PDF |
| `employees` | ✅ Hoàn thành | Đích chuyển đổi từ candidate |
| `employee_job_records` | ✅ Hoàn thành | Ghi `probation_start_date`, `probation_end_date` |
| `employee_contracts` | ✅ Hoàn thành | Lưu hợp đồng thử việc sau khi tuyển |
| `offers` | ❌ Chưa có | |
| `hiring_decisions` | ❌ Chưa có | |
| API + Frontend | ❌ Chưa có | |

---

## Phạm vi

**Trong phạm vi:**
- Tạo và gửi Offer Letter từ template (tái dụng `contract_generate_service`)
- Theo dõi trạng thái offer (sent/waiting/accepted/rejected/negotiating)
- Lưu lý do từ chối offer
- Tạo Quyết định tuyển dụng sau khi offer được chấp nhận
- Kiểm tra vi phạm pháp lý thời hạn thử việc và lương thử việc
- **Chuyển đổi ứng viên → nhân viên**: tạo `Employee`, `EmployeeJobRecord`, migrate học vấn/kinh nghiệm/kỹ năng

**Ngoài phạm vi:**
- Đàm phán lương online
- Ký điện tử (digital signature)
- Hợp đồng thử việc (→ Module 14 — tái dụng `employee_contracts`)

---

## Data Model

### Bảng `offers`

```sql
CREATE TABLE offers (
    id                  SERIAL PRIMARY KEY,
    application_id      INTEGER NOT NULL REFERENCES candidate_applications(id),
    candidate_id        INTEGER NOT NULL REFERENCES candidates(id),
    job_requisition_id  INTEGER NOT NULL REFERENCES job_requisitions(id),

    -- Nội dung offer
    job_position_id     INTEGER REFERENCES job_positions(id),
    department_id       INTEGER REFERENCES departments(id),
    proposed_start_date DATE NOT NULL,
    probation_salary    NUMERIC(15,2) NOT NULL,
    official_salary     NUMERIC(15,2) NOT NULL,    -- dùng để kiểm tra luật 85%
    probation_days      SMALLINT NOT NULL,          -- số ngày thử việc (luật: 6/30/60/180)
    benefits_note       TEXT,

    -- Offer Letter file (sinh từ template)
    offer_file_path     VARCHAR(500),
    offer_file_name     VARCHAR(300),

    -- Trạng thái
    status              VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- draft | sent | waiting | accepted | rejected | negotiating | expired

    sent_at             TIMESTAMP,
    responded_at        TIMESTAMP,
    expires_at          DATE,         -- hạn phản hồi offer

    rejection_reason    TEXT,         -- lý do ứng viên từ chối
    negotiation_note    TEXT,
    internal_note       TEXT,

    created_by_id       INTEGER NOT NULL REFERENCES users(id),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_offers_application ON offers(application_id);
CREATE INDEX ix_offers_status ON offers(status);
```

### Bảng `hiring_decisions`

```sql
CREATE TABLE hiring_decisions (
    id                  SERIAL PRIMARY KEY,
    offer_id            INTEGER NOT NULL REFERENCES offers(id),
    candidate_id        INTEGER NOT NULL REFERENCES candidates(id),
    job_requisition_id  INTEGER NOT NULL REFERENCES job_requisitions(id),

    -- Thông tin quyết định
    decision_number     VARCHAR(50),         -- số QĐ tuyển dụng
    signed_date         DATE NOT NULL,
    department_id       INTEGER NOT NULL REFERENCES departments(id),
    job_position_id     INTEGER NOT NULL REFERENCES job_positions(id),
    job_title_id        INTEGER REFERENCES job_titles(id),
    start_date          DATE NOT NULL,       -- ngày bắt đầu làm việc thực tế

    -- Thử việc (sao chép từ offer, HR có thể điều chỉnh)
    probation_salary    NUMERIC(15,2) NOT NULL,
    official_salary     NUMERIC(15,2) NOT NULL,
    probation_days      SMALLINT NOT NULL,

    -- File quyết định
    file_path           VARCHAR(500),
    file_name           VARCHAR(300),
    file_size           INTEGER,
    mime_type           VARCHAR(100),

    -- Liên kết với nhân viên sau khi tạo
    employee_id         INTEGER REFERENCES employees(id),   -- điền sau khi convert

    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending | converted | cancelled

    created_by_id       INTEGER NOT NULL REFERENCES users(id),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_hiring_decisions_offer ON hiring_decisions(offer_id);
CREATE INDEX ix_hiring_decisions_employee ON hiring_decisions(employee_id);
```

### Alembic migration

File: `0037_add_offers_hiring_decisions.py`

---

## Business Rules — Kiểm tra vi phạm pháp lý

### Thời hạn thử việc tối đa (Điều 24 BLLĐ 2019)

Logic trong `offer_service.validate_probation_days(job_title_level, probation_days)`:

```python
PROBATION_LIMITS = {
    "director": 180,        # Giám đốc, Tổng giám đốc (level 1)
    "manager": 60,          # Chức danh cần trình độ CĐ trở lên
    "specialist": 30,       # TC/CNKT/nhân viên chuyên môn
    "worker": 6,            # Các trường hợp còn lại
}
```

- `job_title.level` → xác định nhóm → kiểm tra `probation_days ≤ limit`
- Nếu vi phạm: raise `HTTPException(400)` với message cụ thể

### Lương thử việc tối thiểu 85% (Điều 26 BLLĐ 2019)

```python
if probation_salary < official_salary * Decimal("0.85"):
    raise ValidationError("Lương thử việc không được thấp hơn 85% lương chính thức")
```

---

## API Design

### Offers

```
GET    /recruitment/applications/{app_id}/offers     -- lịch sử offer cho application
POST   /recruitment/applications/{app_id}/offers     -- tạo offer
GET    /recruitment/offers/{id}
PUT    /recruitment/offers/{id}                      -- chỉ khi draft/negotiating

POST   /recruitment/offers/{id}/send                 -- draft → sent
POST   /recruitment/offers/{id}/accept               -- sent/waiting → accepted
POST   /recruitment/offers/{id}/reject               -- body: { rejection_reason }
POST   /recruitment/offers/{id}/negotiate            -- body: { negotiation_note }
POST   /recruitment/offers/{id}/generate-letter      -- sinh Offer Letter PDF từ template
GET    /recruitment/offers/{id}/download-letter      -- tải file Offer Letter
```

### Hiring Decision

```
POST   /recruitment/offers/{offer_id}/hiring-decision   -- tạo QĐ tuyển dụng
GET    /recruitment/hiring-decisions/{id}
PUT    /recruitment/hiring-decisions/{id}               -- chỉ khi pending
POST   /recruitment/hiring-decisions/{id}/convert       -- convert candidate → employee
GET    /recruitment/hiring-decisions/{id}/download      -- tải file QĐ
```

### Permissions

| Action | Permission |
|---|---|
| Xem offer | `recruitment:view` |
| Tạo / sửa offer | `recruitment:manage` |
| Tạo quyết định tuyển dụng | `recruitment:manage` |
| Convert sang nhân viên | `recruitment:manage` + `employees:create` |

---

## Schemas

```python
class OfferCreate(BaseModel):
    job_position_id: int
    department_id: int
    proposed_start_date: date
    probation_salary: Decimal
    official_salary: Decimal
    probation_days: int
    benefits_note: Optional[str] = None
    expires_at: Optional[date] = None
    internal_note: Optional[str] = None

class OfferRead(BaseModel):
    id: int
    application_id: int
    candidate_name: str
    job_position_name: str
    department_name: str
    proposed_start_date: date
    probation_salary: Decimal
    official_salary: Decimal
    probation_days: int
    probation_days_limit: int          # giới hạn pháp lý theo chức danh
    probation_salary_warning: bool     # True nếu < 85%
    probation_days_warning: bool       # True nếu > giới hạn
    benefits_note: Optional[str]
    status: str
    sent_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime

class HiringDecisionCreate(BaseModel):
    decision_number: Optional[str] = None
    signed_date: date
    department_id: int
    job_position_id: int
    job_title_id: Optional[int] = None
    start_date: date
    probation_salary: Decimal
    official_salary: Decimal
    probation_days: int

class ConvertToEmployeeResult(BaseModel):
    employee_id: int
    employee_code: str
    message: str
```

---

## Service Logic

### `offer_service.py`

**`create_offer(session, app_id, data, user_id) → OfferRead`**
- Validate: `application.current_stage` phải là `interview` (đã qua phỏng vấn)
- Gọi `validate_probation_days` và `validate_probation_salary` → trả warning trong response (không block)
- Tạo offer, `status = draft`

**`generate_offer_letter(session, offer_id, user_id) → bytes`**
- Tìm `contract_template` loại `offer_letter`
- Điền merge fields: tên ứng viên, vị trí, phòng ban, mức lương, ngày bắt đầu, thời gian thử việc
- Tái dụng `contract_generate_service.render_template(template, context)` → trả bytes
- Lưu file vào MinIO, ghi `offer.offer_file_path`

**`accept_offer(session, offer_id, user_id)`**
- `status → accepted`
- Cập nhật `application.current_stage → hired` (chờ quyết định chính thức)

**`reject_offer(session, offer_id, rejection_reason, user_id)`**
- `status → rejected`
- Cập nhật `application.current_stage → rejected`
- Trigger email thông báo trượt (→ 13.7)

### `hiring_decision_service.py`

**`create_decision(session, offer_id, data, user_id) → HiringDecisionRead`**
- Validate: offer `status = accepted`
- Kiểm tra pháp lý (probation_days, probation_salary) — block nếu vi phạm
- Tạo `hiring_decision`, `status = pending`

**`convert_to_employee(session, decision_id, user_id) → ConvertToEmployeeResult`**

Đây là hàm quan trọng nhất — thực hiện trong 1 transaction:

```
1. Lấy candidate từ hiring_decision
2. Tạo Employee:
   - full_name, date_of_birth, gender, nationality, id_number, phone, personal_email
   - status = 'probation'
   - Sinh employee_code (tái dụng employee_code_service)
3. Tạo EmployeeJobRecord:
   - department_id, job_position_id, job_title_id
   - probation_start_date = decision.start_date
   - probation_end_date = start_date + probation_days
   - is_current = True
4. Migrate dữ liệu phụ từ candidate:
   - candidate_educations → employee_education_histories
   - candidate_work_experiences → employee_work_experiences
   - candidate_skills → employee_skills (nếu skill tồn tại trong catalog)
5. Cập nhật hiring_decision:
   - employee_id = new_employee.id
   - status = 'converted'
6. Cập nhật job_requisition:
   - Giảm quantity_remaining -= 1
   - Nếu quantity_remaining = 0: status → completed
7. Ghi AuditLog
```

---

## Thiết kế Frontend

### `OfferListTab.vue` (trong `RecruitmentView.vue`)

**DataTable:**

| Cột | Nội dung |
|---|---|
| Ứng viên | Link → ApplicationDetailView |
| Vị trí | |
| Phòng ban | |
| Lương TV | Cảnh báo 🔴 nếu < 85% |
| Thời gian TV | Cảnh báo 🔴 nếu vượt giới hạn |
| Ngày bắt đầu | |
| Trạng thái | Tag màu |
| Hành động | |

### `OfferFormDialog.vue`

- Auto-fill từ JR: vị trí, phòng ban
- Input lương thử việc + lương chính thức
- **Real-time warning**: tính `probation_salary / official_salary` → hiển thị cảnh báo ngay khi nhập
- Input ngày thử việc + **real-time warning** so với giới hạn pháp lý theo job_title
- DatePicker ngày bắt đầu + hạn phản hồi offer

### `HiringDecisionDialog.vue`

- Confirm lại thông tin: vị trí, phòng ban, lương, ngày bắt đầu
- Input số quyết định
- DatePicker ngày ký
- Upload file QĐ scan (optional)
- Button "Xác nhận & Tạo hồ sơ nhân viên" → gọi `convert_to_employee`

### Sau convert

- Toast: "Đã tạo nhân viên [Tên] — Mã [CODE]"
- Link điều hướng sang hồ sơ nhân viên mới trong module Employee

---

## Cấu trúc file

```
backend/
  alembic/versions/0037_add_offers_hiring_decisions.py   (NEW)
  app/models/recruitment.py                               (EDIT: Offer, HiringDecision)
  app/schemas/recruitment.py                              (EDIT: offer + decision schemas)
  app/services/offer_service.py                          (NEW)
  app/services/hiring_decision_service.py                (NEW)
  app/api/v1/endpoints/recruitment.py                    (EDIT)
  tests/test_recruitment_offer.py                        (NEW)

frontend/
  src/services/recruitmentService.ts                     (EDIT)
  src/views/recruitment/components/OfferListTab.vue      (NEW)
  src/views/recruitment/components/OfferFormDialog.vue   (NEW)
  src/views/recruitment/components/HiringDecisionDialog.vue (NEW)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend: Models + Migration

### Slice 2 — Backend: Offer CRUD + Workflow
- `offer_service.py`: create, send, accept, reject, negotiate
- Validate probation rules
- `generate_offer_letter`: tái dụng contract_generate_service

### Slice 3 — Backend: Hiring Decision + Convert
- `hiring_decision_service.py`
- `convert_to_employee` trong transaction

### Slice 4 — Backend: Tests
- Kiểm tra probation validation (boundary: 60/30/6 ngày, 85% lương)
- Kiểm tra convert tạo đủ records

### Slice 5 — Frontend

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| Convert thất bại giữa chừng (partial) | Cao | Toàn bộ trong 1 DB transaction; rollback nếu lỗi |
| Template Offer Letter chưa có | Trung bình | Tạo template mặc định khi seed; generate trả 400 nếu template không tồn tại |
| Ứng viên convert → Employee bị trùng email | Thấp | Kiểm tra `employees.personal_email` trước khi tạo; cảnh báo nếu trùng |
| JR quantity tính sai khi convert song song | Thấp | `SELECT ... FOR UPDATE` trên job_requisition khi giảm quantity |
| Migrate skill candidate → employee_skills: skill không có trong catalog | Thấp | Bỏ qua skill không tìm được trong catalog; ghi vào `internal_note` của employee |
