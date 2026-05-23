# Kế hoạch triển khai — 9.1. Quản lý khóa học

**Phạm vi:** Danh mục khóa học/chương trình đào tạo · Kế hoạch đào tạo theo năm/quý  
**Phụ thuộc:** Không có phụ thuộc module trước  
**Căn cứ nghiệp vụ:** FEATURES.md §9.1

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `training_courses` table | ❌ Chưa có | |
| `training_plans` table | ❌ Chưa có | |
| `training_plan_courses` table | ❌ Chưa có | |
| API danh mục khóa học | ❌ Chưa có | |
| API kế hoạch đào tạo | ❌ Chưa có | |
| `TrainingView.vue` | ⚠️ Placeholder | Chưa có nội dung thực |

---

## Phạm vi

Theo FEATURES.md §9.1:
> Danh mục khóa học/chương trình đào tạo: tên, loại, thời lượng, đơn vị tổ chức  
> Loại đào tạo: Nội bộ, Bên ngoài, Online  
> Kế hoạch đào tạo theo năm/quý

---

## Thiết kế dữ liệu

### Bảng `training_courses` (danh mục khóa học)

| Cột | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `code` | VARCHAR(50) | UNIQUE NOT NULL | Mã khóa học |
| `name` | VARCHAR(500) | NOT NULL | Tên khóa học |
| `course_type` | VARCHAR(20) | NOT NULL, CHECK | `noi_bo` \| `ben_ngoai` \| `online` |
| `duration_hours` | SMALLINT | nullable | Số giờ đào tạo |
| `organizer` | VARCHAR(200) | nullable | Đơn vị tổ chức |
| `description` | TEXT | nullable | Mô tả chi tiết |
| `cost_per_person` | NUMERIC(15,2) | nullable | Chi phí/người (VND) |
| `is_mandatory` | BOOLEAN | NOT NULL DEFAULT false | Đào tạo bắt buộc |
| `is_active` | BOOLEAN | NOT NULL DEFAULT true | Trạng thái hoạt động |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**Indexes:** `(code)` UNIQUE, `(course_type)`, `(is_active)`

### Bảng `training_plans` (kế hoạch đào tạo)

| Cột | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `title` | VARCHAR(500) | NOT NULL | Tiêu đề kế hoạch |
| `year` | SMALLINT | NOT NULL | Năm kế hoạch |
| `quarter` | SMALLINT | nullable, CHECK 1–4 | Quý (NULL = cả năm) |
| `department_id` | INT | FK departments SET NULL, nullable | NULL = toàn công ty |
| `description` | TEXT | nullable | Mô tả |
| `status` | VARCHAR(20) | NOT NULL DEFAULT `draft`, CHECK | `draft` \| `approved` \| `cancelled` |
| `created_by_id` | INT | FK users SET NULL, nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**Indexes:** `(year)`, `(department_id)`, `(status)`, `(year, quarter)`

### Bảng `training_plan_courses` (liên kết plan ↔ course)

| Cột | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `plan_id` | INT | FK training_plans CASCADE NOT NULL | |
| `course_id` | INT | FK training_courses RESTRICT NOT NULL | |
| `target_count` | SMALLINT | nullable | Số NV dự kiến tham gia |
| `scheduled_date` | DATE | nullable | Ngày dự kiến tổ chức |
| `note` | TEXT | nullable | Ghi chú |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**Constraints:** UNIQUE(`plan_id`, `course_id`)  
**Indexes:** `(plan_id)`, `(course_id)`

---

## Thiết kế API

### Danh mục khóa học

```
GET    /training/courses
       ?search=&course_type=&is_mandatory=&is_active=&page=&page_size=
       → CourseListPage

POST   /training/courses
       body: CourseCreate
       → CourseRead

GET    /training/courses/{id}
       → CourseRead

PUT    /training/courses/{id}
       body: CourseUpdate
       → CourseRead

DELETE /training/courses/{id}
       → 204 No Content
       Logic: soft-delete (set is_active=false) nếu có record liên kết;
              hard-delete nếu chưa có liên kết nào
```

### Kế hoạch đào tạo

```
GET    /training/plans
       ?year=&quarter=&department_id=&status=&page=&page_size=
       → PlanListPage

POST   /training/plans
       body: PlanCreate
       → PlanRead

GET    /training/plans/{id}
       → PlanReadDetail (include courses list)

PUT    /training/plans/{id}
       body: PlanUpdate  (chỉ fields header, không đổi status)
       → PlanRead

DELETE /training/plans/{id}
       → 204 No Content  (chỉ khi status = draft)

POST   /training/plans/{id}/approve
       → PlanRead  (status: draft → approved)

POST   /training/plans/{id}/cancel
       → PlanRead  (status: draft | approved → cancelled)
```

### Courses trong plan

```
GET    /training/plans/{id}/courses
       → list[PlanCourseRead]

POST   /training/plans/{id}/courses
       body: PlanCourseCreate
       → PlanCourseRead

PUT    /training/plans/{id}/courses/{course_id}
       body: PlanCourseUpdate
       → PlanCourseRead

DELETE /training/plans/{id}/courses/{course_id}
       → 204 No Content
```

---

## Permissions

| Permission | Mô tả |
|---|---|
| `training:view` | Xem danh mục khóa học và kế hoạch |
| `training:manage_courses` | CRUD danh mục khóa học |
| `training:manage_plans` | CRUD kế hoạch đào tạo, approve, cancel |

---

## Schemas

### Danh mục khóa học

```python
class CourseRead(BaseModel):
    id: int
    code: str
    name: str
    course_type: str
    course_type_label: str          # "Nội bộ" | "Bên ngoài" | "Online"
    duration_hours: int | None
    organizer: str | None
    description: str | None
    cost_per_person: Decimal | None
    is_mandatory: bool
    is_active: bool
    created_at: datetime

class CourseCreate(BaseModel):
    code: str
    name: str
    course_type: str                # noi_bo | ben_ngoai | online
    duration_hours: int | None = None
    organizer: str | None = None
    description: str | None = None
    cost_per_person: Decimal | None = None
    is_mandatory: bool = False

class CourseUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    course_type: str | None = None
    duration_hours: int | None = None
    organizer: str | None = None
    description: str | None = None
    cost_per_person: Decimal | None = None
    is_mandatory: bool | None = None
    is_active: bool | None = None

class CourseListPage(BaseModel):
    items: list[CourseRead]
    total: int
    page: int
    page_size: int
```

### Courses trong plan

```python
class PlanCourseRead(BaseModel):
    id: int
    plan_id: int
    course_id: int
    course_code: str
    course_name: str
    course_type_label: str
    duration_hours: int | None
    target_count: int | None
    scheduled_date: date | None
    note: str | None

class PlanCourseCreate(BaseModel):
    course_id: int
    target_count: int | None = None
    scheduled_date: date | None = None
    note: str | None = None

class PlanCourseUpdate(BaseModel):
    target_count: int | None = None
    scheduled_date: date | None = None
    note: str | None = None
```

### Kế hoạch đào tạo

```python
class PlanRead(BaseModel):
    id: int
    title: str
    year: int
    quarter: int | None
    department_id: int | None
    department_name: str | None
    status: str
    status_label: str               # "Dự thảo" | "Đã duyệt" | "Đã hủy"
    description: str | None
    created_by_name: str | None
    created_at: datetime
    course_count: int               # computed: số khóa học trong plan

class PlanReadDetail(PlanRead):
    courses: list[PlanCourseRead]

class PlanCreate(BaseModel):
    title: str
    year: int
    quarter: int | None = None      # 1–4 hoặc None
    department_id: int | None = None
    description: str | None = None

class PlanUpdate(BaseModel):
    title: str | None = None
    description: str | None = None

class PlanListPage(BaseModel):
    items: list[PlanRead]
    total: int
    page: int
    page_size: int
```

**Status labels:**
- `draft` → "Dự thảo"
- `approved` → "Đã duyệt"
- `cancelled` → "Đã hủy"

**Course type labels:**
- `noi_bo` → "Nội bộ"
- `ben_ngoai` → "Bên ngoài"
- `online` → "Online"

---

## Service logic

### `training_course_service.py`

- **`get_courses()`**: SELECT với filter `course_type`, `is_mandatory`, `is_active`; ILIKE search trên `code`, `name`, `organizer`; phân trang
- **`get_course_or_404()`**: `_get_or_404` theo id
- **`create_course()`**: kiểm tra `code` trùng lặp → raise 400; insert; trả CourseRead
- **`update_course()`**: `_get_or_404`; kiểm tra `code` nếu thay đổi; update fields; trả CourseRead
- **`delete_course()`**: `_get_or_404`; kiểm tra có `training_plan_courses` hoặc `employee_training_records` liên kết không; nếu có → soft-delete (`is_active=false`); nếu không → hard-delete

### `training_plan_service.py`

- **`get_plans()`**: SELECT JOIN departments (left) với filter `year`, `quarter`, `department_id`, `status`; subquery COUNT courses; phân trang
- **`get_plan_or_404()`**: `_get_or_404` theo id
- **`get_plan_detail()`**: lấy plan + JOIN plan_courses JOIN courses; trả PlanReadDetail
- **`create_plan()`**: validate `department_id` tồn tại nếu có; insert với `status=draft`; trả PlanRead
- **`update_plan()`**: `_get_or_404`; chỉ update `title`, `description` (không update status ở đây); trả PlanRead
- **`delete_plan()`**: `_get_or_404`; kiểm tra `status == draft` → nếu không raise 400; xóa plan_courses trước (CASCADE), xóa plan
- **`approve_plan()`**: `_get_or_404`; kiểm tra `status == draft` → nếu không raise 400; set `status=approved`
- **`cancel_plan()`**: `_get_or_404`; kiểm tra `status in (draft, approved)` → nếu không raise 400; set `status=cancelled`
- **`add_course_to_plan()`**: kiểm tra plan không bị cancelled; kiểm tra `course_id` tồn tại; kiểm tra UNIQUE → raise 409 nếu đã có; insert plan_course
- **`update_plan_course()`**: tìm record theo `(plan_id, course_id)`; update fields
- **`remove_course_from_plan()`**: tìm record theo `(plan_id, course_id)` → 404 nếu không có; xóa

---

## Migration

**File:** `alembic/versions/0027_create_training_courses_plans.py`

```python
op.create_table(
    "training_courses",
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("code", sa.String(50), unique=True, nullable=False),
    sa.Column("name", sa.String(500), nullable=False),
    sa.Column("course_type", sa.String(20), nullable=False),
    sa.Column("duration_hours", sa.SmallInteger, nullable=True),
    sa.Column("organizer", sa.String(200), nullable=True),
    sa.Column("description", sa.Text, nullable=True),
    sa.Column("cost_per_person", sa.Numeric(15, 2), nullable=True),
    sa.Column("is_mandatory", sa.Boolean, nullable=False, server_default="false"),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.func.now()),
    sa.Column("updated_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.func.now()),
    sa.CheckConstraint("course_type IN ('noi_bo','ben_ngoai','online')", name="ck_training_courses_type"),
)

op.create_table(
    "training_plans",
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("title", sa.String(500), nullable=False),
    sa.Column("year", sa.SmallInteger, nullable=False),
    sa.Column("quarter", sa.SmallInteger, nullable=True),
    sa.Column("department_id", sa.Integer, sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
    sa.Column("description", sa.Text, nullable=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
    sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.func.now()),
    sa.Column("updated_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.func.now()),
    sa.CheckConstraint("quarter BETWEEN 1 AND 4 OR quarter IS NULL", name="ck_training_plans_quarter"),
    sa.CheckConstraint("status IN ('draft','approved','cancelled')", name="ck_training_plans_status"),
)

op.create_table(
    "training_plan_courses",
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("plan_id", sa.Integer, sa.ForeignKey("training_plans.id", ondelete="CASCADE"), nullable=False),
    sa.Column("course_id", sa.Integer, sa.ForeignKey("training_courses.id", ondelete="RESTRICT"), nullable=False),
    sa.Column("target_count", sa.SmallInteger, nullable=True),
    sa.Column("scheduled_date", sa.Date, nullable=True),
    sa.Column("note", sa.Text, nullable=True),
    sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.func.now()),
    sa.UniqueConstraint("plan_id", "course_id", name="uq_training_plan_courses"),
)

# Indexes
op.create_index("ix_training_courses_type", "training_courses", ["course_type"])
op.create_index("ix_training_courses_active", "training_courses", ["is_active"])
op.create_index("ix_training_plans_year", "training_plans", ["year"])
op.create_index("ix_training_plans_dept", "training_plans", ["department_id"])
op.create_index("ix_training_plans_status", "training_plans", ["status"])
op.create_index("ix_training_plan_courses_plan", "training_plan_courses", ["plan_id"])
op.create_index("ix_training_plan_courses_course", "training_plan_courses", ["course_id"])
```

---

## Thiết kế Frontend

### `TrainingView.vue` (EDIT — thay thế placeholder)

Cấu trúc với 2 tabs:
- **Tab "Khóa học"** → `CourseListTab.vue`
- **Tab "Kế hoạch"** → `TrainingPlanTab.vue`

Dùng `<TabView>` của PrimeVue v4.

---

### `CourseListTab.vue`

**Toolbar:**
- `InputText` placeholder "Tìm mã, tên, đơn vị tổ chức..." → debounce search
- `Select` "Loại đào tạo" (filter prop): Tất cả / Nội bộ / Bên ngoài / Online
- `Select` "Bắt buộc" (filter prop): Tất cả / Có / Không
- `Select` "Trạng thái" (filter prop): Tất cả / Đang hoạt động / Ngừng hoạt động
- Button "Thêm khóa học" (chỉ hiện với `training:manage_courses`)

**DataTable:**
| Cột | Hiển thị |
|---|---|
| STT | index + 1 |
| Mã KH | `code` |
| Tên khóa học | `name` |
| Loại | `<Tag>` với severity: noi_bo→info, ben_ngoai→warn, online→success |
| Thời lượng | `duration_hours` + "giờ" (nếu có) |
| Đơn vị tổ chức | `organizer` |
| Chi phí/người | format VND |
| Bắt buộc | `<Checkbox>` readonly |
| Trạng thái | `<Tag>` Hoạt động/Ngừng |
| Thao tác | nút Sửa, Xóa |

**Dialog "Thêm / Sửa khóa học":**
- `InputText`: Mã khóa học (required), Tên khóa học (required)
- `Select` (filter): Loại đào tạo (required)
- `InputNumber`: Số giờ, Chi phí/người
- `InputText`: Đơn vị tổ chức
- `Textarea`: Mô tả
- `Checkbox`: Đào tạo bắt buộc, Đang hoạt động
- Validation: code required, name required, course_type required

---

### `TrainingPlanTab.vue`

**Toolbar:**
- `InputNumber` "Năm": filter theo year (default năm hiện tại)
- `Select` "Quý" (filter prop): Tất cả / Q1 / Q2 / Q3 / Q4
- `Select` "Phòng ban" (filter prop): load từ API departments
- `Select` "Trạng thái" (filter prop): Tất cả / Dự thảo / Đã duyệt / Đã hủy
- Button "Tạo kế hoạch" (chỉ hiện với `training:manage_plans`)

**DataTable:**
| Cột | Hiển thị |
|---|---|
| Tiêu đề kế hoạch | `title` |
| Năm/Quý | e.g. "2026 - Q2" hoặc "2026 (Cả năm)" |
| Phòng ban | `department_name` hoặc "Toàn công ty" |
| Số khóa học | `course_count` |
| Trạng thái | `<Tag>` draft→secondary, approved→success, cancelled→danger |
| Thao tác | nút Xem chi tiết, Duyệt, Hủy, Xóa |

**Side panel / ExpandedRow chi tiết kế hoạch:**
- Danh sách courses trong plan: DataTable nhỏ (tên KH, loại, số giờ, số NV dự kiến, ngày dự kiến, ghi chú)
- Button "Thêm khóa học vào kế hoạch" (chỉ khi status = draft, có quyền manage_plans)
- Nút xóa từng course khỏi plan

**Dialog "Tạo kế hoạch":**
- `InputText`: Tiêu đề (required)
- `InputNumber`: Năm (required, default năm hiện tại)
- `Select` (filter): Quý (optional)
- `Select` (filter): Phòng ban (optional, default = null = toàn công ty)
- `Textarea`: Mô tả

**Dialog "Thêm khóa học vào kế hoạch":**
- `Select` (filter): Chọn khóa học (required) — load danh sách `is_active=true`
- `InputNumber`: Số NV dự kiến
- `DatePicker`: Ngày dự kiến tổ chức
- `Textarea`: Ghi chú

---

### CSS

**File:** `frontend/src/assets/styles/views/_training.scss`

```scss
.training-view {
  .course-type-tag { /* spacing overrides nếu cần */ }

  .plan-detail-courses {
    margin-top: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--surface-50);
    border-radius: 6px;

    .dark-mode & {
      background: var(--surface-800);
    }
  }

  .plan-year-quarter {
    font-size: 0.875rem;
    color: var(--text-color-secondary);
  }
}
```

Đăng ký trong `main.scss` (hoặc global SCSS entry point):
```scss
@use './views/training';   // hoặc @import
```

---

## Cấu trúc file mới / thay đổi

```
backend/
  alembic/versions/0027_create_training_courses_plans.py  (NEW)
  app/models/training.py                                   (NEW)
  app/models/__init__.py                                   (EDIT: add import)
  app/schemas/training.py                                  (NEW)
  app/services/training_course_service.py                  (NEW)
  app/services/training_plan_service.py                    (NEW)
  app/api/v1/endpoints/training.py                         (NEW)
  app/api/v1/router.py                                     (EDIT: include training router)

frontend/
  src/services/trainingService.ts                          (NEW)
  src/views/training/TrainingView.vue                      (EDIT: replace placeholder)
  src/views/training/components/CourseListTab.vue          (NEW)
  src/views/training/components/TrainingPlanTab.vue        (NEW)
  src/assets/styles/views/_training.scss                   (NEW)
```

---

## Kế hoạch theo slice

### Slice 1 — Backend: Danh mục khóa học

**Tasks:**
1. Migration `0027_create_training_courses_plans.py` — tạo đủ 3 bảng (chạy luôn để có schema cho slice 2)
2. Model `app/models/training.py`: `TrainingCourse`, `TrainingPlan`, `TrainingPlanCourse`
3. Cập nhật `app/models/__init__.py` import các model mới
4. Schema `app/schemas/training.py`: `CourseRead`, `CourseCreate`, `CourseUpdate`, `CourseListPage`
5. Service `training_course_service.py`: `get_courses`, `get_course_or_404`, `create_course`, `update_course`, `delete_course`
6. Endpoint `app/api/v1/endpoints/training.py`: CRUD `/training/courses` với permission guards
7. Cập nhật `app/api/v1/router.py`

**Exit criteria:**
- `GET /training/courses` trả danh sách phân trang, filter hoạt động
- `POST /training/courses` tạo thành công, validate `course_type` đúng
- `PUT /training/courses/{id}` cập nhật đúng
- `DELETE /training/courses/{id}`: hard-delete khi chưa có liên kết; soft-delete khi đã có liên kết
- Duplicate `code` → 400
- Sai `course_type` → 422

---

### Slice 2 — Backend: Kế hoạch đào tạo

**Tasks:**
1. Schema bổ sung: `PlanCourseRead`, `PlanCourseCreate`, `PlanCourseUpdate`, `PlanRead`, `PlanReadDetail`, `PlanCreate`, `PlanUpdate`, `PlanListPage`
2. Service `training_plan_service.py`: đầy đủ các method (get, create, update, delete, approve, cancel, add_course, update_plan_course, remove_course)
3. Bổ sung endpoints vào `training.py`:
   - CRUD `/training/plans`
   - `POST /training/plans/{id}/approve`
   - `POST /training/plans/{id}/cancel`
   - CRUD `/training/plans/{id}/courses`

**Exit criteria:**
- CRUD plans hoạt động; `GET /training/plans/{id}` trả `courses` list
- `approve` chỉ từ `draft` → `approved`; `cancel` từ `draft`/`approved` → `cancelled`
- `DELETE /training/plans/{id}` chỉ hoạt động khi status = `draft`
- Thêm course trùng vào plan → 409
- Course bị RESTRICT không xóa được khi đang có plan_courses

---

### Slice 3 — Frontend

**Tasks:**
1. `trainingService.ts`: types (CourseRead, PlanRead, PlanReadDetail, ...) + API calls cho tất cả endpoints
2. `TrainingView.vue`: replace placeholder bằng TabView 2 tabs
3. `CourseListTab.vue`: toolbar search/filter, DataTable, dialog thêm/sửa, xóa có confirm
4. `TrainingPlanTab.vue`: toolbar filter, DataTable, expand row courses, dialog tạo plan, dialog thêm course vào plan
5. `_training.scss`: styles; đăng ký trong main.scss

**Exit criteria:**
- Tab "Khóa học": danh sách render; search/filter hoạt động; thêm/sửa/xóa khóa học hoạt động
- Tab "Kế hoạch": danh sách render; filter theo năm/quý/phòng ban/status; tạo kế hoạch; duyệt/hủy plan; expand row hiện courses; thêm/xóa course khỏi plan
- Tất cả Select có `filter` prop
- Không có `<style scoped>`
- Dark mode ổn

---

### Slice 4 — Tests

**File:** `backend/tests/test_training_courses.py`

```python
class TestTrainingCourses:
    test_list_courses_pagination
    test_list_courses_filter_by_type
    test_list_courses_filter_by_mandatory
    test_list_courses_filter_by_active
    test_list_courses_search_by_name
    test_list_courses_search_by_code
    test_create_course_success
    test_create_course_duplicate_code_returns_400
    test_create_course_invalid_type_returns_422
    test_get_course_not_found_returns_404
    test_update_course_success
    test_delete_course_hard_delete_no_links
    test_delete_course_soft_delete_with_links
    test_unauthenticated_returns_401
    test_missing_permission_returns_403
```

**File:** `backend/tests/test_training_plans.py`

```python
class TestTrainingPlans:
    test_list_plans_pagination
    test_list_plans_filter_by_year
    test_list_plans_filter_by_quarter
    test_list_plans_filter_by_status
    test_create_plan_success
    test_create_plan_invalid_quarter_returns_422
    test_get_plan_detail_includes_courses
    test_update_plan_header_fields_only
    test_delete_plan_draft_success
    test_delete_plan_approved_returns_400
    test_approve_plan_from_draft
    test_approve_plan_not_draft_returns_400
    test_cancel_plan_from_draft
    test_cancel_plan_from_approved
    test_cancel_plan_already_cancelled_returns_400
    test_add_course_to_plan_success
    test_add_duplicate_course_to_plan_returns_409
    test_update_plan_course_target_count
    test_remove_course_from_plan
```

**Chạy test:**
```bash
docker exec hrms-backend-1 pytest tests/test_training_courses.py tests/test_training_plans.py -v
```

---

## Rủi ro và cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Xóa course đang dùng trong plan | RESTRICT FK trên `training_plan_courses.course_id`; service kiểm tra và soft-delete thay thế |
| Xóa plan đã approved (có NV đang theo dõi) | Chỉ cho xóa khi `draft`; approved/cancelled chỉ có thể cancel |
| `quarter = NULL` nghĩa là "cả năm" — cần phân biệt với "chưa nhập" | Check constraint rõ; UI hiển thị "Cả năm" khi null |
| Course `is_active=false` vẫn xuất hiện trong plan cũ | `GET /training/plans/{id}` không filter `is_active` — vẫn hiện để tham chiếu; badge "Ngừng HĐ" |
| Frontend load departments chậm | Cache departments trong store; không reload mỗi lần mở Select |

---

## Thứ tự thực hiện

```
Slice 1 (Backend: Danh mục khóa học)
  ↓
Slice 2 (Backend: Kế hoạch đào tạo)
  ↓
Slice 3 (Frontend)
  ↓
Slice 4 (Tests)
```

---

## Không nằm trong 9.1

| Phần | Thuộc về |
|---|---|
| Gán nhân viên vào khóa học | 9.2 Theo dõi đào tạo |
| Ghi nhận kết quả học | 9.2 Theo dõi đào tạo |
| Training Passport của nhân viên | 9.2 Theo dõi đào tạo |
| Báo cáo đào tạo tổng hợp | 9.3 (nếu có) |
| Upload tài liệu khóa học | Ngoài phạm vi hiện tại |
