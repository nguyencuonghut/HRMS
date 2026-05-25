# Kế hoạch triển khai — 13.2. Đăng tin tuyển dụng

**Phạm vi:** Job Posting · Đa kênh tuyển dụng · Danh mục kênh · Tuân thủ pháp lý đăng tin  
**Phụ thuộc:** `13.1 JR` (job_requisitions) · `departments` ✅ · `job_positions` ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §13.2

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `job_requisitions` | ❌ Xây ở 13.1 | Tin đăng tạo từ JR đã duyệt |
| `recruitment_channels` | ❌ Chưa có | Danh mục kênh tuyển dụng |
| `job_postings` | ❌ Chưa có | |
| API + Frontend | ❌ Chưa có | |

---

## Phạm vi

**Trong phạm vi:**
- Danh mục kênh tuyển dụng (catalog)
- Tạo/sửa/đóng tin tuyển dụng từ JR đã duyệt
- Phân loại tin: nội bộ / bên ngoài
- Quản lý trạng thái tin (vòng đời đầy đủ)
- Ghi nhận nguồn ứng viên theo kênh (dùng ở 13.3)
- Cảnh báo ngôn ngữ phân biệt đối xử

**Ngoài phạm vi:**
- Tự động đăng lên TopCV/VietnamWorks qua API (tích hợp bên ngoài)
- Career Page nhúng vào website (tính năng nâng cao)
- Quản lý ứng viên (→ 13.3)

---

## Data Model

### Bảng `recruitment_channels`

```sql
CREATE TABLE recruitment_channels (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(50) UNIQUE NOT NULL,   -- topcv | vietnamworks | linkedin | referral | internal | ...
    name        VARCHAR(200) NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order  SMALLINT DEFAULT 0
);
```

Seed dữ liệu mặc định:
```
internal      → Tuyển nội bộ
referral      → Giới thiệu nội bộ
company_web   → Website công ty
topcv         → TopCV
vietnamworks  → VietnamWorks
vietnamjobs   → VietnamJobs
linkedin      → LinkedIn
headhunter    → Headhunter / Agency
other         → Khác
```

### Bảng `job_postings`

```sql
CREATE TABLE job_postings (
    id                  SERIAL PRIMARY KEY,
    job_requisition_id  INTEGER NOT NULL REFERENCES job_requisitions(id),

    title               VARCHAR(300) NOT NULL,
    description         TEXT NOT NULL,       -- nội dung mô tả hiển thị ra ngoài
    requirements        TEXT,
    benefits            TEXT,
    work_location       VARCHAR(300),        -- địa điểm làm việc
    deadline            DATE,                -- hạn nộp hồ sơ
    salary_display      VARCHAR(100),        -- "Thỏa thuận" hoặc "15-20 triệu"

    posting_type        VARCHAR(20) NOT NULL DEFAULT 'external',  -- internal | external
    channels            INTEGER[],           -- mảng channel_id đã đăng

    status              VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- draft | active | closed | expired

    opened_at           TIMESTAMP,           -- khi chuyển sang active
    closed_at           TIMESTAMP,           -- khi đóng thủ công
    expires_at          TIMESTAMP,           -- deadline → tự động expired

    note                TEXT,                -- ghi chú nội bộ
    created_by_id       INTEGER NOT NULL REFERENCES users(id),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_job_postings_jr ON job_postings(job_requisition_id);
CREATE INDEX ix_job_postings_status ON job_postings(status);
```

---

## API Design

### Danh mục kênh tuyển dụng

```
GET    /recruitment/channels              -- danh sách kênh (public trong module)
POST   /recruitment/channels             -- thêm kênh mới
PUT    /recruitment/channels/{id}        -- sửa
DELETE /recruitment/channels/{id}        -- chỉ khi không có posting đã dùng
```

### Job Posting

```
GET    /recruitment/job-postings?status=&job_requisition_id=&page=&page_size=
POST   /recruitment/job-postings                    -- tạo từ JR đã duyệt
GET    /recruitment/job-postings/{id}
PUT    /recruitment/job-postings/{id}               -- chỉ khi draft/active

POST   /recruitment/job-postings/{id}/publish       -- draft → active
POST   /recruitment/job-postings/{id}/close         -- active → closed
POST   /recruitment/job-postings/{id}/reopen        -- closed → active (nếu deadline chưa qua)
```

### Permissions

| Action | Permission |
|---|---|
| Xem posting | `recruitment:view` |
| Tạo / sửa / đóng | `recruitment:manage` |
| Quản lý kênh | `recruitment:manage` |

---

## Schemas

```python
class RecruitmentChannelRead(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool
    sort_order: int

class JobPostingCreate(BaseModel):
    job_requisition_id: int
    title: str
    description: str
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    work_location: Optional[str] = None
    deadline: Optional[date] = None
    salary_display: Optional[str] = None  -- "Thỏa thuận" hoặc khoảng lương
    posting_type: str = "external"        -- internal | external
    channels: List[int] = []             -- danh sách channel_id

class JobPostingRead(BaseModel):
    id: int
    job_requisition_id: int
    job_requisition_code: str
    job_position_name: str
    department_name: str
    title: str
    description: str
    requirements: Optional[str]
    benefits: Optional[str]
    work_location: Optional[str]
    deadline: Optional[date]
    salary_display: Optional[str]
    posting_type: str
    channels: List[RecruitmentChannelRead]
    status: str
    opened_at: Optional[datetime]
    closed_at: Optional[datetime]
    candidate_count: int   -- số ứng viên đã apply (join từ applications)
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime

class JobPostingListPage(BaseModel):
    items: List[JobPostingRead]
    total: int
    page: int
    page_size: int
```

---

## Service Logic

### `job_posting_service.py`

**`create_posting(session, data, created_by_id) → JobPostingRead`**
- Validate `job_requisition_id`: JR phải có `status = approved` hoặc `in_progress`
- Validate `channels`: tất cả channel_id phải tồn tại và `is_active = True`
- Validate `deadline`: không được nhỏ hơn ngày hiện tại
- Khi tạo: `status = draft`

**`publish_posting(session, posting_id, user_id)`**
- `status = draft` → `active`
- Ghi `opened_at = now()`
- Cập nhật `job_requisition.status → in_progress` nếu chưa phải

**`close_posting(session, posting_id, user_id, reason?)`**
- `status = active` → `closed`
- Ghi `closed_at = now()`

**`check_expired_postings(session)` — scheduled task**
- Chạy hàng ngày: tìm posting `status = active` có `deadline < today` → chuyển `expired`

**`validate_posting_language(text: str) → List[str]`**
- Kiểm tra danh sách từ khóa vi phạm pháp lý (Điều 8 BLLĐ):
  - `["nam giới", "nữ giới", "độc thân", "chưa kết hôn", "không có con", "dưới 30 tuổi", ...]`
- Trả về danh sách từ khóa phát hiện được (warning, không block save)
- Service trả về warnings → Frontend hiển thị cảnh báo vàng

---

## Thiết kế Frontend

### `JobPostingTab.vue` (trong `RecruitmentView.vue`)

**Toolbar:**
- Button "Tạo tin tuyển dụng" → `JobPostingFormDialog.vue`
- Filter: Status (chip), Phòng ban, Loại (nội bộ/ngoài), Năm

**DataTable:**

| Cột | Nội dung |
|---|---|
| Tiêu đề | `title` |
| JR | `job_requisition_code` |
| Loại | Tag "Nội bộ" / "Bên ngoài" |
| Kênh | Icons kênh đã đăng |
| Hạn nộp | `deadline` (đỏ nếu < 7 ngày) |
| Ứng viên | Số ứng viên đã apply |
| Trạng thái | Tag màu |
| Thao tác | Xem / Sửa / Đăng / Đóng |

**Tag màu status:**
- `draft` → secondary
- `active` → success
- `closed` → warn
- `expired` → danger

### `JobPostingFormDialog.vue`

- Select JR (lọc theo approved/in_progress)
- Tự động điền `title`, `description`, `requirements` từ JR (editable)
- **Cảnh báo vi phạm pháp lý**: sau khi nhập mô tả/yêu cầu, gọi validate và hiển thị Message component màu vàng nếu phát hiện từ khóa vi phạm
- Select đa kênh: MultiSelect với danh sách kênh
- Radio: Nội bộ / Bên ngoài
- DatePicker: Hạn nộp hồ sơ
- Input: Mức lương hiển thị (text tự do)

### `JobPostingDetailView.vue`

- Hiển thị nội dung tin (preview như ứng viên thấy)
- Timeline trạng thái
- Danh sách ứng viên đã apply (link sang 13.3)

---

## Cấu trúc file

```
backend/
  alembic/versions/0034_add_job_postings.py            (NEW)
  app/models/recruitment.py                             (EDIT: thêm RecruitmentChannel, JobPosting)
  app/schemas/recruitment.py                            (EDIT: thêm posting schemas)
  app/services/job_posting_service.py                  (NEW)
  app/api/v1/endpoints/recruitment.py                  (EDIT: thêm posting + channel endpoints)
  tests/test_recruitment_posting.py                    (NEW)

frontend/
  src/services/recruitmentService.ts                   (EDIT: thêm posting API)
  src/views/recruitment/components/JobPostingTab.vue   (NEW)
  src/views/recruitment/components/JobPostingFormDialog.vue (NEW)
  src/views/recruitment/JobPostingDetailView.vue        (NEW)
  src/router/index.ts                                  (EDIT)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend: Model + Channels
- Migration 0034
- Model `RecruitmentChannel`, `JobPosting`
- CRUD channels endpoint
- Seed dữ liệu kênh mặc định

### Slice 2 — Backend: Posting CRUD + workflow
- `job_posting_service.py`
- Endpoints: tạo, sửa, publish, close, reopen
- Validate language (danh sách từ khóa)
- Scheduled task check expired

### Slice 3 — Backend: Tests

### Slice 4 — Frontend

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| Một JR có nhiều posting (đăng lại khi hết hạn) | Thấp | Cho phép nhiều posting/JR, chỉ 1 `active` tại một thời điểm |
| Cảnh báo từ khóa bị false positive | Trung bình | Warning không block; HR quyết định cuối cùng; danh sách từ khóa có thể cấu hình |
| Đăng nội bộ lộ thông tin nhạy cảm (lương) | Thấp | `salary_display` là text tự do; HR chủ động điền "Thỏa thuận" |
| Tự động expire sai múi giờ | Thấp | Dùng UTC, so sánh `deadline.date() < date.today()` |
