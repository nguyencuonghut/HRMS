# Kế hoạch triển khai — 9.2. Theo dõi đào tạo nhân viên

**Phạm vi:** Gán nhân viên vào khóa học · Ghi nhận kết quả · Theo dõi trạng thái hoàn thành · Training Passport  
**Phụ thuộc:** `9.1 Quản lý khóa học` ✅ (training_courses, training_plans phải tồn tại)  
**Căn cứ nghiệp vụ:** FEATURES.md §9.2

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `training_courses` table | ✅ Hoàn thành (9.1) | |
| `training_plans` table | ✅ Hoàn thành (9.1) | |
| `employee_training_records` table | ❌ Chưa có | |
| API theo dõi đào tạo | ❌ Chưa có | |
| Tab "Theo dõi" trong `TrainingView.vue` | ❌ Chưa có | |
| Bulk assign từ plan | ❌ Chưa có | |
| Training Passport endpoint | ❌ Chưa có | |

---

## Phạm vi

Theo FEATURES.md §9.2:
> Gán nhân viên vào khóa học  
> Ghi nhận kết quả: Đạt / Không đạt / Điểm số  
> Theo dõi trạng thái hoàn thành  
> Hộ chiếu đào tạo (Training Passport): toàn bộ lịch sử đào tạo của nhân viên

---

## Thiết kế dữ liệu

### Bảng `employee_training_records`

| Cột | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `employee_id` | INT | FK employees CASCADE NOT NULL | Nhân viên |
| `course_id` | INT | FK training_courses RESTRICT NOT NULL | Khóa học |
| `plan_id` | INT | FK training_plans SET NULL, nullable | Gán từ plan; NULL = gán thủ công |
| `status` | VARCHAR(20) | NOT NULL DEFAULT `chua_bat_dau`, CHECK | Xem bảng trạng thái |
| `result` | VARCHAR(20) | nullable, CHECK | `dat` \| `khong_dat` (NULL = chưa đánh giá) |
| `score` | NUMERIC(5,2) | nullable | Điểm số 0.00–100.00 |
| `start_date` | DATE | nullable | Ngày bắt đầu |
| `end_date` | DATE | nullable | Ngày kết thúc |
| `note` | TEXT | nullable | Ghi chú |
| `created_by_id` | INT | FK users SET NULL, nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**Trạng thái (`status`):**
| Giá trị | Nhãn hiển thị |
|---|---|
| `chua_bat_dau` | Chưa bắt đầu |
| `dang_hoc` | Đang học |
| `hoan_thanh` | Hoàn thành |
| `khong_hoan_thanh` | Không hoàn thành |
| `vang_mat` | Vắng mặt |

**Kết quả (`result`):**
| Giá trị | Nhãn hiển thị |
|---|---|
| `dat` | Đạt |
| `khong_dat` | Không đạt |
| NULL | Chưa đánh giá |

**Indexes:**
- `(employee_id)`
- `(course_id)`
- `(plan_id)`
- `(status)`
- `(end_date)` — partial index: `WHERE status = 'hoan_thanh'` (tối ưu truy vấn completed)
- `(employee_id, course_id)` — composite để tránh duplicate check

---

## Thiết kế API

### Employee training records

```
GET    /training/records
       ?employee_id=&course_id=&plan_id=&status=&result=
       &from_date=&to_date=&department_id=&search=
       &page=&page_size=
       → TrainingRecordListPage

POST   /training/records
       body: TrainingRecordCreate
       → TrainingRecordRead

GET    /training/records/{id}
       → TrainingRecordRead

PUT    /training/records/{id}
       body: TrainingRecordUpdate
       → TrainingRecordRead

DELETE /training/records/{id}
       → 204 No Content
```

### Bulk assign từ plan

```
POST   /training/plans/{plan_id}/assign
       body: BulkAssignRequest { employee_ids: [...] }
       → BulkAssignResult { created: int, skipped: int }
       Logic: với mỗi employee_id, tạo record nếu chưa tồn tại;
              bỏ qua (skipped++) nếu đã có record (employee_id, course_id, plan_id)
```

### Training Passport

```
GET    /employees/{employee_id}/training/passport
       → list[TrainingRecordRead]
       Logic: toàn bộ lịch sử, không phân trang, sắp xếp theo end_date DESC, created_at DESC
```

---

## Permissions

| Permission | Mô tả |
|---|---|
| `training:view` | Xem danh sách records, passport |
| `training:manage_records` | Gán NV, cập nhật trạng thái/kết quả, xóa |

---

## Schemas

### TrainingRecordRead

```python
class TrainingRecordRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str | None
    course_id: int
    course_name: str
    course_type: str
    course_type_label: str
    plan_id: int | None
    plan_title: str | None
    status: str
    status_label: str
    result: str | None
    result_label: str | None        # None nếu result là None
    score: Decimal | None
    start_date: date | None
    end_date: date | None
    note: str | None
    created_by_name: str | None
    created_at: datetime
```

### TrainingRecordCreate

```python
class TrainingRecordCreate(BaseModel):
    employee_id: int
    course_id: int
    plan_id: int | None = None
    status: str = "chua_bat_dau"    # default
    start_date: date | None = None
    end_date: date | None = None
    note: str | None = None
```

### TrainingRecordUpdate

```python
class TrainingRecordUpdate(BaseModel):
    status: str | None = None
    result: str | None = None
    score: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_score_and_dates(self) -> "TrainingRecordUpdate":
        if self.score is not None:
            if not (0 <= self.score <= 100):
                raise ValueError("score phải trong khoảng 0–100")
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date phải >= start_date")
        return self
```

### Bulk assign

```python
class BulkAssignRequest(BaseModel):
    employee_ids: list[int]         # 1–200 phần tử
    plan_id: int                    # plan phải tồn tại và không bị cancelled
    course_id: int                  # course phải tồn tại trong plan
    note: str | None = None

    @model_validator(mode="after")
    def validate_employee_ids(self) -> "BulkAssignRequest":
        if not (1 <= len(self.employee_ids) <= 200):
            raise ValueError("Số lượng nhân viên phải từ 1 đến 200")
        return self

class BulkAssignResult(BaseModel):
    created: int
    skipped: int                    # đã tồn tại record
```

### Pagination

```python
class TrainingRecordListPage(BaseModel):
    items: list[TrainingRecordRead]
    total: int
    page: int
    page_size: int
```

---

## Service logic

### `training_record_service.py`

**`get_records()`:**
- SELECT `employee_training_records`
  - JOIN `employees` (employee_code, employee_name)
  - JOIN `departments` via employees (department_name) — LEFT JOIN
  - JOIN `training_courses` (course_name, course_type)
  - LEFT JOIN `training_plans` (plan_title)
  - LEFT JOIN `users` as created_by (created_by_name)
- Filter: `employee_id`, `course_id`, `plan_id`, `status`, `result`
- Filter `department_id`: JOIN employees → WHERE `employees.department_id = :dept`
- Filter `from_date`/`to_date`: WHERE `end_date BETWEEN :from AND :to` (nếu có)
- Filter `search`: ILIKE trên `employee_code`, `employee_name`, `course_name`
- ORDER BY `created_at DESC`
- Phân trang; trả `TrainingRecordListPage`

**`get_record_or_404()`:** `_get_or_404` theo id; không cho xem record của NV khác nếu thiếu quyền

**`create_record()`:**
- Validate `employee_id` tồn tại → 404
- Validate `course_id` tồn tại và `is_active` → 404
- Validate `plan_id` tồn tại nếu có → 404
- Nếu có `plan_id`: kiểm tra `(plan_id, course_id)` có trong `training_plan_courses` → 400 nếu course không thuộc plan
- Validate `end_date >= start_date` nếu cả hai có
- Insert; trả `TrainingRecordRead`

**`update_record()`:**
- `_get_or_404`
- Validate `score` trong 0–100 (đã có trong schema validator, service check lại)
- Validate `end_date >= start_date` nếu cả hai có hoặc một trong hai thay đổi
- Update fields; trả `TrainingRecordRead`

**`delete_record()`:** `_get_or_404`; xóa

**`bulk_assign()`:**
- Validate `plan_id` tồn tại, `status != cancelled` → 400 nếu plan cancelled
- Validate `course_id` tồn tại trong `training_plan_courses` cho plan đó → 400 nếu không
- Với mỗi `employee_id` trong danh sách:
  - Kiểm tra employee tồn tại (batch query)
  - Kiểm tra đã có record với `(employee_id, course_id, plan_id)` không → skipped++ nếu có
  - Tạo record mới với `status = chua_bat_dau` → created++
- Dùng `INSERT ... ON CONFLICT DO NOTHING` để tối ưu bulk insert
- Trả `BulkAssignResult`

**`get_training_passport()`:**
- SELECT toàn bộ records của `employee_id` với đủ JOIN (không phân trang)
- ORDER BY `end_date DESC NULLS LAST`, `created_at DESC`
- Trả `list[TrainingRecordRead]`

---

## Migration

**File:** `alembic/versions/0028_create_employee_training_records.py`

```python
op.create_table(
    "employee_training_records",
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("employee_id", sa.Integer,
              sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
    sa.Column("course_id", sa.Integer,
              sa.ForeignKey("training_courses.id", ondelete="RESTRICT"), nullable=False),
    sa.Column("plan_id", sa.Integer,
              sa.ForeignKey("training_plans.id", ondelete="SET NULL"), nullable=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="chua_bat_dau"),
    sa.Column("result", sa.String(20), nullable=True),
    sa.Column("score", sa.Numeric(5, 2), nullable=True),
    sa.Column("start_date", sa.Date, nullable=True),
    sa.Column("end_date", sa.Date, nullable=True),
    sa.Column("note", sa.Text, nullable=True),
    sa.Column("created_by_id", sa.Integer,
              sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    sa.Column("created_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.func.now()),
    sa.Column("updated_at", sa.TIMESTAMPTZ, nullable=False, server_default=sa.func.now()),
    sa.CheckConstraint(
        "status IN ('chua_bat_dau','dang_hoc','hoan_thanh','khong_hoan_thanh','vang_mat')",
        name="ck_emp_training_records_status",
    ),
    sa.CheckConstraint(
        "result IN ('dat','khong_dat') OR result IS NULL",
        name="ck_emp_training_records_result",
    ),
    sa.CheckConstraint(
        "score >= 0 AND score <= 100 OR score IS NULL",
        name="ck_emp_training_records_score",
    ),
    sa.CheckConstraint(
        "end_date >= start_date OR start_date IS NULL OR end_date IS NULL",
        name="ck_emp_training_records_dates",
    ),
)

# Indexes
op.create_index("ix_emp_training_records_employee", "employee_training_records", ["employee_id"])
op.create_index("ix_emp_training_records_course", "employee_training_records", ["course_id"])
op.create_index("ix_emp_training_records_plan", "employee_training_records", ["plan_id"])
op.create_index("ix_emp_training_records_status", "employee_training_records", ["status"])
op.create_index("ix_emp_training_records_end_date", "employee_training_records", ["end_date"])
# Partial index cho completed records
op.execute(
    "CREATE INDEX ix_emp_training_records_completed "
    "ON employee_training_records (employee_id, end_date) "
    "WHERE status = 'hoan_thanh'"
)
op.create_index(
    "ix_emp_training_records_emp_course",
    "employee_training_records",
    ["employee_id", "course_id"],
)
```

---

## Thiết kế Frontend

### Tab "Theo dõi" trong `TrainingView.vue`

Thêm tab thứ ba vào `TabView`:
- Tab "Khóa học" → `CourseListTab.vue` (9.1)
- Tab "Kế hoạch" → `TrainingPlanTab.vue` (9.1)
- **Tab "Theo dõi"** → `TrainingRecordTab.vue` (9.2 — mới)

---

### `TrainingRecordTab.vue`

**Toolbar:**
- `InputText` placeholder "Tìm mã NV, tên NV, tên khóa học..." → debounce search
- `Select` "Phòng ban" (filter prop): load từ API departments
- `Select` "Khóa học" (filter prop): load danh sách courses
- `Select` "Trạng thái" (filter prop): Tất cả / Chưa bắt đầu / Đang học / Hoàn thành / Không hoàn thành / Vắng mặt
- `Select` "Kết quả" (filter prop): Tất cả / Đạt / Không đạt / Chưa đánh giá
- `DatePicker` "Từ ngày" — `DatePicker` "Đến ngày" (filter theo end_date)
- Button "Gán vào khóa học" (chỉ hiện với `training:manage_records`)

**DataTable:**
| Cột | Hiển thị |
|---|---|
| Nhân viên | `employee_code` + `employee_name` |
| Phòng ban | `department_name` |
| Khóa học | `course_name` |
| Loại | `<Tag>` course_type_label |
| Trạng thái | `<Tag>` (xem màu bên dưới) |
| Kết quả | `<Tag>` (xem màu bên dưới) |
| Điểm | `score` (hiện "—" nếu null) |
| Ngày bắt đầu | format DD/MM/YYYY |
| Ngày kết thúc | format DD/MM/YYYY |
| Thao tác | nút Cập nhật kết quả, Xóa |

**Tag colors:**
| Status | Severity |
|---|---|
| `chua_bat_dau` | secondary |
| `dang_hoc` | info |
| `hoan_thanh` | success |
| `khong_hoan_thanh` | danger |
| `vang_mat` | warn |

| Result | Severity |
|---|---|
| `dat` | success |
| `khong_dat` | danger |
| null | secondary (hiện "Chưa đánh giá") |

---

### Dialog "Gán vào khóa học"

Dùng để gán một hoặc nhiều nhân viên vào một khóa học:

- `Select` (filter): **Khóa học** (required) — load `is_active=true`; hiện mã + tên
- `Select` (filter): **Kế hoạch** (optional) — load plans theo year hiện tại; hiện title + năm; khi chọn plan, tự filter course theo courses trong plan
- `MultiSelect` (filter): **Nhân viên** (required, chọn nhiều) — load employees; hiện mã + tên; placeholder "Chọn nhân viên..."
- `DatePicker`: Ngày bắt đầu (optional)
- `Textarea`: Ghi chú (optional)
- Button "Gán": gọi `POST /training/records` cho từng NV (nếu plan chọn và course từ plan → gọi `POST /training/plans/{id}/assign`); hiện toast kết quả "Đã gán X NV, bỏ qua Y (đã tồn tại)"

---

### Dialog "Cập nhật kết quả"

Cập nhật trạng thái và kết quả học cho một record:

- `Select` (filter): **Trạng thái** (required)
- `Select` (filter): **Kết quả** (optional, chỉ hiện khi status = `hoan_thanh` hoặc `khong_hoan_thanh`)
- `InputNumber` (min=0, max=100, fractionDigits=2): **Điểm số** (optional)
- `DatePicker`: Ngày bắt đầu, Ngày kết thúc (optional)
- `Textarea`: Ghi chú (optional)
- Validation: score 0–100; end_date >= start_date

---

### Training Passport (trong employee profile)

> **Out of scope cho 9.2** — sẽ tích hợp vào hồ sơ nhân viên (module 3.x) trong plan sau.

API `GET /employees/{employee_id}/training/passport` đã sẵn sàng để tích hợp. Khi tích hợp:
- Thêm tab "Đào tạo" vào employee profile view
- Bảng read-only: Khóa học, Loại, Trạng thái, Kết quả, Điểm, Ngày bắt đầu, Ngày kết thúc
- Sắp xếp mới nhất lên đầu

---

### CSS bổ sung vào `_training.scss`

```scss
// Record tab
.training-record-tab {
  .record-score {
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  .passport-table {
    .p-datatable-tbody > tr > td {
      padding: 0.4rem 0.75rem;
    }
  }

  .assign-dialog-multiselect {
    width: 100%;
  }
}
```

---

## Cấu trúc file mới / thay đổi

```
backend/
  alembic/versions/0028_create_employee_training_records.py  (NEW)
  app/models/training.py                                      (EDIT: thêm EmployeeTrainingRecord)
  app/schemas/training.py                                     (EDIT: thêm record schemas + bulk assign)
  app/services/training_record_service.py                     (NEW)
  app/api/v1/endpoints/training.py                            (EDIT: thêm record endpoints + bulk assign)
  app/api/v1/router.py                                        (EDIT: thêm employee passport sub-route)
  tests/test_training_records.py                              (NEW)

frontend/
  src/services/trainingService.ts                             (EDIT: thêm record types + API calls)
  src/views/training/components/TrainingRecordTab.vue         (NEW)
  src/views/training/TrainingView.vue                         (EDIT: thêm tab "Theo dõi")
  src/assets/styles/views/_training.scss                      (EDIT: thêm record styles)
```

---

## Kế hoạch theo slice

### Slice 1 — Backend: Record CRUD + Bulk Assign + Passport

**Tasks:**
1. Migration `0028_create_employee_training_records.py`
2. Model `EmployeeTrainingRecord` trong `app/models/training.py`
3. Schema bổ sung vào `app/schemas/training.py`:
   - `TrainingRecordRead`, `TrainingRecordCreate`, `TrainingRecordUpdate`
   - `TrainingRecordListPage`
   - `BulkAssignRequest`, `BulkAssignResult`
4. Service `training_record_service.py`:
   - `get_records()` với đủ JOIN và filter
   - `get_record_or_404()`
   - `create_record()` với validation
   - `update_record()` với validation score + dates
   - `delete_record()`
   - `bulk_assign()` với INSERT ON CONFLICT DO NOTHING
   - `get_training_passport()`
5. Bổ sung endpoints vào `app/api/v1/endpoints/training.py`:
   - `GET/POST/GET/{id}/PUT/{id}/DELETE/{id}` cho `/training/records`
   - `POST /training/plans/{plan_id}/assign`
6. Thêm route `GET /employees/{employee_id}/training/passport` vào router

**Exit criteria:**
- `POST /training/records` tạo record thành công; validation lỗi → 422
- `PUT /training/records/{id}` cập nhật status, result, score; score ngoài 0–100 → 422; end_date < start_date → 422
- `DELETE /training/records/{id}` xóa thành công
- `GET /training/records` trả danh sách phân trang; filter theo employee, course, status, dept hoạt động
- `POST /training/plans/{id}/assign` với 3 NV: 2 mới → created=2; 1 đã tồn tại → skipped=1
- `GET /employees/{id}/training/passport` trả toàn bộ lịch sử, sắp xếp đúng
- Plan cancelled → bulk assign trả 400
- Course không thuộc plan → bulk assign trả 400

---

### Slice 2 — Frontend

**Tasks:**
1. Bổ sung vào `trainingService.ts`:
   - Types: `TrainingRecordRead`, `TrainingRecordCreate`, `TrainingRecordUpdate`, `TrainingRecordListPage`, `BulkAssignRequest`, `BulkAssignResult`
   - API calls: `getRecords`, `createRecord`, `updateRecord`, `deleteRecord`, `bulkAssign`, `getPassport`
2. `TrainingRecordTab.vue`:
   - Toolbar search + filters (dept, course, status, result, date range)
   - DataTable với Tag colors theo status/result
   - Nút "Gán vào khóa học" → dialog assign
   - Nút "Cập nhật kết quả" per row → dialog update
   - Confirm xóa
3. Dialog "Gán vào khóa học": MultiSelect NV, Select course/plan, DatePicker start, Textarea note
4. Dialog "Cập nhật kết quả": Select status/result, InputNumber score, DatePicker dates, Textarea note
5. Cập nhật `TrainingView.vue`: thêm tab thứ ba "Theo dõi"
6. Bổ sung CSS vào `_training.scss`

**Exit criteria:**
- Tab "Theo dõi" render đúng danh sách records
- Search + filter hoạt động (debounce)
- Gán 1 NV: toast thành công; gán nhiều NV: toast hiện "Đã gán X NV, bỏ qua Y"
- Dialog cập nhật kết quả: lưu thành công; score validation hiện trên UI; end_date < start_date → disabled button
- Xóa record có confirm
- Tất cả Select có `filter` prop
- Không có `<style scoped>`
- Dark mode ổn

---

### Slice 3 — Tests

**File:** `backend/tests/test_training_records.py`

```python
class TestTrainingRecords:
    # CRUD cơ bản
    test_create_record_success
    test_create_record_invalid_employee_returns_404
    test_create_record_invalid_course_returns_404
    test_create_record_inactive_course_returns_400
    test_create_record_plan_id_course_not_in_plan_returns_400
    test_get_record_not_found_returns_404
    test_update_record_status
    test_update_record_result_and_score
    test_update_record_score_out_of_range_returns_422
    test_update_record_end_date_before_start_date_returns_422
    test_delete_record_success

    # List + filter
    test_list_records_pagination
    test_list_records_filter_by_employee
    test_list_records_filter_by_status
    test_list_records_filter_by_result
    test_list_records_filter_by_department
    test_list_records_search_by_employee_name
    test_list_records_filter_by_date_range

    # Bulk assign
    test_bulk_assign_creates_records
    test_bulk_assign_skips_existing_records
    test_bulk_assign_returns_created_and_skipped_counts
    test_bulk_assign_cancelled_plan_returns_400
    test_bulk_assign_course_not_in_plan_returns_400
    test_bulk_assign_too_many_employees_returns_422

    # Training Passport
    test_passport_returns_all_records_for_employee
    test_passport_sorted_by_end_date_desc
    test_passport_empty_for_new_employee

    # Auth + Permission
    test_unauthenticated_returns_401
    test_missing_permission_returns_403
```

**Chạy test:**
```bash
docker exec hrms-backend-1 pytest tests/test_training_records.py -v
```

---

## Rủi ro và cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Bulk assign nhiều NV (100+) → INSERT chậm | Dùng `INSERT ... ON CONFLICT DO NOTHING` batch; tránh N+1 |
| Cùng NV được gán cùng course từ nhiều plan khác nhau | Không có UNIQUE trên (employee_id, course_id); cho phép nhiều records — đây là thiết kế có chủ ý (NV tham gia cùng course nhiều lần) |
| Score = 0 bị nhầm với NULL | Score là `Decimal | None`; 0 là điểm hợp lệ; UI phân biệt "0 điểm" vs "chưa có điểm" |
| `training_courses` bị soft-delete (is_active=false) nhưng records vẫn reference | RESTRICT FK giữ course tồn tại; soft-delete course không phá vỡ records; badge "Ngừng HĐ" trong record view |
| Xóa employee → CASCADE xóa hết records | FK employees CASCADE: chấp nhận theo thiết kế; nếu cần giữ history, cân nhắc SET NULL trong tương lai |
| Filter kết hợp nhiều điều kiện → query phức | Index đã có trên employee_id, status, course_id, end_date; kiểm tra EXPLAIN ANALYZE nếu query > 500ms |
| Training Passport quá nhiều records (NV lâu năm) | Không phân trang passport theo spec; nếu > 500 records thì xem xét phân trang trong tương lai; hiện tại chấp nhận |
| MultiSelect NV trong dialog assign load chậm | Lazy load + virtual scroll trong PrimeVue MultiSelect; hoặc search-as-you-type |

---

## Thứ tự thực hiện

```
Slice 1 (Backend: Record CRUD + Bulk Assign + Passport)
  ↓
Slice 2 (Frontend: TrainingRecordTab + dialogs)
  ↓
Slice 3 (Tests)
```

---

## Không nằm trong 9.2

| Phần | Thuộc về |
|---|---|
| Tích hợp Training Passport vào hồ sơ nhân viên (tab "Đào tạo" trong 3.x) | Plan 3.x (employee profile) |
| Báo cáo đào tạo tổng hợp (thống kê toàn công ty) | 9.3 nếu có |
| Upload chứng chỉ / tài liệu hoàn thành | Ngoài phạm vi hiện tại |
| Nhắc nhở đào tạo sắp hết hạn (notification) | Ngoài phạm vi hiện tại |
| Tích hợp điểm đào tạo vào KPI | Ngoài phạm vi hiện tại |
