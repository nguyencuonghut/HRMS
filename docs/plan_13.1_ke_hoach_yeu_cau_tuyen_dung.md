# Kế hoạch triển khai — 13.1. Kế hoạch & Yêu cầu tuyển dụng

**Phạm vi:** Headcount Planning · Job Requisition (JR) · Phê duyệt JR · Ngân sách tuyển dụng  
**Phụ thuộc:** `departments` ✅ · `job_positions` ✅ · `job_titles` ✅ · `users` ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §13.1  
**Lưu ý:** Đây là module nền tảng của toàn bộ ATS — 13.2 → 13.8 đều phụ thuộc vào JR

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `departments` | ✅ Hoàn thành | Tham chiếu trực tiếp |
| `job_positions` | ✅ Hoàn thành | JR kế thừa JD từ đây |
| `job_titles` | ✅ Hoàn thành | Tham chiếu |
| `headcount_plans` | ❌ Chưa có | |
| `job_requisitions` | ❌ Chưa có | |
| `recruitment_budget_items` | ❌ Chưa có | |
| API + Frontend | ❌ Chưa có | |

---

## Phạm vi

**Trong phạm vi:**
- Lập kế hoạch nhân sự theo năm / phòng ban (tùy chọn — không bắt buộc khi tạo JR)
- CRUD Job Requisition: tạo, phê duyệt, theo dõi trạng thái
- JR kế thừa nội dung JD từ `JobPosition`, cho phép override
- Phê duyệt JR qua các bước theo phân quyền
- Ngân sách dự toán / thực tế cho từng JR

**Ngoài phạm vi:**
- Đăng tin (→ 13.2)
- Quản lý ứng viên (→ 13.3 → 13.5)
- Báo cáo tuyển dụng (→ 13.8)

---

## Data Model

### Bảng `headcount_plans`

```sql
CREATE TABLE headcount_plans (
    id              SERIAL PRIMARY KEY,
    year            SMALLINT NOT NULL,
    department_id   INTEGER REFERENCES departments(id),
    job_position_id INTEGER REFERENCES job_positions(id),
    current_count   SMALLINT NOT NULL DEFAULT 0,
    planned_count   SMALLINT NOT NULL DEFAULT 0,  -- nhu cầu bổ sung
    reason          TEXT,
    created_by_id   INTEGER REFERENCES users(id),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (year, department_id, job_position_id)
);
```

### Bảng `job_requisitions`

```sql
CREATE TABLE job_requisitions (
    id                  SERIAL PRIMARY KEY,
    code                VARCHAR(30) UNIQUE NOT NULL,  -- JR-2026-0001
    job_position_id     INTEGER NOT NULL REFERENCES job_positions(id),
    department_id       INTEGER NOT NULL REFERENCES departments(id),
    headcount_plan_id   INTEGER REFERENCES headcount_plans(id),  -- nullable

    quantity            SMALLINT NOT NULL DEFAULT 1,
    reason_type         VARCHAR(20) NOT NULL,  -- new | replacement | expansion
    deadline            DATE,
    salary_min          NUMERIC(15,2),
    salary_max          NUMERIC(15,2),

    -- JD override (null = dùng nguyên từ job_position)
    jd_description      TEXT,
    jd_requirements     TEXT,

    status              VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- draft | pending_review | approved | in_progress | completed | cancelled

    -- Phê duyệt
    submitted_by_id     INTEGER REFERENCES users(id),
    submitted_at        TIMESTAMP,
    approved_by_id      INTEGER REFERENCES users(id),
    approved_at         TIMESTAMP,
    rejection_note      TEXT,

    internal_note       TEXT,
    created_by_id       INTEGER NOT NULL REFERENCES users(id),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_jr_department ON job_requisitions(department_id);
CREATE INDEX ix_jr_status ON job_requisitions(status);
CREATE INDEX ix_jr_job_position ON job_requisitions(job_position_id);
```

### Bảng `recruitment_budget_items`

```sql
CREATE TABLE recruitment_budget_items (
    id                  SERIAL PRIMARY KEY,
    job_requisition_id  INTEGER NOT NULL REFERENCES job_requisitions(id) ON DELETE CASCADE,
    item_name           VARCHAR(200) NOT NULL,  -- "Phí đăng tin TopCV", "Headhunter",...
    estimated_amount    NUMERIC(15,2),
    actual_amount       NUMERIC(15,2),
    note                TEXT,
    created_by_id       INTEGER REFERENCES users(id),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### Alembic migration

File: `0033_add_recruitment_planning.py`

---

## API Design

### Headcount Plan

```
GET    /recruitment/headcount-plans?year=&department_id=&page=&page_size=
POST   /recruitment/headcount-plans
PUT    /recruitment/headcount-plans/{id}
DELETE /recruitment/headcount-plans/{id}
```

### Job Requisition

```
GET    /recruitment/job-requisitions?status=&department_id=&year=&page=&page_size=
POST   /recruitment/job-requisitions
GET    /recruitment/job-requisitions/{id}
PUT    /recruitment/job-requisitions/{id}
DELETE /recruitment/job-requisitions/{id}          -- chỉ khi status=draft

POST   /recruitment/job-requisitions/{id}/submit   -- draft → pending_review
POST   /recruitment/job-requisitions/{id}/approve  -- pending_review → approved
POST   /recruitment/job-requisitions/{id}/reject   -- pending_review → draft (kèm rejection_note)
POST   /recruitment/job-requisitions/{id}/cancel   -- hủy JR đang hoạt động
```

### Budget

```
GET    /recruitment/job-requisitions/{id}/budget
POST   /recruitment/job-requisitions/{id}/budget
PUT    /recruitment/job-requisitions/{id}/budget/{item_id}
DELETE /recruitment/job-requisitions/{id}/budget/{item_id}
```

### Permissions

| Action | Permission |
|---|---|
| Xem JR | `recruitment:view` |
| Tạo / sửa JR | `recruitment:manage` |
| Phê duyệt JR | `recruitment:approve` |

---

## Schemas (Pydantic)

```python
class HeadcountPlanCreate(BaseModel):
    year: int
    department_id: int
    job_position_id: int
    current_count: int = 0
    planned_count: int
    reason: Optional[str] = None

class HeadcountPlanRead(HeadcountPlanCreate):
    id: int
    department_name: Optional[str]
    job_position_name: Optional[str]
    created_at: datetime

class JobRequisitionCreate(BaseModel):
    job_position_id: int
    department_id: int
    headcount_plan_id: Optional[int] = None
    quantity: int = 1
    reason_type: str  # new | replacement | expansion
    deadline: Optional[date] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    jd_description: Optional[str] = None   # None = kế thừa từ JobPosition
    jd_requirements: Optional[str] = None
    internal_note: Optional[str] = None

class JobRequisitionRead(BaseModel):
    id: int
    code: str
    job_position_id: int
    job_position_name: str
    department_id: int
    department_name: str
    headcount_plan_id: Optional[int]
    quantity: int
    reason_type: str
    deadline: Optional[date]
    salary_min: Optional[Decimal]
    salary_max: Optional[Decimal]
    # JD: merged từ JobPosition nếu override = None
    effective_description: Optional[str]
    effective_requirements: Optional[str]
    status: str
    submitted_at: Optional[datetime]
    approved_by_name: Optional[str]
    approved_at: Optional[datetime]
    rejection_note: Optional[str]
    internal_note: Optional[str]
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime

class JobRequisitionListPage(BaseModel):
    items: List[JobRequisitionRead]
    total: int
    page: int
    page_size: int

class BudgetItemCreate(BaseModel):
    item_name: str
    estimated_amount: Optional[Decimal] = None
    actual_amount: Optional[Decimal] = None
    note: Optional[str] = None

class BudgetItemRead(BudgetItemCreate):
    id: int
    created_at: datetime
```

---

## Service Logic

### `jr_service.py`

**`generate_jr_code(session, year) → str`**
- Format: `JR-{year}-{seq:04d}` — sequence tăng dần theo năm, reset mỗi năm

**`create_jr(session, data, created_by_id) → JobRequisitionRead`**
- Validate `job_position_id` tồn tại
- Validate `department_id` tồn tại
- Nếu `headcount_plan_id` cung cấp: kiểm tra plan thuộc đúng department
- Sinh `code` tự động
- `effective_description`: nếu `jd_description` = None → lấy từ `job_position.description`
- `effective_requirements`: tương tự

**`submit_jr(session, jr_id, user_id)`**
- Chỉ được submit nếu `status = draft` và `created_by_id = user_id` (hoặc có quyền `recruitment:manage`)
- Chuyển `status → pending_review`, ghi `submitted_by_id`, `submitted_at`

**`approve_jr(session, jr_id, user_id)`**
- Kiểm tra permission `recruitment:approve`
- Chỉ được approve nếu `status = pending_review`
- Chuyển `status → approved`, ghi `approved_by_id`, `approved_at`

**`reject_jr(session, jr_id, user_id, rejection_note)`**
- `status → draft` (trả về nháp để chỉnh sửa lại)
- Ghi `rejection_note`

**`cancel_jr(session, jr_id, user_id)`**
- Chỉ cancel khi status ∈ {draft, pending_review, approved, in_progress}
- Nếu đang `in_progress` (có ứng viên): kiểm tra không còn ứng viên đang trong pipeline

### `headcount_plan_service.py`

**`get_fulfillment_rate(session, year, department_id?) → dict`**
- So sánh `planned_count` với số JR `completed` cùng năm/phòng ban

---

## Thiết kế Frontend

### Router

```
/recruitment                → RecruitmentView.vue (tabs)
  /recruitment/jr           → JRListTab.vue
  /recruitment/headcount    → HeadcountPlanTab.vue
```

### `RecruitmentView.vue`

Tab layout tương tự `PerformanceView.vue`:
- Tab "Yêu cầu tuyển dụng" (JR) — mặc định
- Tab "Kế hoạch nhân sự" — tùy chọn, có thể ẩn nếu công ty không dùng

### `JRListTab.vue`

**Toolbar:**
- Button "Tạo yêu cầu tuyển dụng" → mở `JRFormDialog.vue`
- Filter: Status (chip select), Phòng ban (Select), Năm (Select)

**DataTable:**

| Cột | Nội dung |
|---|---|
| Mã JR | `code` |
| Vị trí | `job_position_name` |
| Phòng ban | `department_name` |
| Số lượng | `quantity` |
| Hạn cần | `deadline` |
| Trạng thái | Tag màu theo status |
| Thao tác | Xem / Sửa / Submit / Approve / Cancel |

**Màu tag status:**
- `draft` → secondary
- `pending_review` → warn
- `approved` → info
- `in_progress` → primary
- `completed` → success
- `cancelled` → danger

### `JRFormDialog.vue`

- Select vị trí công việc → tự động điền JD từ `JobPosition` vào preview
- Checkbox "Tùy chỉnh JD cho đợt tuyển này" → mở textarea override
- Select phòng ban
- Chọn lý do tuyển: Vị trí mới / Thay thế / Mở rộng
- Liên kết kế hoạch nhân sự (optional Select, lọc theo phòng ban + năm)
- Mức lương dự kiến (min–max)
- Hạn cần người
- Ghi chú nội bộ

### `JRDetailView.vue`

- Thông tin JD hiệu lực (merged)
- Timeline phê duyệt
- Tab "Ngân sách": bảng budget items, thêm/sửa/xóa
- Tab "Ứng viên": placeholder → link sang 13.3

---

## Cấu trúc file

```
backend/
  alembic/versions/0033_add_recruitment_planning.py   (NEW)
  app/models/recruitment.py                            (NEW: HeadcountPlan, JobRequisition, RecruitmentBudgetItem)
  app/schemas/recruitment.py                           (NEW)
  app/services/jr_service.py                           (NEW)
  app/services/headcount_plan_service.py               (NEW)
  app/api/v1/endpoints/recruitment.py                  (NEW)
  app/api/v1/router.py                                 (EDIT: include recruitment router)
  tests/test_recruitment_jr.py                         (NEW)

frontend/
  src/services/recruitmentService.ts                   (NEW)
  src/views/recruitment/RecruitmentView.vue            (NEW)
  src/views/recruitment/components/JRListTab.vue       (NEW)
  src/views/recruitment/components/JRFormDialog.vue    (NEW)
  src/views/recruitment/JRDetailView.vue               (NEW)
  src/views/recruitment/components/HeadcountPlanTab.vue (NEW)
  src/assets/styles/views/_recruitment.scss            (NEW)
  src/router/index.ts                                  (EDIT: thêm /recruitment routes)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend: Models & Migration
- Alembic migration 0033
- Models `HeadcountPlan`, `JobRequisition`, `RecruitmentBudgetItem`

### Slice 2 — Backend: JR CRUD + Approval workflow
- `jr_service.py`: CRUD, generate_code, submit/approve/reject/cancel
- `headcount_plan_service.py`: CRUD, fulfillment_rate
- Endpoints `/recruitment/job-requisitions` + `/recruitment/headcount-plans`
- Permissions `recruitment:view`, `recruitment:manage`, `recruitment:approve`

### Slice 3 — Backend: Budget API + Tests
- Budget endpoints
- `tests/test_recruitment_jr.py`

### Slice 4 — Frontend
- `recruitmentService.ts`
- `RecruitmentView.vue` + `JRListTab.vue` + `JRFormDialog.vue`
- `JRDetailView.vue` + `HeadcountPlanTab.vue`
- Router + SCSS

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| JR code bị trùng khi tạo đồng thời | Thấp | Dùng DB sequence hoặc `SELECT MAX + 1 FOR UPDATE` |
| Phê duyệt nhiều cấp phức tạp | Trung bình | MVP chỉ 1 bước approve; cấu hình đa cấp là phase sau |
| JR bị cancel khi đã có ứng viên đang xét | Trung bình | Kiểm tra: chỉ cancel nếu không còn application ở trạng thái active; hoặc require confirm |
| Kế hoạch nhân sự không dùng → tabs rỗng | Thấp | Tab "Kế hoạch nhân sự" hiển thị empty state rõ ràng, không block luồng JR |
