# Kế hoạch triển khai — 14.1. Tiếp nhận nhân viên mới (Onboarding Checklist)

**Phạm vi:** Checklist tiếp nhận nhân viên mới sau khi convert_to_employee từ Module 13.5  
**Phụ thuộc:** `13.5` (HiringDecision.convert_to_employee) ✅ · `employees` ✅ · `employee_job_records` ✅ · `users` ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §14.1  
**Lưu ý:** Module này là điểm khởi đầu của Chương 14 — toàn bộ 14.2 và 14.3 đều phụ thuộc vào dữ liệu onboarding được tạo ở đây

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `employees` (status=probation, start_date) | ✅ Hoàn thành | Được tạo bởi `hiring_decision_service.convert_to_employee` |
| `employee_job_records` (probation_start_date, probation_end_date) | ✅ Hoàn thành | Gắn kèm khi tạo Employee |
| `hiring_decisions` (hiring_decision_id) | ✅ Hoàn thành | FK tham chiếu sang OnboardingChecklist |
| `document_checklist_service._init_document_checklist` | ✅ Hoàn thành | Khởi tạo hồ sơ pháp lý (Module 13.6), khác với onboarding task |
| `OnboardingTask` (template tasks) | ❌ Chưa có | |
| `OnboardingChecklist` (instance per employee) | ❌ Chưa có | |
| `OnboardingChecklistItem` (task instance) | ❌ Chưa có | |
| `onboarding_service.py` | ❌ Chưa có | |
| API endpoints `/onboarding` | ❌ Chưa có | |
| Frontend | ❌ Chưa có | |

---

## Phạm vi

**Trong phạm vi:**
- Quản lý template các task onboarding (HR cấu hình, admin thêm/sửa/xóa)
- Tự động tạo OnboardingChecklist + items khi nhân viên được convert_to_employee
- Phân công task cho người phụ trách (IT, admin, trưởng bộ phận, buddy)
- Theo dõi trạng thái từng task và tổng thể
- Gán buddy (mentor) cho nhân viên mới
- Danh sách checklist theo phòng ban / trạng thái
- Tích hợp với reminder_service (cảnh báo task quá hạn)

**Ngoài phạm vi:**
- Email notification tự động cho assignee (→ phase sau)
- Mobile app cho nhân viên tự check task
- Quy trình phê duyệt từng task (task chỉ có done/skip, không cần approve)
- Đánh giá thử việc (→ 14.2)
- Báo cáo (→ 14.3)

---

## Thiết kế dữ liệu

### Bảng `onboarding_tasks` (template tasks — HR cấu hình)

```sql
CREATE TABLE onboarding_tasks (
    id                    SERIAL PRIMARY KEY,
    code                  VARCHAR(50) NOT NULL UNIQUE,    -- 'IT_ACCOUNT', 'POLICY_TRAINING', ...
    name                  VARCHAR(200) NOT NULL,           -- "Cấp tài khoản hệ thống"
    description           TEXT,
    -- Nhóm công việc để lọc và phân loại
    -- admin: thủ tục hành chính | it: công nghệ thông tin
    -- training: đào tạo nội bộ | specialty: chuyên môn nghiệp vụ
    group                 VARCHAR(30) NOT NULL DEFAULT 'admin',
    -- Role mặc định phụ trách (nullable: nếu null thì HR tự phân công khi tạo checklist)
    default_assignee_role VARCHAR(100),
    -- Số ngày kể từ start_date của nhân viên (0 = ngay ngày đầu, 7 = cuối tuần đầu)
    due_offset_days       SMALLINT NOT NULL DEFAULT 3,
    sort_order            SMALLINT NOT NULL DEFAULT 0,
    is_active             BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at            TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_onboarding_tasks_group ON onboarding_tasks(group);
CREATE INDEX ix_onboarding_tasks_active ON onboarding_tasks(is_active);
```

**Dữ liệu seed mặc định (8 task tiêu biểu):**

| code | name | group | due_offset_days |
|---|---|---|---|
| `ADMIN_WELCOME` | Gửi email chào mừng & thông tin cần biết | admin | 0 |
| `ADMIN_BADGE` | Làm thẻ nhân viên | admin | 1 |
| `IT_ACCOUNT` | Cấp tài khoản hệ thống (email, Slack, HRMS) | it | 1 |
| `IT_EQUIPMENT` | Bàn giao thiết bị làm việc | it | 1 |
| `TRAINING_POLICY` | Đào tạo nội quy công ty & chính sách | training | 3 |
| `TRAINING_SAFETY` | Đào tạo an toàn lao động | training | 5 |
| `SPECIALTY_INTRO` | Giới thiệu quy trình nghiệp vụ bộ phận | specialty | 5 |
| `BUDDY_INTRO` | Buddy giới thiệu đồng nghiệp và môi trường | specialty | 0 |

### Bảng `onboarding_checklists` (instance per employee)

```sql
CREATE TABLE onboarding_checklists (
    id                  SERIAL PRIMARY KEY,
    employee_id         INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    hiring_decision_id  INTEGER REFERENCES hiring_decisions(id) ON DELETE SET NULL,  -- nullable: có thể tạo thủ công
    buddy_user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,  -- mentor
    -- in_progress: đang thực hiện | completed: hoàn thành tất cả | cancelled: hủy
    status              VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    -- completion_pct: tính on-the-fly; lưu cache để query nhanh
    completion_pct      NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    created_by_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (employee_id)  -- mỗi nhân viên chỉ có 1 checklist onboarding
);

CREATE INDEX ix_onboarding_checklists_status ON onboarding_checklists(status);
CREATE INDEX ix_onboarding_checklists_employee ON onboarding_checklists(employee_id);
```

### Bảng `onboarding_checklist_items` (task instance)

```sql
CREATE TABLE onboarding_checklist_items (
    id              SERIAL PRIMARY KEY,
    checklist_id    INTEGER NOT NULL REFERENCES onboarding_checklists(id) ON DELETE CASCADE,
    task_id         INTEGER NOT NULL REFERENCES onboarding_tasks(id) ON DELETE RESTRICT,
    assignee_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,  -- người phụ trách cụ thể
    due_date        DATE NOT NULL,        -- = employee.start_date + task.due_offset_days
    completed_at    TIMESTAMP,           -- NULL = chưa hoàn thành
    -- pending: chưa bắt đầu | in_progress: đang làm | done: hoàn thành | skipped: bỏ qua
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    note            TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (checklist_id, task_id)  -- mỗi task chỉ xuất hiện 1 lần trong checklist
);

CREATE INDEX ix_onboarding_items_checklist ON onboarding_checklist_items(checklist_id);
CREATE INDEX ix_onboarding_items_assignee ON onboarding_checklist_items(assignee_user_id);
CREATE INDEX ix_onboarding_items_due_date ON onboarding_checklist_items(due_date);
CREATE INDEX ix_onboarding_items_status ON onboarding_checklist_items(status);
```

### Alembic migration

File: `0045_add_onboarding_checklist.py`

```python
# Tạo: onboarding_tasks, onboarding_checklists, onboarding_checklist_items
# Seed: 8 task template mặc định (INSERT INTO onboarding_tasks)
# Depends on: 0044_add_hold_email_template.py
```

---

## API Design

### Onboarding Checklist

```
GET    /onboarding?status=&department_id=&days_until_completion=&page=&page_size=
       → Page[OnboardingChecklistListItem]
       -- Lọc: status (in_progress|completed|cancelled), department_id, days_until_completion (filter còn <= N ngày)

POST   /onboarding
       body: { employee_id, hiring_decision_id?, buddy_user_id? }
       → OnboardingChecklistRead
       -- Tự động populate items từ tất cả OnboardingTask.is_active=True
       -- Tự động tính due_date = employee.start_date + task.due_offset_days

GET    /onboarding/{id}
       → OnboardingChecklistRead (kèm items đầy đủ)

PATCH  /onboarding/{id}
       body: { buddy_user_id?, status? }  -- HR cập nhật buddy hoặc cancel checklist
       → OnboardingChecklistRead

PATCH  /onboarding/{id}/items/{item_id}
       body: { status, assignee_user_id?, note? }
       → OnboardingChecklistItemRead
       -- Sau khi update item → recompute completion_pct của checklist
       -- Nếu tất cả items done/skipped → tự động set checklist.status = 'completed'
```

### Onboarding Task Templates (Admin)

```
GET    /onboarding/tasks?is_active=&group=
       → List[OnboardingTaskRead]
       -- Sắp xếp theo group, sort_order

POST   /onboarding/tasks
       body: { code, name, description?, group, default_assignee_role?, due_offset_days, sort_order? }
       → OnboardingTaskRead

PUT    /onboarding/tasks/{id}
       body: { name?, description?, group?, default_assignee_role?, due_offset_days?, sort_order?, is_active? }
       → OnboardingTaskRead

DELETE /onboarding/tasks/{id}
       -- Chỉ xóa được nếu không có item nào đang dùng task này
       -- Nếu đã có item: chỉ set is_active=False (soft delete)
```

### Permissions

| Action | Permission |
|---|---|
| Xem checklist | `employees:view` |
| Tạo/sửa checklist, cập nhật item | `employees:edit` |
| Quản lý task template | `employees:manage` (hoặc `hr:manage`) |

---

## Schemas (Pydantic)

```python
class OnboardingTaskRead(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    group: str           # admin | it | training | specialty
    default_assignee_role: Optional[str]
    due_offset_days: int
    sort_order: int
    is_active: bool
    created_at: datetime

class OnboardingTaskCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    group: str                    # phải là 1 trong: admin|it|training|specialty
    default_assignee_role: Optional[str] = None
    due_offset_days: int = 3      # default 3 ngày
    sort_order: int = 0

class OnboardingChecklistItemRead(BaseModel):
    id: int
    checklist_id: int
    task_id: int
    task_code: str
    task_name: str
    task_group: str
    assignee_user_id: Optional[int]
    assignee_name: Optional[str]
    due_date: date
    completed_at: Optional[datetime]
    status: str         # pending | in_progress | done | skipped
    note: Optional[str]
    is_overdue: bool    # computed: due_date < today AND status NOT IN ['done','skipped']
    created_at: datetime
    updated_at: datetime

class OnboardingChecklistItemUpdate(BaseModel):
    status: str                           # pending | in_progress | done | skipped
    assignee_user_id: Optional[int] = None
    note: Optional[str] = None

class OnboardingChecklistRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    department_name: Optional[str]
    start_date: date
    hiring_decision_id: Optional[int]
    buddy_user_id: Optional[int]
    buddy_name: Optional[str]
    status: str          # in_progress | completed | cancelled
    completion_pct: float
    items: List[OnboardingChecklistItemRead]
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

class OnboardingChecklistCreate(BaseModel):
    employee_id: int
    hiring_decision_id: Optional[int] = None
    buddy_user_id: Optional[int] = None

class OnboardingChecklistListItem(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    department_name: Optional[str]
    start_date: date
    buddy_name: Optional[str]
    status: str
    completion_pct: float
    total_items: int
    done_items: int
    overdue_items: int
    days_since_start: int        # today - employee.start_date
```

---

## Service Logic — `onboarding_service.py`

### `create_checklist(session, employee_id, hiring_decision_id?, buddy_user_id?, created_by_id) → OnboardingChecklistRead`

1. Kiểm tra employee tồn tại; raise 404 nếu không.
2. Kiểm tra UNIQUE: nếu đã có checklist cho employee này → raise 409 "Nhân viên đã có checklist onboarding".
3. Tạo `OnboardingChecklist` với `status='in_progress'`, `completion_pct=0`.
4. Query tất cả `OnboardingTask` có `is_active=True`, order by `sort_order`.
5. Với mỗi task: tạo `OnboardingChecklistItem`:
   - `due_date = employee.start_date + timedelta(days=task.due_offset_days)`
   - `status = 'pending'`
   - `assignee_user_id = None` (HR phân công sau, hoặc dùng default_assignee_role để lookup sau)
6. `session.flush()` → trả về checklist với items.

### `update_item_status(session, item_id, data: OnboardingChecklistItemUpdate, user_id) → OnboardingChecklistItemRead`

1. Get item, raise 404 nếu không.
2. Update: `status`, `note`, `assignee_user_id` (nếu có).
3. Nếu `status == 'done'`: set `completed_at = utcnow()`.
4. Nếu `status != 'done'`: set `completed_at = None`.
5. Recompute `completion_pct`:
   - `total = COUNT(items WHERE status != 'skipped')`
   - `done = COUNT(items WHERE status = 'done')`
   - `pct = done / total * 100` nếu `total > 0` else `0`
6. Nếu `ALL items status IN ['done', 'skipped']`: set `checklist.status = 'completed'`.
7. Update `checklist.completion_pct`, `checklist.updated_at`.

### `get_overdue_items(session) → List[OverdueChecklistItem]`

Query: `onboarding_checklist_items` JOIN `onboarding_checklists` WHERE:
- `items.due_date < today`
- `items.status NOT IN ('done', 'skipped')`
- `checklists.status = 'in_progress'`

Dùng bởi `reminder_service` hoặc scheduled job để gửi cảnh báo.

### Auto-trigger từ `hiring_decision_service.convert_to_employee`

Sau khi `employee_service.create_employee(session, payload)` thành công (dòng ~263 trong `hiring_decision_service.py`), thêm:

```python
from app.services.onboarding_service import create_checklist as _create_onboarding
await _create_onboarding(
    session,
    employee_id=emp.id,
    hiring_decision_id=decision_id,
    created_by_id=user_id,
)
```

**Lưu ý:** Nếu tạo onboarding checklist thất bại (ví dụ không có task nào active), KHÔNG rollback toàn bộ convert_to_employee. Log warning và tiếp tục.

### `list_checklists(session, status?, department_id?, days_until_completion?, page, page_size) → Page[OnboardingChecklistListItem]`

JOIN: `onboarding_checklists` → `employees` → `employee_job_records` (is_current=True) → `departments`

Filter:
- `status`: lọc theo `onboarding_checklists.status`
- `department_id`: lọc theo `employee_job_records.department_id`
- `days_until_completion`: tính ngày kết thúc thử việc từ `employee_job_records.probation_end_date`, filter `days <= N`

Computed fields (subquery):
- `total_items = COUNT(items)`
- `done_items = COUNT(items WHERE status='done')`
- `overdue_items = COUNT(items WHERE due_date < today AND status NOT IN ['done','skipped'])`

---

## Thiết kế Frontend

### Route mới

```typescript
// Thêm vào router/index.ts
{
  path: 'employees/onboarding',
  name: 'onboarding-list',
  component: () => import('@/views/employees/OnboardingListView.vue'),
  meta: { title: 'Tiếp nhận nhân viên mới' },
},
{
  path: 'employees/onboarding/tasks',
  name: 'onboarding-tasks',
  component: () => import('@/views/employees/OnboardingTaskConfigView.vue'),
  meta: { title: 'Cấu hình task onboarding' },
},
{
  path: 'employees/onboarding/:employee_id',
  name: 'onboarding-detail',
  component: () => import('@/views/employees/OnboardingDetailView.vue'),
  meta: { title: 'Chi tiết onboarding' },
},
```

### Menu item cần thêm (`AppMenu.vue`)

Thêm vào nhóm "Nhân sự" (hiện là single item `{ to: '/employees', label: 'Nhân sự', icon: 'pi-users' }`). Cần convert sang group với items:

```typescript
{
  label: 'Nhân sự',
  icon: 'pi-users',
  items: [
    { to: '/employees', label: 'Danh sách nhân viên' },
    { to: '/employees/onboarding', label: 'Tiếp nhận nhân viên mới', icon: 'pi-clipboard' },
  ]
}
```

### `OnboardingListView.vue` (route `/employees/onboarding`)

**Breadcrumb:** `Nhân viên > Tiếp nhận nhân viên mới`

**Toolbar:**
- Select Status (Đang thực hiện / Hoàn thành / Đã hủy / Tất cả)
- Select Phòng ban
- Input số ngày còn lại (filter days_until_completion)
- Button "Tạo checklist thủ công" → mở `OnboardingCreateDialog.vue`
- Button "Cấu hình task" → link sang `/employees/onboarding/tasks`

**DataTable:**

| Cột | Nội dung |
|---|---|
| Nhân viên | `employee_name` + `employee_code` (badge) |
| Phòng ban | `department_name` |
| Ngày vào làm | `start_date` |
| Buddy | `buddy_name` hoặc `—` |
| Tiến độ | ProgressBar `completion_pct` + `done_items/total_items` |
| Task quá hạn | Badge đỏ `overdue_items` nếu > 0 |
| Trạng thái | Tag: in_progress (warn) / completed (success) / cancelled (danger) |
| Thao tác | Button "Xem chi tiết" |

### `OnboardingDetailView.vue` (route `/employees/onboarding/:employee_id`)

**Breadcrumb:** `Nhân viên > Tiếp nhận nhân viên mới > {employee_name}`

**Header card:**
- Tên nhân viên, mã NV, phòng ban, ngày vào làm
- Buddy: Select user (HR cập nhật được)
- ProgressBar tổng thể `completion_pct`
- Trạng thái checklist (Tag)

**DataTable items — group by task.group:**

| Cột | Nội dung |
|---|---|
| Task | `task_name` |
| Nhóm | Badge: Admin / IT / Đào tạo / Chuyên môn |
| Phụ trách | Select User (inline editable) |
| Hạn hoàn thành | `due_date` — màu đỏ nếu `is_overdue=true` |
| Trạng thái | Dropdown inline: Chờ / Đang làm / Xong / Bỏ qua |
| Ghi chú | Input text inline |
| Hoàn thành lúc | `completed_at` (hiển thị khi status=done) |

**Action buttons:**
- "Đánh dấu tất cả hoàn thành" → PATCH batch (bulk update)
- "Hủy checklist" → PATCH checklist status=cancelled (require confirm)

### `OnboardingCreateDialog.vue`

**Fields:**
- Select Nhân viên (required) — chỉ hiện nhân viên status=probation chưa có checklist
- Select Buddy (optional) — Select user
- Hiring Decision ID (auto-fill nếu có, không cần hiển thị)
- Button "Tạo" → POST /onboarding

### `OnboardingTaskConfigView.vue` (route `/employees/onboarding/tasks`)

**Breadcrumb:** `Nhân viên > Tiếp nhận nhân viên mới > Cấu hình task`

DataTable các task templates, inline edit, toggle is_active, thêm task mới, reorder sort_order.

---

## Cấu trúc file

```
backend/
  alembic/versions/0045_add_onboarding_checklist.py    (NEW)
  app/models/onboarding.py                              (NEW: OnboardingTask, OnboardingChecklist, OnboardingChecklistItem)
  app/schemas/onboarding.py                             (NEW)
  app/services/onboarding_service.py                    (NEW)
  app/api/v1/endpoints/onboarding.py                    (NEW)
  app/api/v1/router.py                                  (EDIT: include onboarding router)
  app/services/hiring_decision_service.py               (EDIT: gọi create_checklist sau convert_to_employee)
  tests/test_onboarding.py                              (NEW)

frontend/
  src/services/onboardingService.ts                     (NEW)
  src/views/employees/OnboardingListView.vue            (NEW)
  src/views/employees/OnboardingDetailView.vue          (NEW)
  src/views/employees/OnboardingTaskConfigView.vue      (NEW)
  src/views/employees/OnboardingCreateDialog.vue        (NEW)
  src/router/index.ts                                   (EDIT: thêm 3 routes onboarding)
  src/components/layout/AppMenu.vue                     (EDIT: convert Nhân sự sang group, thêm submenu)
```

---

## Kế hoạch theo Slice

### Slice 1 — DB migration + seed tasks
- `0045_add_onboarding_checklist.py`: tạo 3 bảng
- Seed 8 task template mặc định
- Model file `app/models/onboarding.py`
- **Deliverable:** Migration chạy thành công, seed data có thể query

### Slice 2 — Service + Core API
- `onboarding_service.py`: `create_checklist`, `update_item_status`, `list_checklists`, `get_checklist_detail`, `get_overdue_items`
- Schemas `app/schemas/onboarding.py`
- Endpoints: `GET /onboarding`, `POST /onboarding`, `GET /onboarding/{id}`, `PATCH /onboarding/{id}/items/{item_id}`
- **Deliverable:** Có thể tạo checklist thủ công qua API, update item, kiểm tra completion_pct

### Slice 3 — Auto-trigger + Admin Task API
- Edit `hiring_decision_service.convert_to_employee`: thêm call `create_checklist` sau tạo employee
- Endpoints: `GET /onboarding/tasks`, `POST /onboarding/tasks`, `PUT /onboarding/tasks/{id}`, `DELETE /onboarding/tasks/{id}`
- Tests: `tests/test_onboarding.py` — test convert_to_employee tự động tạo checklist
- **Deliverable:** Convert ứng viên → nhân viên tự sinh checklist; HR có thể cấu hình task template

### Slice 4 — Frontend: List view
- `onboardingService.ts`: API calls
- `OnboardingListView.vue`: DataTable + filters + toolbar
- `OnboardingCreateDialog.vue`: form tạo thủ công
- Router + AppMenu update
- **Deliverable:** HR xem danh sách, tạo checklist, filter theo status/phòng ban

### Slice 5 — Frontend: Detail view + Task config
- `OnboardingDetailView.vue`: header card, DataTable items, inline status update, buddy select
- `OnboardingTaskConfigView.vue`: quản lý template tasks
- **Deliverable:** HR click vào nhân viên, thấy checklist, cập nhật từng task inline

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| `convert_to_employee` rollback khi không có task nào active | Thấp | Wrap `create_checklist` trong try/except; log warning, KHÔNG raise nếu không có task (tạo checklist trống) |
| Race condition: tạo 2 checklist cùng lúc cho 1 nhân viên | Thấp | UNIQUE constraint `(employee_id)` trên DB sẽ throw IntegrityError; bắt và trả 409 |
| completion_pct không cập nhật khi item bị xóa | Thấp | Không cho xóa item (chỉ skip); recompute mỗi lần update item |
| Nhân viên không có start_date → due_date không tính được | Thấp | Kiểm tra `employee.start_date` khi tạo checklist; raise 422 nếu thiếu |
| Task template bị xóa sau khi đã có checklist item | Trung bình | FK `REFERENCES onboarding_tasks ON DELETE RESTRICT`; khi xóa task → kiểm tra item; nếu có → set is_active=False thay vì xóa |
| Menu Nhân sự hiện là single item, cần convert sang group | Thấp | Sửa AppMenu.vue: thay `{ to, label, icon }` bằng `{ label, icon, items: [...] }`; test routing không bị break |
