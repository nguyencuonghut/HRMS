# Kế hoạch triển khai — 13.4. Quy trình tuyển chọn (Recruitment Pipeline)

**Phạm vi:** Pipeline stages · Sàng lọc hồ sơ · Bài test · Phỏng vấn · Interview Kit (scorecard)  
**Phụ thuộc:** `13.1 JR` · `13.3 Candidates + Applications` · `users` ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §13.4

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `candidate_applications` | ✅ Hoàn thành | Xây ở 13.3, có trường `current_stage` |
| `pipeline_stage_templates` + items | ✅ Hoàn thành | Migration 0037 |
| `pipeline_stages` | ✅ Hoàn thành | Migration 0037 |
| `candidate_stage_results` | ✅ Hoàn thành | Migration 0037 |
| `interview_sessions` | ✅ Hoàn thành | Migration 0037 |
| `interview_panelists` | ✅ Hoàn thành | Migration 0037 |
| `interview_questions` | ✅ Hoàn thành | Migration 0037 |
| `scorecard_criteria` | ✅ Hoàn thành | Migration 0037 |
| Backend API | ✅ Hoàn thành | Tất cả endpoints đã có |
| Frontend Kanban + Application Detail | ✅ Hoàn thành | Slice 5 + 6 |
| Danh mục tuyển dụng (Catalog) | ✅ Hoàn thành | `RecruitmentCatalogView.vue` |

---

## Phạm vi

**Trong phạm vi:**
- Cấu hình pipeline bước tuyển chọn cho từng JR
- Sàng lọc hồ sơ: đánh dấu phù hợp/không phù hợp, ghi lý do
- Bài test: ghi nhận kết quả (nhập tay hoặc upload file)
- Lập lịch phỏng vấn: ngày giờ, hình thức, phân công người phỏng vấn
- Ghi nhận kết quả phỏng vấn theo scorecard tiêu chí
- Thư viện câu hỏi phỏng vấn (Interview Kit)
- Chuyển ứng viên qua các bước (advance/reject/hold)

**Ngoài phạm vi:**
- Tự động gửi email lịch phỏng vấn (→ 13.7)
- Offer Letter (→ 13.5)
- Video phỏng vấn, tích hợp calendar (ngoài phạm vi)

---

## Data Model

### Bảng `pipeline_stage_templates`

```sql
-- Mẫu cấu hình pipeline (chia sẻ giữa các JR cùng loại vị trí)
CREATE TABLE pipeline_stage_templates (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,   -- "Pipeline nhân viên văn phòng"
    job_position_id INTEGER REFERENCES job_positions(id),  -- NULL = áp cho mọi vị trí
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_by_id   INTEGER REFERENCES users(id),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE pipeline_stage_template_items (
    id                  SERIAL PRIMARY KEY,
    template_id         INTEGER NOT NULL REFERENCES pipeline_stage_templates(id) ON DELETE CASCADE,
    stage_order         SMALLINT NOT NULL,
    stage_name          VARCHAR(100) NOT NULL,
    stage_type          VARCHAR(30) NOT NULL,  -- screening | test | interview | final
    is_required         BOOLEAN DEFAULT TRUE,
    UNIQUE (template_id, stage_order)
);
```

### Bảng `pipeline_stages`

```sql
-- Pipeline cụ thể gắn với 1 JR
CREATE TABLE pipeline_stages (
    id                  SERIAL PRIMARY KEY,
    job_requisition_id  INTEGER NOT NULL REFERENCES job_requisitions(id) ON DELETE CASCADE,
    stage_order         SMALLINT NOT NULL,
    stage_name          VARCHAR(100) NOT NULL,
    stage_type          VARCHAR(30) NOT NULL,  -- screening | test | interview | final
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (job_requisition_id, stage_order)
);

CREATE INDEX ix_pipeline_stages_jr ON pipeline_stages(job_requisition_id);
```

### Bảng `candidate_stage_results`

```sql
-- Kết quả của từng ứng viên tại từng bước
CREATE TABLE candidate_stage_results (
    id                  SERIAL PRIMARY KEY,
    application_id      INTEGER NOT NULL REFERENCES candidate_applications(id) ON DELETE CASCADE,
    stage_id            INTEGER NOT NULL REFERENCES pipeline_stages(id),

    result              VARCHAR(20),   -- pass | fail | hold | pending
    score               NUMERIC(5,2),  -- điểm tổng (optional)
    notes               TEXT,          -- nhận xét tổng hợp

    -- Với bước test: upload file kết quả
    test_file_path      VARCHAR(500),
    test_file_name      VARCHAR(300),
    test_score_raw      NUMERIC(5,2),  -- điểm gốc từ test
    test_pass_threshold NUMERIC(5,2),  -- ngưỡng đạt

    evaluated_by_id     INTEGER REFERENCES users(id),
    evaluated_at        TIMESTAMP,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (application_id, stage_id)
);
```

### Bảng `interview_sessions`

```sql
CREATE TABLE interview_sessions (
    id              SERIAL PRIMARY KEY,
    application_id  INTEGER NOT NULL REFERENCES candidate_applications(id) ON DELETE CASCADE,
    stage_id        INTEGER NOT NULL REFERENCES pipeline_stages(id),

    scheduled_at    TIMESTAMP NOT NULL,
    duration_minutes SMALLINT DEFAULT 60,
    format          VARCHAR(20) NOT NULL DEFAULT 'in_person',  -- in_person | online | phone
    location        VARCHAR(300),   -- địa điểm hoặc link meeting
    note            TEXT,

    status          VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    -- scheduled | completed | cancelled | rescheduled

    completed_at    TIMESTAMP,
    cancel_reason   TEXT,
    created_by_id   INTEGER REFERENCES users(id),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_interview_sessions_application ON interview_sessions(application_id);
CREATE INDEX ix_interview_sessions_scheduled ON interview_sessions(scheduled_at);
```

### Bảng `interview_panelists`

```sql
-- Người tham gia phỏng vấn + đánh giá của họ
CREATE TABLE interview_panelists (
    id                  SERIAL PRIMARY KEY,
    interview_session_id INTEGER NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    user_id             INTEGER NOT NULL REFERENCES users(id),

    -- Scorecard từng tiêu chí (JSONB linh hoạt)
    criteria_scores     JSONB,
    -- [{"criterion": "Thái độ", "score": 4, "max_score": 5}, ...]

    overall_score       NUMERIC(4,2),  -- điểm tổng (tính tự động hoặc nhập tay)
    result              VARCHAR(20),   -- pass | fail | hold
    private_notes       TEXT,          -- ghi chú riêng, không chia sẻ với NV

    submitted_at        TIMESTAMP,
    UNIQUE (interview_session_id, user_id)
);
```

### Bảng `interview_questions`

```sql
-- Thư viện câu hỏi phỏng vấn
CREATE TABLE interview_questions (
    id              SERIAL PRIMARY KEY,
    question_text   TEXT NOT NULL,
    category        VARCHAR(100),     -- "Kỹ năng chuyên môn", "Hành vi", "Tình huống",...
    difficulty      VARCHAR(20),      -- easy | medium | hard
    job_position_id INTEGER REFERENCES job_positions(id),  -- NULL = dùng cho mọi vị trí
    stage_type      VARCHAR(30),      -- gợi ý dùng ở bước nào (interview | screening)
    is_active       BOOLEAN DEFAULT TRUE,
    created_by_id   INTEGER REFERENCES users(id),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_interview_questions_position ON interview_questions(job_position_id);
```

### Bảng `scorecard_criteria`

```sql
-- Bộ tiêu chí đánh giá mẫu cho từng vị trí/bước
CREATE TABLE scorecard_criteria (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,    -- "Kỹ năng giao tiếp"
    job_position_id INTEGER REFERENCES job_positions(id),  -- NULL = áp dụng chung
    stage_type      VARCHAR(30),
    max_score       SMALLINT NOT NULL DEFAULT 5,
    sort_order      SMALLINT DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE
);
```

### Alembic migration

File: `0037_add_recruitment_pipeline.py`

---

## API Design

### Pipeline Stages

```
-- Mẫu pipeline
GET    /recruitment/pipeline-templates
POST   /recruitment/pipeline-templates
PUT    /recruitment/pipeline-templates/{id}
DELETE /recruitment/pipeline-templates/{id}

-- Pipeline của JR cụ thể
GET    /recruitment/job-requisitions/{jr_id}/pipeline
POST   /recruitment/job-requisitions/{jr_id}/pipeline       -- cấu hình hoặc clone từ template
PUT    /recruitment/job-requisitions/{jr_id}/pipeline/{stage_id}
DELETE /recruitment/job-requisitions/{jr_id}/pipeline/{stage_id}
```

### Advance ứng viên qua pipeline

```
POST   /recruitment/applications/{id}/advance
       body: { stage_id, result, notes }

POST   /recruitment/applications/{id}/hold
       body: { notes }

GET    /recruitment/job-requisitions/{jr_id}/kanban
       → { stages: [{ stage, applications: [...] }] }
```

### Kết quả bước (Stage Results)

```
POST   /recruitment/applications/{id}/stages/{stage_id}/result
PUT    /recruitment/applications/{id}/stages/{stage_id}/result
GET    /recruitment/applications/{id}/stages                   -- kết quả tất cả bước
```

### Phỏng vấn

```
POST   /recruitment/applications/{id}/interviews
GET    /recruitment/applications/{id}/interviews
GET    /recruitment/interviews/{id}
PUT    /recruitment/interviews/{id}
POST   /recruitment/interviews/{id}/complete     -- đánh dấu hoàn thành
POST   /recruitment/interviews/{id}/cancel

-- Đánh giá của panelist
POST   /recruitment/interviews/{id}/panelists/{user_id}/score
PUT    /recruitment/interviews/{id}/panelists/{user_id}/score
```

### Interview Kit

```
GET    /recruitment/questions?job_position_id=&category=&stage_type=
POST   /recruitment/questions
PUT    /recruitment/questions/{id}
DELETE /recruitment/questions/{id}

GET    /recruitment/scorecard-criteria?job_position_id=&stage_type=
POST   /recruitment/scorecard-criteria
PUT    /recruitment/scorecard-criteria/{id}      ← thêm sau khi triển khai Catalog UI
DELETE /recruitment/scorecard-criteria/{id}      ← thêm sau khi triển khai Catalog UI
```

### Permissions

| Action | Permission |
|---|---|
| Xem pipeline / kết quả | `recruitment:view` |
| Cấu hình pipeline, ghi kết quả | `recruitment:manage` |
| Đánh giá phỏng vấn (panelist) | `recruitment:view` (user được phân công) |

---

## Schemas (chọn lọc)

```python
class PipelineStageRead(BaseModel):
    id: int
    stage_order: int
    stage_name: str
    stage_type: str
    is_active: bool
    application_count: int   -- số ứng viên đang ở bước này

class KanbanBoard(BaseModel):
    job_requisition_id: int
    stages: List[KanbanStage]

class KanbanStage(BaseModel):
    stage: PipelineStageRead
    applications: List[KanbanCard]

class KanbanCard(BaseModel):
    application_id: int
    candidate_id: int
    candidate_name: str
    applied_date: date
    source_channel: Optional[str]
    last_result: Optional[str]   -- kết quả bước gần nhất

class InterviewSessionCreate(BaseModel):
    stage_id: int
    scheduled_at: datetime
    duration_minutes: int = 60
    format: str = "in_person"
    location: Optional[str] = None
    panelist_user_ids: List[int]  -- danh sách người phỏng vấn

class PanelistScoreSubmit(BaseModel):
    criteria_scores: List[dict]  # [{"criterion": str, "score": int, "max_score": int}]
    overall_score: Optional[Decimal] = None
    result: str   # pass | fail | hold
    private_notes: Optional[str] = None
```

---

## Service Logic

### `pipeline_service.py`

**`setup_pipeline_for_jr(session, jr_id, stages_or_template_id)`**
- Tạo `pipeline_stages` cho JR từ danh sách bước hoặc clone từ template
- Validate: ít nhất 1 bước, stage_order không trùng

**`advance_application(session, application_id, stage_id, result, notes, user_id)`**
- Tạo / cập nhật `candidate_stage_results`
- Nếu result = `pass`: kiểm tra còn bước tiếp theo → cập nhật `application.current_stage`
- Nếu là bước cuối và pass: chuyển `current_stage = 'offer'` (sẵn sàng cho 13.5)
- Nếu result = `fail`: chuyển `current_stage = 'rejected'`, yêu cầu `rejection_reason`

**`get_kanban(session, jr_id) → KanbanBoard`**
- JOIN `pipeline_stages` + `candidate_applications` + `candidates`
- Group ứng viên theo `current_stage`

### `interview_service.py`

**`create_interview(session, application_id, data, created_by_id)`**
- Validate: `stage_id` thuộc JR của application
- Validate `scheduled_at` > now
- Tạo `interview_session`
- Tạo `interview_panelists` rows (chưa có score)
- Trigger email mời phỏng vấn (→ 13.7)

**`submit_panelist_score(session, interview_id, user_id, data)`**
- Chỉ user trong danh sách panelists mới được submit
- Tính `overall_score` từ `criteria_scores` nếu không nhập tay
- Ghi `submitted_at`

**`complete_interview(session, interview_id, user_id)`**
- `status → completed`, ghi `completed_at`
- Tính kết quả tổng hợp: majority vote từ panelists (pass nếu ≥ 50% đánh giá pass)
- Cập nhật `candidate_stage_results` tương ứng

---

## Thiết kế Frontend

### `RecruitmentCatalogView.vue` *(Danh mục tuyển dụng — thêm mới)*

Nằm tại `src/views/catalog/RecruitmentCatalogView.vue`, truy cập qua `/catalog/recruitment` và mục “Danh mục tuyển dụng” trong sidebar.

**3 tab quản trị:**

| Tab | Nội dung | CRUD |
|---|---|---|
| Mẫu quy trình | Danh sách `pipeline_stage_templates` kèm các bước | Tạo / Sửa / Xóa |
| Câu hỏi phỏng vấn | `interview_questions` lọc theo bước và độ khó | Tạo / Sửa / Xóa |
| Tiêu chí chấm điểm | `scorecard_criteria` lọc theo bước | Tạo / Sửa / Xóa |

**Dialog tạo/sửa mẫu quy trình:**
- Nhập tên mẫu, tuỳ chọn đặt làm mặc định
- Thêm/xóa/sắp xếp các bước (`stage_name`, `stage_type`)
- Lưu qua `POST/PUT /recruitment/pipeline-templates`

> **Lưu ý thuật ngữ UI:** Từ “pipeline” và “template” (tiếng Anh) đã được chuyển sang tiếng Việt trong toàn bộ giao diện:
> - “pipeline template” → **”mẫu quy trình”**
> - “Cấu hình pipeline” → **”Cấu hình quy trình”**
> - “Scorecard Criteria” → **”Tiêu chí chấm điểm”**

---

### `PipelineSetupDialog.vue`

- Điểm vào: từ `KanbanPipelineView.vue` khi JR chưa có quy trình
- Chức năng chính:
  - chọn nhanh 1 mẫu quy trình (`pipeline_template`) — hiển thị tên và danh sách bước
  - hoặc tạo thủ công danh sách bước cho JR
  - lưu bằng `POST /recruitment/job-requisitions/{jr_id}/pipeline`
- Nguồn cấu hình:
  - **”Từ mẫu có sẵn”**: chọn template → backend tự clone các bước
  - **”Tạo thủ công”**: nhập tên và loại từng bước

### `KanbanPipelineView.vue`

- Chọn JR → hiển thị Kanban board (nhúng trong tab “Tuyển chọn” của `RecruitmentView.vue`)
- Nếu JR chưa có quy trình:
  - hiển thị empty state với button **”Cấu hình quy trình”** → mở `PipelineSetupDialog`
- Mỗi cột = 1 bước quy trình
- Card ứng viên: tên, ngày apply, nguồn, kết quả bước gần nhất
- Click card → chuyển sang `ApplicationDetailView`

### `ApplicationDetailView.vue`

**Tabs:**
- **Hồ sơ**: thông tin cá nhân, học vấn, kinh nghiệm (readonly từ candidate)
- **Pipeline**: timeline các bước đã qua, kết quả từng bước
- **Phỏng vấn**: danh sách interview sessions, scorecard từng vòng
- **Ghi chú nội bộ**

### `InterviewScheduleDialog.vue`

- DateTimePicker lịch phỏng vấn
- Select hình thức (trực tiếp / online / điện thoại)
- Input địa điểm / link
- MultiSelect người phỏng vấn (từ danh sách users)
- Gợi ý câu hỏi: hiển thị `interview_questions` theo vị trí (collapsible)

### `ScorecardDialog.vue`

- Danh sách tiêu chí (`scorecard_criteria`) với slider/số điểm
- Rating tổng: Pass / Fail / Hold (radio)
- Textarea ghi chú riêng
- Submit → readonly sau khi đã submit

---

## Cấu trúc file

```
backend/
  alembic/versions/0037_add_recruitment_pipeline.py    ✅ (NEW)
  app/models/recruitment.py                             ✅ (EDIT: thêm pipeline models)
  app/schemas/recruitment.py                            ✅ (EDIT: thêm pipeline schemas
                                                              + ScorecardCriterionUpdate)
  app/services/pipeline_service.py                     ✅ (NEW)
  app/services/interview_service.py                    ✅ (NEW — bao gồm update/delete
                                                              scorecard criterion)
  app/api/v1/endpoints/recruitment.py                  ✅ (EDIT: tất cả pipeline endpoints
                                                              + PUT/DELETE scorecard-criteria)

frontend/
  src/services/recruitmentService.ts                   ✅ (EDIT: thêm pipeline + interview API
                                                              + template/question/criteria CRUD)
  src/views/recruitment/components/PipelineSetupDialog.vue ✅ (NEW)
  src/views/recruitment/KanbanPipelineView.vue         ✅ (NEW)
  src/views/recruitment/ApplicationDetailView.vue      ✅ (NEW)
  src/views/recruitment/components/InterviewScheduleDialog.vue ✅ (NEW)
  src/views/recruitment/components/ScorecardDialog.vue ✅ (NEW)
  src/views/recruitment/components/InterviewKitPanel.vue ✅ (NEW)
  src/views/catalog/RecruitmentCatalogView.vue         ✅ (NEW — quản lý mẫu quy trình,
                                                              câu hỏi PV, tiêu chí chấm điểm)
  src/router/index.ts                                  ✅ (EDIT: thêm route catalog/recruitment
                                                              và recruitment/applications/:id)
  src/components/layout/AppMenu.vue                    ✅ (EDIT: thêm "Danh mục tuyển dụng")
  src/assets/styles/views/_recruitment.scss            ✅ (EDIT: thêm styles cho Kanban,
                                                              PipelineSetup, template picker)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend: Models + Migration ✅
- Migration 0037
- Models: PipelineStageTemplate, PipelineStageTemplateItem, PipelineStage, CandidateStageResult, InterviewSession, InterviewPanelist, InterviewQuestion, ScorecardCriterion

### Slice 2 — Backend: Pipeline Setup + Advance/Reject ✅
- `pipeline_service.py`: setup_pipeline_for_jr, advance_application, hold_application, get_kanban
- Endpoints: pipeline config + advance/hold

### Slice 3 — Backend: Interview + Scorecard ✅
- `interview_service.py`: create_interview, submit_panelist_score, complete_interview, cancel_interview
- Interview endpoints

### Slice 4 — Backend: Interview Kit endpoints ✅
- Endpoints: GET/POST/PUT/DELETE cho `interview_questions` và `scorecard_criteria`
- Schema `ScorecardCriterionUpdate` (bổ sung khi làm Catalog UI)
- Service `update_scorecard_criterion`, `delete_scorecard_criterion` (bổ sung khi làm Catalog UI)

### Slice 5 — Frontend: Quy trình + Kanban ✅
- `PipelineSetupDialog.vue`: chọn mẫu có sẵn hoặc tạo thủ công
- `KanbanPipelineView.vue`: nhúng trong tab “Tuyển chọn”, empty state có CTA “Cấu hình quy trình”
- `JRDetailView.vue`: button “Tuyển chọn” dẫn tới Kanban với `jr_id` pre-selected

### Slice 6 — Frontend: Chi tiết tuyển chọn + Phỏng vấn + Scorecard ✅
- `ApplicationDetailView.vue` (4 tab: Hồ sơ / Pipeline / Phỏng vấn / Ghi chú)
- `InterviewScheduleDialog.vue` + `InterviewKitPanel.vue`
- `ScorecardDialog.vue`

### Ngoài kế hoạch gốc — Danh mục tuyển dụng ✅
- `RecruitmentCatalogView.vue`: quản lý mẫu quy trình, câu hỏi phỏng vấn, tiêu chí chấm điểm
- Route `catalog/recruitment`, menu sidebar “Danh mục tuyển dụng”
- Thuật ngữ UI đã Việt hoá: “pipeline” → “quy trình tuyển chọn”, “template” → “mẫu quy trình”

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| Kéo thả Kanban phức tạp với nhiều ứng viên | Trung bình | Dùng `vuedraggable` hoặc PrimeVue OrderList; fallback: dropdown select stage |
| Pipeline bước mềm dẻo → trạng thái phức tạp | Cao | `current_stage` chỉ là string key; logic advance trong service, không trong model |
| Panelist chưa submit score khi complete interview | Thấp | Cảnh báo nhưng vẫn cho complete; score của người chưa submit = absent |
| Nhiều interview sessions cho 1 bước (lịch lại) | Thấp | Cho phép nhiều session/stage; stage result tính theo session completed gần nhất |
| Scorecard quá phức tạp → không dùng | Trung bình | Scorecard là optional; cho phép submit result mà không điền criteria_scores |
