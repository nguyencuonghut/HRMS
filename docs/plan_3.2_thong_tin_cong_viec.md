# Kế hoạch thực hiện — 3.2. Thông tin công việc (Employee Job Records)

**Phạm vi:** Gán phòng ban / chức danh / vị trí công việc · Lịch sử chuyển công tác · Ngày thử việc / ngày chính thức · Đồng bộ trạng thái nhân viên · Mã hiển thị có prefix phòng ban  
**Phụ thuộc:** `1.1 Cơ cấu tổ chức` ✅ · `1.2 RBAC` ✅ · `3.1 Thông tin cá nhân` ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| Bảng `departments` (cây phân cấp) | ✅ Đã có (1.1) |
| Bảng `job_titles` | ✅ Đã có (1.1) |
| Bảng `job_positions` (gắn phòng ban + chức danh) | ✅ Đã có (1.1) |
| `departments.display_prefix` | ✅ Đã có (thêm trong 3.1) |
| `Employee.status`, `Employee.start_date` | ✅ Đã có (3.1) |
| `compute_display_code()` — hiện chỉ dùng `employee_seq`, chưa có prefix | ✅ Có, cần nâng cấp |
| Model `EmployeeJobRecord` | ❌ Chưa có |
| Bảng `employee_job_records` | ❌ Chưa có |
| Service / Schema / Endpoint job records | ❌ Chưa có |
| Frontend tab "Công việc" trong EmployeeDetailView | ❌ Chưa có |

---

## Phạm vi 3.2 — Thông tin công việc

Theo `docs/FEATURES.md §3.2`:

| Yêu cầu | Thiết kế |
|---|---|
| Phòng ban | FK → `departments` trong `employee_job_records` |
| Chức danh | FK → `job_titles` trong `employee_job_records` (nullable) |
| Vị trí công việc | FK → `job_positions` trong `employee_job_records` (nullable) |
| Ngày vào làm | `employees.start_date` — đã có, không thay đổi |
| Ngày thử việc | `employee_job_records.probation_start_date` + `probation_end_date` |
| Ngày chính thức | `employee_job_records.official_date` |
| Trạng thái nhân viên | `employees.status` — cập nhật đồng bộ qua service |
| Mã nhân viên có prefix phòng ban | `compute_display_code()` nâng cấp: join bản ghi hiện tại → lấy `display_prefix` |

> **Phạm vi 3.2 không bao gồm**: người thân (3.3), học vấn (3.4), hồ sơ đính kèm (3.5).

---

## Thiết kế cơ sở dữ liệu

### Bảng `employee_job_records`

```sql
CREATE TABLE employee_job_records (
    id                  SERIAL PRIMARY KEY,
    employee_id         INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,

    -- Đơn vị tổ chức
    department_id       INTEGER NOT NULL REFERENCES departments(id),
    job_title_id        INTEGER REFERENCES job_titles(id),      -- nullable: có thể chưa có chức danh
    job_position_id     INTEGER REFERENCES job_positions(id),   -- nullable: vị trí cụ thể (tùy chọn)

    -- Mốc thời gian nhân sự
    probation_start_date    DATE,        -- ngày bắt đầu thử việc (NULL nếu nhận thẳng chính thức)
    probation_end_date      DATE,        -- ngày kế hoạch kết thúc thử việc
    official_date           DATE,        -- ngày thực tế trở thành nhân viên chính thức

    -- Hiệu lực bản ghi
    effective_from      DATE NOT NULL,   -- ngày bắt đầu hiệu lực (thường = start_date hoặc ngày chuyển công tác)
    effective_to        DATE,            -- NULL = bản ghi hiện tại; ngày = đã kết thúc (chuyển công tác/nghỉ)
    is_current          BOOLEAN NOT NULL DEFAULT TRUE,

    -- Ghi chú
    notes               TEXT,

    -- Audit
    changed_by          INTEGER REFERENCES users(id),   -- người ghi nhận thay đổi
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP
);

-- Đảm bảo mỗi nhân viên chỉ có tối đa 1 bản ghi is_current = TRUE
CREATE UNIQUE INDEX uq_job_record_current
    ON employee_job_records (employee_id)
    WHERE (is_current = TRUE);

-- Index tìm kiếm nhanh theo employee
CREATE INDEX ix_job_records_employee_id ON employee_job_records (employee_id);
CREATE INDEX ix_job_records_department_id ON employee_job_records (department_id);
```

> **Thiết kế lịch sử không xóa**: mỗi lần chuyển công tác/thăng chức tạo một bản ghi mới. Bản ghi cũ không xóa — set `effective_to = ngày chuyển - 1`, `is_current = FALSE`. Bản ghi mới `is_current = TRUE`.

> **Partial unique index** thay vì constraint CHECK: PostgreSQL cho phép `UNIQUE WHERE (is_current = TRUE)` — mỗi nhân viên chỉ có tối đa 1 bản ghi hiện tại, nhưng có thể có nhiều bản ghi lịch sử (`is_current = FALSE`).

---

## Nâng cấp `compute_display_code()`

Hiện tại (3.1):
```python
def compute_display_code(employee_seq: int, dept_display_prefix: Optional[str] = None) -> str:
    seq_str = f"{employee_seq:04d}"
    return f"{dept_display_prefix}{seq_str}" if dept_display_prefix else seq_str
```

Signature không đổi. Thay đổi ở chỗ gọi: service sẽ join `employee_job_records` (is_current=True) → `departments.display_prefix` và truyền vào hàm này.

Trước 3.2: `compute_display_code(emp.employee_seq)` → `"0011"` (no prefix — đúng theo thiết kế)  
Sau 3.2: `compute_display_code(emp.employee_seq, dept.display_prefix)` → `"HC0011"` nếu phòng có prefix

**Quy tắc hiển thị** (không đổi so với thiết kế 3.1):

| Tình huống | Hiển thị | Ví dụ |
|---|---|---|
| Chưa có job record | `{employee_seq:04d}` | `0011` |
| Có phòng ban, phòng có `display_prefix` | `{display_prefix}{employee_seq:04d}` | `HC0011` |
| Có phòng ban, phòng chưa đặt `display_prefix` | `{employee_seq:04d}` | `0011` |

Nhân viên chuyển phòng → `employee_seq` không đổi, prefix thay đổi theo phòng mới → `display_code` tự động cập nhật khi đọc.

---

## Đồng bộ `employees.status`

`employees.status` là trạng thái nhân sự tổng thể (probation / official / long_leave / resigned). Bảng `employee_job_records` phản ánh cụ thể hơn (gắn ngày tháng thực tế).

Quy tắc đồng bộ trong service:

| Hành động | `employees.status` cập nhật thành |
|---|---|
| Tạo job record mới (gán phòng ban lần đầu) | Không tự động thay đổi |
| Ghi nhận ngày chính thức (`official_date`) | `'official'` |
| Chuyển công tác (tạo bản ghi mới) | Không thay đổi (trạng thái vẫn giữ) |
| HR cập nhật status thủ công (nghỉ phép dài hạn, nghỉ việc) | Trực tiếp qua `PUT /employees/{id}` — đã có từ 3.1 |

> **Thiết kế chủ ý**: không tự động đổi status khi tạo job record, vì HR Manager là người quyết định trạng thái chính thức. Chỉ khi HR bấm nút "Xác nhận chính thức" mới cập nhật `status = official` đồng thời với `official_date`.

---

## Schema thiết kế (Pydantic)

### Request schemas

```python
class JobRecordCreate(BaseModel):
    department_id: int
    job_title_id: Optional[int] = None
    job_position_id: Optional[int] = None
    probation_start_date: Optional[date] = None
    probation_end_date: Optional[date] = None
    official_date: Optional[date] = None
    effective_from: date              # bắt buộc: ngày hiệu lực
    notes: Optional[str] = None
    # Nếu official_date được đặt → service tự đồng bộ employees.status = 'official'

class JobRecordUpdate(BaseModel):
    department_id: Optional[int] = None
    job_title_id: Optional[int] = None
    job_position_id: Optional[int] = None
    probation_start_date: Optional[date] = None
    probation_end_date: Optional[date] = None
    official_date: Optional[date] = None
    notes: Optional[str] = None
    # Chỉ cho phép sửa bản ghi is_current=True
    # effective_from, effective_to không cho sửa trực tiếp (kiểm soát qua service)

class JobRecordTransfer(BaseModel):
    """Chuyển công tác / thăng chức — tạo bản ghi mới, đóng bản ghi cũ."""
    department_id: int
    job_title_id: Optional[int] = None
    job_position_id: Optional[int] = None
    effective_from: date              # ngày hiệu lực của vị trí mới
    notes: Optional[str] = None
```

### Response schemas

```python
class DepartmentBrief(BaseModel):
    id: int
    code: str
    name: str
    display_prefix: Optional[str]

class JobTitleBrief(BaseModel):
    id: int
    code: str
    name: str

class JobPositionBrief(BaseModel):
    id: int
    code: str
    name: str

class JobRecordRead(BaseModel):
    id: int
    employee_id: int
    department_id: int
    department: DepartmentBrief          # denormalized để UI không cần lookup riêng
    job_title_id: Optional[int]
    job_title: Optional[JobTitleBrief]
    job_position_id: Optional[int]
    job_position: Optional[JobPositionBrief]
    probation_start_date: Optional[date]
    probation_end_date: Optional[date]
    official_date: Optional[date]
    effective_from: date
    effective_to: Optional[date]
    is_current: bool
    notes: Optional[str]
    changed_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
```

### Bổ sung vào `EmployeeRead` (3.1 → 3.2)

```python
class EmployeeRead(BaseModel):
    ...  # tất cả field 3.1 giữ nguyên
    current_job: Optional[JobRecordRead]    # bản ghi is_current=True, None nếu chưa gán
    # display_code đã có — giờ phản ánh đúng prefix phòng ban
```

---

## API Endpoints

```
# Job records
GET    /api/v1/employees/{id}/job-records              Lịch sử công việc (mới nhất trước)
POST   /api/v1/employees/{id}/job-records              Tạo bản ghi đầu tiên (gán phòng ban)
PUT    /api/v1/employees/{id}/job-records/current      Sửa bản ghi hiện tại (in-place)
POST   /api/v1/employees/{id}/job-records/transfer     Chuyển công tác / thăng chức (tạo bản ghi mới)
```

**Lý do thiết kế 2 endpoint riêng (update vs transfer)**:
- `PUT .../current`: sửa thông tin ghi nhầm (sai ngày, sai vị trí) — không tạo bản ghi lịch sử mới.
- `POST .../transfer`: chuyển công tác thực sự — đóng bản ghi cũ, tạo bản ghi mới, giữ toàn bộ lịch sử.

---

## Logic service

### `create_job_record()`

```python
async def create_job_record(session, employee_id, payload: JobRecordCreate, actor_id) -> EmployeeJobRecord:
    # 1. Kiểm tra employee tồn tại
    # 2. Kiểm tra không có is_current=True rồi (nếu có → yêu cầu dùng /transfer)
    # 3. INSERT bản ghi mới với is_current=True
    # 4. Nếu payload.official_date → cập nhật Employee.status = 'official'
    # 5. Audit log
```

### `transfer_job_record()`

```python
async def transfer_job_record(session, employee_id, payload: JobRecordTransfer, actor_id) -> EmployeeJobRecord:
    # 1. Lấy bản ghi is_current=True (nếu không có → raise 409)
    # 2. SET old_record.effective_to = payload.effective_from - 1 day
    #        old_record.is_current = False
    # 3. INSERT bản ghi mới với is_current=True, effective_from = payload.effective_from
    # 4. Audit log: "TRANSFER", lưu old department → new department
```

### `get_display_code_prefix()`

```python
async def get_display_code_prefix(session, employee_id: int) -> Optional[str]:
    """Lấy display_prefix của phòng ban hiện tại để tính display_code."""
    result = await session.execute(
        select(Department.display_prefix)
        .join(EmployeeJobRecord, EmployeeJobRecord.department_id == Department.id)
        .where(
            EmployeeJobRecord.employee_id == employee_id,
            EmployeeJobRecord.is_current == True,
        )
    )
    return result.scalar_one_or_none()
```

Tích hợp vào `build_employee_read_data()` và `_build_list_item_data()`:

```python
# Thay thế compute_display_code(emp.employee_seq) bằng:
prefix = await get_display_code_prefix(session, emp.id)
display_code = compute_display_code(emp.employee_seq, prefix)
```

---

## RBAC

Tái sử dụng quyền `employees:edit` cho tất cả thao tác ghi nhận công việc.

| Hành động | Quyền |
|---|---|
| Xem lịch sử công việc | `employees:view` |
| Gán phòng ban lần đầu | `employees:edit` |
| Sửa bản ghi hiện tại | `employees:edit` |
| Chuyển công tác / thăng chức | `employees:edit` |

---

## Frontend

### Tab "Công việc" trong `EmployeeDetailView.vue`

Tab mới thêm vào sau tab "Liên lạc" (hoặc sau "Địa chỉ" tùy layout):

**Phần 1 — Vị trí hiện tại** (view + edit inline):
```
Phòng ban:    [HC] Hành chính Tổng hợp
Chức danh:    Chuyên viên
Vị trí:       Chuyên viên hành chính
Ngày vào làm: 15/01/2024
Ngày thử việc: 15/01/2024 → 14/04/2024
Ngày chính thức: 15/04/2024
[Sửa thông tin] [Ghi nhận chuyển công tác]
```

**Phần 2 — Lịch sử công việc** (DataTable, read-only):

| Phòng ban | Chức danh | Từ ngày | Đến ngày |
|---|---|---|---|
| Hành chính TH | Chuyên viên | 15/04/2024 | (hiện tại) |
| Kinh doanh | Nhân viên KD | 15/01/2024 | 14/04/2024 |

### Component `JobRecordEditor.vue`

Sub-component cho form sửa/tạo job record:
- `DepartmentSelect` (Select + filter, load từ `GET /departments`)
- `JobTitleSelect` (Select + filter)
- `JobPositionSelect` (Select + filter, phụ thuộc department được chọn)
- DatePicker: `probation_start_date`, `probation_end_date`, `official_date`, `effective_from`
- Textarea: `notes`

### Component `JobTransferDialog.vue`

Dialog "Ghi nhận chuyển công tác":
- Hiển thị vị trí cũ ở trên (read-only)
- Form vị trí mới: department, job_title, job_position, effective_from, notes
- Nút xác nhận → `POST .../transfer`

### Service bổ sung trong `employeeService.ts`

```typescript
// Job records
getJobRecords: (id: number) => api.get<JobRecordRead[]>(`${BASE}/${id}/job-records`)

createJobRecord: (id: number, data: JobRecordCreate) =>
  api.post<JobRecordRead>(`${BASE}/${id}/job-records`, data)

updateCurrentJobRecord: (id: number, data: JobRecordUpdate) =>
  api.put<JobRecordRead>(`${BASE}/${id}/job-records/current`, data)

transferJobRecord: (id: number, data: JobRecordTransfer) =>
  api.post<JobRecordRead>(`${BASE}/${id}/job-records/transfer`, data)
```

---

## Seed dữ liệu

Gán phòng ban cho 10 nhân viên mẫu (đã có từ 3.1):

| employee_seq | full_name | department | job_title | effective_from | display_code (sau 3.2) |
|---|---|---|---|---|---|
| 1 | Nguyễn Văn An | Hành chính (HC) | Trưởng phòng | 2024-01-15 | HC0001 |
| 2 | Trần Thị Bình | Kế toán (KT) | Kế toán viên | 2024-03-01 | KT0002 |
| 3 | Lê Văn Cường | Kinh doanh (KD) | Nhân viên KD | 2024-06-15 | KD0003 |
| 4 | Phạm Thị Dung | Kế toán (KT) | Kế toán viên | 2024-09-01 | KT0004 |
| 5 | Hoàng Văn Em | Kinh doanh (KD) | Nhân viên KD | 2025-01-01 | KD0005 |
| 6 | Ngô Thị Phương | Hành chính (HC) | Chuyên viên HC | 2025-04-01 | HC0006 |
| 7 | Đỗ Văn Giang | Kinh doanh (KD) | Nhân viên KD | 2025-11-01 | KD0007 |
| 8 | Vũ Thị Hoa | Hành chính (HC) | Chuyên viên HC | 2026-03-01 | HC0008 |
| 9 | Bùi Văn Ích | Kế toán (KT) | Thực tập sinh | 2026-04-15 | KT0009 |
| 10 | Trịnh Thị Kim | Kinh doanh (KD) | Nhân viên KD | 2023-06-01 | KD0010 |

Nhân viên 1 (Nguyễn Văn An) có thêm 1 bản ghi lịch sử (chuyển từ Kinh doanh → Hành chính) để demo tab lịch sử.

---

## Tests

### `test_employee_job_records.py`

```
test_create_job_record_success              → 201, is_current=True, display_code cập nhật prefix
test_create_job_record_duplicate_403       → đã có is_current record → 409 (dùng /transfer)
test_list_job_records_history              → trả đúng thứ tự mới nhất trước
test_update_current_record                 → sửa in-place, không tạo bản ghi mới
test_transfer_creates_new_record           → bản ghi cũ is_current=False, effective_to đúng
test_transfer_updates_display_code         → display_code phản ánh phòng mới
test_official_date_syncs_status            → khi official_date được set → employees.status = 'official'
test_job_record_requires_edit_perm_403     → role viewer không được tạo
test_job_record_writes_audit_log           → audit log ghi nhận CREATE / TRANSFER
test_get_employee_includes_current_job     → GET /employees/{id} trả current_job đúng
test_display_code_no_prefix               → nhân viên chưa có job record → display_code = "000X"
test_display_code_dept_no_prefix          → phòng ban không có display_prefix → display_code = "000X"
```

---

## Thứ tự triển khai

### Bước 1 — Model & Migration
1. Tạo `backend/app/models/employee_job.py`: `EmployeeJobRecord`
2. Tạo migration `0008_create_employee_job_records.py`
3. Đăng ký model vào `backend/app/models/__init__.py`

### Bước 2 — Seed dữ liệu
1. Tạo `backend/app/seeds/employee_job_records.py`
2. Đăng ký vào seed pipeline sau `employees.py`

### Bước 3 — Backend CRUD
1. Bổ sung schemas vào `backend/app/schemas/employee.py`: `JobRecordCreate`, `JobRecordUpdate`, `JobRecordTransfer`, `JobRecordRead`, `DepartmentBrief`, `JobTitleBrief`, `JobPositionBrief`
2. Tạo / mở rộng `backend/app/services/employee_job_service.py`: `create_job_record`, `update_current_job_record`, `transfer_job_record`, `get_job_records`, `get_display_code_prefix`
3. Nâng cấp `employee_service.py`: tích hợp `get_display_code_prefix` vào `build_employee_read_data()` và `_build_list_item_data()`; bổ sung `current_job` vào `EmployeeRead`
4. Thêm endpoints vào `backend/app/api/v1/endpoints/employees.py` (hoặc tách file riêng `employee_job_records.py`)
5. Đăng ký router

### Bước 4 — Tests backend
1. Tạo `backend/tests/test_employee_job_records.py`
2. Chạy `docker exec hrms-backend-1 python -m pytest tests/ -v` → toàn bộ pass

### Bước 5 — Frontend
1. Bổ sung types vào `frontend/src/services/employeeService.ts`: `JobRecordRead`, `JobRecordCreate`, `JobRecordUpdate`, `JobRecordTransfer`
2. Thêm service methods vào `employeeService.ts`
3. Tạo `frontend/src/views/employees/JobRecordEditor.vue` (form tạo/sửa)
4. Tạo `frontend/src/views/employees/JobTransferDialog.vue` (dialog chuyển công tác)
5. Thêm tab "Công việc" vào `EmployeeDetailView.vue`

### Bước 6 — Phân quyền & Audit log
1. Verify quyền `employees:edit` cho tất cả thao tác ghi nhận công việc
2. Audit log: `CREATE_JOB_RECORD`, `UPDATE_JOB_RECORD`, `TRANSFER_JOB_RECORD`

---

## Rủi ro thiết kế cần tránh

1. **Lưu nhiều is_current=TRUE cho 1 nhân viên**  
   Phải dùng partial unique index `WHERE (is_current = TRUE)`. Đừng kiểm soát bằng application code đơn thuần — race condition có thể tạo 2 bản ghi is_current đồng thời.

2. **Xóa bản ghi lịch sử khi chuyển công tác**  
   Phải giữ nguyên bản ghi cũ, chỉ set `is_current=False` + `effective_to`. Toàn bộ lịch sử phải truy xuất được.

3. **Tính display_code mỗi request bằng cách query riêng**  
   Nên JOIN `employee_job_records` + `departments` trong cùng query list employees để tránh N+1. Với danh sách 100 nhân viên, không thể gọi 100 query riêng lẻ.

4. **Để `employees.status` không đồng bộ với job record**  
   `status` phải được service cập nhật có chủ đích (khi HR xác nhận chính thức). Không tự động đổi chỉ vì tạo job record mới — HR là người quyết định trạng thái.

5. **Gộp logic chuyển công tác vào PUT thông thường**  
   `PUT .../current` chỉ để sửa thông tin ghi nhầm. Chuyển công tác thực sự phải qua `POST .../transfer` để đảm bảo lịch sử không bị ghi đè.

---

## Kết quả mong đợi sau 3.2

- Mỗi nhân viên có bản ghi công việc hiện tại (phòng ban, chức danh, vị trí) được ghi nhận chính xác.
- Lịch sử chuyển công tác, thăng chức được lưu đầy đủ và truy xuất được.
- Mã hiển thị (`display_code`) phản ánh đúng prefix của phòng ban hiện tại — tự động cập nhật khi nhân viên chuyển phòng.
- Ngày thử việc và ngày chính thức được ghi nhận rõ ràng, liên kết với trạng thái nhân viên.
- Frontend có tab "Công việc" trong hồ sơ nhân viên — xem và cập nhật thông tin công việc, xem lịch sử chuyển công tác.
