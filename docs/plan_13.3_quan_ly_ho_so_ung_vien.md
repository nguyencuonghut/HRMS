# Kế hoạch triển khai — 13.3. Quản lý hồ sơ ứng viên

**Phạm vi:** Candidate profile · Talent Pool · Tiếp nhận hồ sơ · Đính kèm file  
**Phụ thuộc:** `13.1 JR` · `13.2 Job Postings` · `education_levels` ✅ · `nationalities / ethnicities / religions` ✅ · MinIO ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §13.3  
**Lưu ý kiến trúc:** Bảng `candidates` **độc lập** với `employees` — chỉ migrate sang employees sau khi có Quyết định tuyển dụng (13.5)

**Nguyên tắc thiết kế cập nhật:** `Candidate` phải là một **Employee Draft + Recruitment Metadata**. Các trường nhân thân và giấy tờ cần bám sát shape của `Employee` để bước convert ở 13.5 là copy/validate, không phải transform nhiều lớp.

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `employees` | ✅ Hoàn thành | Bảng riêng — candidates không dùng |
| MinIO | ✅ Hoàn thành | Tái dụng lưu file CV/đính kèm |
| `education_levels` | ✅ Hoàn thành | Tham chiếu trình độ học vấn |
| `candidates` | ❌ Chưa có | Model mới hoàn toàn |
| `candidate_applications` | ❌ Chưa có | |
| API + Frontend | ❌ Chưa có | |

---

## Phạm vi

**Trong phạm vi:**
- CRUD hồ sơ ứng viên (candidates): thông tin cá nhân, học vấn, kinh nghiệm, kỹ năng
- Upload file đính kèm (CV, bằng cấp, CCCD scan, ảnh thẻ) → MinIO
- Liên kết ứng viên với JR qua `candidate_applications`
- Import hàng loạt từ Excel
- Talent Pool: tìm kiếm, lọc, gắn ứng viên vào JR mới
- Ghi chú nội bộ

**Ngoài phạm vi:**
- Parse CV tự động từ PDF/Word (NLP — ngoài phạm vi cơ bản)
- Career Page form online (tính năng nâng cao)
- Pipeline xử lý ứng viên (→ 13.4)

---

## Data Model

### Bảng `candidates`

```sql
CREATE TABLE candidates (
    id              SERIAL PRIMARY KEY,

    -- Thông tin cá nhân
    full_name       VARCHAR(200) NOT NULL,
    last_name       VARCHAR(100),         -- ưu tiên lưu cùng shape với employees
    first_name      VARCHAR(100),
    date_of_birth   DATE,
    gender          VARCHAR(10),          -- male | female | other
    nationality_id  INTEGER REFERENCES nationalities(id),
    raw_nationality_text VARCHAR(100),    -- dữ liệu thô khi import, dùng để map catalog
    ethnicity_id    INTEGER REFERENCES ethnicities(id),
    religion_id     INTEGER REFERENCES religions(id),

    -- Giấy tờ nhận dạng — align với employees
    id_number       VARCHAR(30),          -- CCCD/CMND/Hộ chiếu
    id_issued_on    DATE,
    id_issued_by    VARCHAR(200),
    id_expires_on   DATE,
    passport_number VARCHAR(50),
    passport_issued_on DATE,
    passport_expires_on DATE,
    work_permit_number VARCHAR(50),
    work_permit_issued_on DATE,
    work_permit_expires_on DATE,

    -- Liên lạc / mã số cá nhân — align với employees
    phone_number    VARCHAR(20),
    personal_email  VARCHAR(200),
    personal_tax_code VARCHAR(20),
    bhxh_code       VARCHAR(20),

    -- Địa chỉ (text tự do — không normalize như Employee)
    address         TEXT,

    -- Thông tin nghề nghiệp hiện tại
    current_company  VARCHAR(200),
    current_position VARCHAR(200),
    expected_salary  NUMERIC(15,2),       -- lương kỳ vọng

    -- Nguồn tiếp nhận
    source_channel_id INTEGER REFERENCES recruitment_channels(id),
    source_note      TEXT,               -- ghi chú thêm về nguồn

    -- Nội bộ
    internal_note   TEXT,
    tags            TEXT[],              -- mảng tag phân loại (kỹ năng chính, vị trí phù hợp,...)

    is_active       BOOLEAN NOT NULL DEFAULT TRUE,  -- false khi ứng viên yêu cầu xóa thông tin
    created_by_id   INTEGER REFERENCES users(id),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_candidates_personal_email ON candidates(personal_email);
CREATE INDEX ix_candidates_name  ON candidates USING gin(to_tsvector('simple', full_name));
```

### Bảng `candidate_educations`

```sql
CREATE TABLE candidate_educations (
    id                  SERIAL PRIMARY KEY,
    candidate_id        INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    institution_id      INTEGER REFERENCES educational_institutions(id) ON DELETE SET NULL,
    institution_name    VARCHAR(300),   -- denormalized / raw fallback
    major_id            INTEGER REFERENCES education_majors(id) ON DELETE SET NULL,
    major_name          VARCHAR(300),   -- denormalized / raw fallback
    education_level_id  INTEGER REFERENCES education_levels(id) ON DELETE SET NULL,
    graduation_year     SMALLINT,
    diploma_type        VARCHAR(100),
    is_main_education   BOOLEAN DEFAULT FALSE,
    note                TEXT
);
```

**Nguyên tắc thiết kế:** `candidate_educations` phải bám gần `employee_education_histories` để giảm chi phí convert ở `13.5`.
Form nhập tay của ATS dùng catalog `educational_institutions`, `education_majors`, `education_levels`; các cột
`institution_name` / `major_name` chỉ giữ vai trò denormalized hoặc raw fallback cho dữ liệu import/cũ.

### Bảng `candidate_work_experiences`

```sql
CREATE TABLE candidate_work_experiences (
    id              SERIAL PRIMARY KEY,
    candidate_id    INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    company_name    VARCHAR(300) NOT NULL,
    position_name   VARCHAR(200),
    start_date      DATE,
    end_date        DATE,               -- NULL = đang làm
    description     TEXT,
    sort_order      SMALLINT DEFAULT 0
);
```

### Bảng `candidate_skills`

```sql
CREATE TABLE candidate_skills (
    id              SERIAL PRIMARY KEY,
    candidate_id    INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    skill_name      VARCHAR(200) NOT NULL,
    proficiency_level VARCHAR(20),      -- beginner | intermediate | advanced | expert
    UNIQUE (candidate_id, skill_name)
);
```

### Bảng `candidate_attachments`

```sql
CREATE TABLE candidate_attachments (
    id              SERIAL PRIMARY KEY,
    candidate_id    INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    attachment_type VARCHAR(30) NOT NULL,  -- cv | degree | id_card | photo | other
    file_path       VARCHAR(500) NOT NULL,
    file_name       VARCHAR(300) NOT NULL,
    file_size       INTEGER,
    mime_type       VARCHAR(100),
    note            TEXT,
    uploaded_by_id  INTEGER REFERENCES users(id),
    uploaded_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_candidate_attachments_candidate ON candidate_attachments(candidate_id);
```

### Bảng `candidate_applications`

```sql
CREATE TABLE candidate_applications (
    id                  SERIAL PRIMARY KEY,
    candidate_id        INTEGER NOT NULL REFERENCES candidates(id),
    job_requisition_id  INTEGER NOT NULL REFERENCES job_requisitions(id),

    applied_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    source_channel_id   INTEGER REFERENCES recruitment_channels(id),

    -- Pipeline stage hiện tại (update khi chuyển bước)
    current_stage       VARCHAR(50) DEFAULT 'new',
    -- new | screening | test | interview | offer | hired | rejected | withdrawn

    rejection_reason    TEXT,          -- lý do loại (ghi để báo cáo)
    internal_note       TEXT,

    created_by_id       INTEGER REFERENCES users(id),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (candidate_id, job_requisition_id)  -- 1 ứng viên 1 lần apply cho 1 JR
);

CREATE INDEX ix_applications_jr ON candidate_applications(job_requisition_id);
CREATE INDEX ix_applications_stage ON candidate_applications(current_stage);
```

### Alembic migration

Files:
- `0035_add_candidates.py`
- `0036_align_candidate_personal_fields.py`

---

## API Design

### Candidates

```
GET    /recruitment/candidates?search=&source_channel_id=&page=&page_size=
POST   /recruitment/candidates
POST   /recruitment/candidates/check-duplicates
GET    /recruitment/candidates/{id}
PUT    /recruitment/candidates/{id}
DELETE /recruitment/candidates/{id}   -- soft delete (is_active=false)

-- Sub-resources
POST   /recruitment/candidates/{id}/educations
PUT    /recruitment/candidates/{id}/educations/{edu_id}
DELETE /recruitment/candidates/{id}/educations/{edu_id}

POST   /recruitment/candidates/{id}/work-experiences
PUT    /recruitment/candidates/{id}/work-experiences/{exp_id}
DELETE /recruitment/candidates/{id}/work-experiences/{exp_id}

POST   /recruitment/candidates/{id}/skills
DELETE /recruitment/candidates/{id}/skills/{skill_id}

POST   /recruitment/candidates/{id}/attachments        -- multipart/form-data
DELETE /recruitment/candidates/{id}/attachments/{att_id}
GET    /recruitment/candidates/{id}/attachments/{att_id}/download
```

### Applications

```
POST   /recruitment/candidates/{id}/apply              -- apply ứng viên vào JR
GET    /recruitment/job-requisitions/{jr_id}/applications?stage=&page=&page_size=
GET    /recruitment/applications/{id}
```

### Import

```
POST   /recruitment/candidates/import                  -- Excel bulk import
GET    /recruitment/candidates/import-template         -- tải file mẫu
```

### Permissions

| Action | Permission |
|---|---|
| Xem danh sách | `recruitment:view` |
| Thêm/sửa/xóa | `recruitment:manage` |
| Upload file | `recruitment:manage` |
| Import | `recruitment:manage` |

---

## Schemas

```python
class CandidateCreate(BaseModel):
    full_name: str
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality_id: Optional[int] = None
    raw_nationality_text: Optional[str] = None
    ethnicity_id: Optional[int] = None
    religion_id: Optional[int] = None
    id_number: Optional[str] = None
    id_issued_on: Optional[date] = None
    id_issued_by: Optional[str] = None
    id_expires_on: Optional[date] = None
    passport_number: Optional[str] = None
    passport_issued_on: Optional[date] = None
    passport_expires_on: Optional[date] = None
    work_permit_number: Optional[str] = None
    work_permit_issued_on: Optional[date] = None
    work_permit_expires_on: Optional[date] = None
    phone_number: Optional[str] = None
    personal_email: Optional[str] = None
    personal_tax_code: Optional[str] = None
    bhxh_code: Optional[str] = None
    address: Optional[str] = None
    current_company: Optional[str] = None
    current_position: Optional[str] = None
    expected_salary: Optional[Decimal] = None
    source_channel_id: Optional[int] = None
    source_note: Optional[str] = None
    internal_note: Optional[str] = None
    tags: List[str] = []

class CandidateRead(CandidateCreate):
    id: int
    nationality_name: Optional[str]
    ethnicity_name: Optional[str]
    religion_name: Optional[str]
    source_channel_name: Optional[str]
    educations: List[CandidateEducationRead]
    work_experiences: List[CandidateWorkExpRead]
    skills: List[CandidateSkillRead]
    attachments: List[CandidateAttachmentRead]
    active_applications: int   -- số JR đang xét
    identity_strength: Literal["weak", "medium", "strong"]
    identity_strength_label: str
    conversion_ready: bool
    conversion_missing_fields: List[str]
    created_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime

class CandidateListItem(BaseModel):
    id: int
    full_name: str
    phone_number: Optional[str]
    personal_email: Optional[str]
    current_position: Optional[str]
    nationality_name: Optional[str]
    source_channel_name: Optional[str]
    active_applications: int
    identity_strength: Literal["weak", "medium", "strong"]
    identity_strength_label: str
    created_at: datetime

class CandidateListPage(BaseModel):
    items: List[CandidateListItem]
    total: int
    page: int
    page_size: int

class CandidateDuplicateCheck(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    id_number: Optional[str] = None
    passport_number: Optional[str] = None
    phone_number: Optional[str] = None
    personal_email: Optional[str] = None
    exclude_candidate_id: Optional[int] = None

class CandidateDuplicateMatch(BaseModel):
    candidate_id: int
    full_name: str
    date_of_birth: Optional[date]
    id_number: Optional[str]
    passport_number: Optional[str]
    phone_number: Optional[str]
    personal_email: Optional[str]
    current_company: Optional[str]
    current_position: Optional[str]
    match_level: Literal["exact", "possible"]
    reason_codes: List[str]
    reason_labels: List[str]

class CandidateDuplicateCheckResult(BaseModel):
    exact_matches: List[CandidateDuplicateMatch]
    possible_matches: List[CandidateDuplicateMatch]

class ApplicationCreate(BaseModel):
    job_requisition_id: int
    applied_date: date = Field(default_factory=date.today)
    source_channel_id: Optional[int] = None
    internal_note: Optional[str] = None

class ApplicationRead(BaseModel):
    id: int
    candidate_id: int
    candidate_name: str
    job_requisition_id: int
    job_requisition_code: str
    job_position_name: str
    department_name: str
    applied_date: date
    source_channel_name: Optional[str]
    current_stage: str
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
```

---

## Service Logic

### `candidate_service.py`

**`create_candidate(session, data, created_by_id) → CandidateRead`**
- Bắt buộc `full_name`
- Bắt buộc có ít nhất 1 identity anchor: `personal_email` hoặc `phone_number` hoặc `id_number` hoặc `passport_number`
- Nếu `last_name` / `first_name` không truyền → auto tách từ `full_name`
- Nếu `raw_nationality_text` có giá trị → cố gắng map sang `nationality_id`
- Tạo candidate record

**`get_candidate_identity_strength(candidate) → weak | medium | strong`**
- `strong`: có `id_number` hoặc `passport_number`
- `medium`: có `personal_email` hoặc `phone_number` hoặc `full_name + date_of_birth`
- `weak`: chỉ có `full_name` hoặc dữ liệu nhận diện quá ít
- Dùng để hiển thị badge trên danh sách/chi tiết, giúp HR biết hồ sơ nào khó đối chiếu trùng

**`check_candidate_duplicates(session, data) → CandidateDuplicateCheckResult`**
- Mục tiêu: cảnh báo sớm candidate có thể đã tồn tại trước khi HR bấm "Tạo"
- Rule `exact`:
  - trùng `id_number`
  - hoặc trùng `passport_number`
  - hoặc trùng `personal_email`
  - hoặc trùng `phone_number`
- Rule `possible`:
  - trùng `full_name + date_of_birth`
  - hoặc trùng `full_name` đơn thuần
- `exclude_candidate_id` dùng cho mode edit để không tự match chính record đang sửa
- Endpoint chỉ trả warning/mức độ nghi ngờ, không tự merge và không block cứng việc tạo mới

**`search_candidates(session, search, source_channel_id, page, page_size)`**
- Full-text search trên `full_name` (GIN index), `personal_email`, `phone_number`
- Lọc theo `source_channel_id`

**`get_candidate_conversion_readiness(candidate) → {ready, missing_fields}`**
- Kiểm tra các field tối thiểu để tạo `Employee` ở 13.5:
  - `last_name`, `first_name`
  - `date_of_birth`, `gender`
  - `nationality_id`
  - `id_number`, `id_issued_on`, `id_issued_by`
- Dùng để hiển thị cảnh báo sớm trên hồ sơ ứng viên, thay vì fail muộn ở bước convert

**`apply_candidate(session, candidate_id, jr_id, data, created_by_id)`**
- Kiểm tra unique `(candidate_id, jr_id)` — cùng ứng viên không apply 2 lần cùng 1 JR
- Kiểm tra JR `status ∈ {approved, in_progress}`
- Tạo `candidate_application` với `current_stage = 'new'`
- Cập nhật `jr.status → in_progress` nếu chưa phải

**`upload_attachment(session, candidate_id, file, attachment_type, user_id)`**
- Upload lên MinIO: bucket `hrms-attachments`, path `recruitment/candidates/{id}/{type}/{filename}`
- Lưu record vào `candidate_attachments`
- Giới hạn: 20MB/file; mime_type: PDF, Word, JPG, PNG

**`import_candidates_excel(session, content, created_by_id) → ImportResult`**
- Đọc file Excel theo mẫu
- Validate từng dòng
- Upsert theo `personal_email` (nếu email cá nhân đã có → update, chưa có → insert)
- Trả về `created`, `updated`, `skipped`, `errors`

---

## Thiết kế Frontend

### `CandidateListTab.vue` (trong `RecruitmentView.vue`)

**Toolbar:**
- Button "Thêm ứng viên" → `CandidateFormDialog.vue`
- Button "Import Excel" → `CandidateImportDialog.vue`
- Search input (`full_name`, `personal_email`, `phone_number`)
- Filter: Kênh nguồn, Trạng thái ứng tuyển
- Hiển thị badge `identity_strength` ngay trong danh sách

**DataTable:**

| Cột | Nội dung |
|---|---|
| Họ tên | Link → CandidateDetailView |
| SĐT / Email | |
| Vị trí hiện tại | `current_company` — `current_position` |
| Nguồn | `source_channel_name` |
| Đang xét | Số JR active (Badge) |
| Ngày tạo | |
| Thao tác | Sửa / Xóa / Apply vào JR |

### `CandidateDetailView.vue`

**Tabs:**
- **Thông tin cá nhân**: form edit thông tin cơ bản
- **Học vấn & Kinh nghiệm**: danh sách, inline add/edit
- **Kỹ năng**: tag cloud, thêm kỹ năng
- **Hồ sơ đính kèm**: upload CV/bằng cấp/ảnh, preview PDF, download
- **Ứng tuyển**: danh sách JR đã apply + trạng thái pipeline
- **Ghi chú nội bộ**: textarea

**Button "Gắn vào JR"**: mở dialog chọn JR để apply

### `CandidateFormDialog.vue`

- Thông tin cá nhân bám theo shape `Employee`:
  - `full_name`, `last_name`, `first_name`
  - `date_of_birth`, `gender`
  - `nationality_id`, `ethnicity_id`, `religion_id`
  - `id_number`, `id_issued_on`, `id_issued_by`
  - `phone_number`, `personal_email`, `personal_tax_code`, `bhxh_code`
- Chọn nguồn kênh
- Tags (chip input)
- Ghi chú nội bộ
- Gọi `POST /recruitment/candidates/check-duplicates` khi user nhập các field nhận diện
- Trước khi submit create: validate phải có ít nhất 1 identity anchor (`personal_email` / `phone_number` / `id_number` / `passport_number`)
- Nếu có match:
  - hiển thị panel cảnh báo trong modal
  - tách rõ `Trùng mạnh` (`exact_matches`) và `Có thể trùng` (`possible_matches`)
  - mỗi item hiển thị lý do match + thông tin nhận diện chính để HR quyết định mở hồ sơ cũ hay vẫn tạo mới

---

## Cấu trúc file

```
backend/
  alembic/versions/0035_add_candidates.py              (NEW)
  app/models/recruitment.py                             (EDIT: thêm Candidate, CandidateEducation,
                                                               CandidateWorkExperience, CandidateSkill,
                                                               CandidateAttachment, CandidateApplication)
  app/schemas/recruitment.py                            (EDIT: thêm candidate schemas)
  app/services/candidate_service.py                    (NEW)
  app/services/candidate_import_service.py             (NEW)
  app/api/v1/endpoints/recruitment.py                  (EDIT: thêm candidate + application endpoints)
  tests/test_recruitment_candidates.py                 (NEW)

frontend/
  src/services/recruitmentService.ts                   (EDIT: thêm candidate API)
  src/views/recruitment/components/CandidateListTab.vue (NEW)
  src/views/recruitment/CandidateDetailView.vue        (NEW)
  src/views/recruitment/components/CandidateFormDialog.vue (NEW)
  src/views/recruitment/components/CandidateImportDialog.vue (NEW)
  src/router/index.ts                                  (EDIT)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend: Models + Migration
- Migration 0035
- Models: Candidate, CandidateEducation, CandidateWorkExperience, CandidateSkill, CandidateAttachment, CandidateApplication

### Slice 2 — Backend: CRUD Candidate + Sub-resources
- `candidate_service.py`: CRUD, search, sub-resources
- Endpoints cơ bản

### Slice 3 — Backend: Upload + Import + Apply
- Upload attachment → MinIO
- Import Excel
- `apply_candidate` endpoint

### Slice 4 — Backend: Tests

### Slice 5 — Frontend
- `CandidateListTab.vue` + `CandidateFormDialog.vue`
- `CandidateDetailView.vue` với đầy đủ tabs
- `CandidateImportDialog.vue`

### Ghi chú triển khai mới
- Dù `Candidate` vẫn cho phép tạo nhanh với dữ liệu chưa đủ, shape dữ liệu phải bám `Employee`
- Convert ở 13.5 chỉ được phép fail do dữ liệu thiếu bắt buộc, không được fail do lệch type/text-vs-FK

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| Trùng ứng viên (cùng người apply nhiều lần) | Trung bình | Dùng `check-duplicates` trước khi tạo: exact theo `id_number` / `passport_number` / `personal_email` / `phone_number`, possible theo `full_name(+date_of_birth)`; HR quyết định mở hồ sơ cũ hay vẫn tạo mới |
| Hồ sơ định danh quá yếu, khó đối chiếu trùng | Trung bình | Rule create mới yêu cầu ít nhất 1 identity anchor; đồng thời hiển thị badge `identity_strength` để HR ưu tiên bổ sung dữ liệu |
| File CV lớn (nhiều trang, scan chất lượng cao) | Trung bình | Giới hạn 20MB/file; MinIO xử lý async |
| GDPR / quyền riêng tư | Trung bình | `is_active = false` khi ứng viên yêu cầu xóa; không xóa cứng để tránh orphan records |
| Talent pool quá lớn, search chậm | Thấp | GIN index full-text; pagination bắt buộc |
| Import trùng email | Thấp | Upsert theo `personal_email` — update nếu đã có, insert nếu chưa |
