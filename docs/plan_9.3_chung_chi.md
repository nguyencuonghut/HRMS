# Kế hoạch triển khai — 9.3. Chứng chỉ

**Phạm vi:** Quản lý chứng chỉ nhân viên · Cảnh báo sắp hết hạn · Lưu file chứng chỉ  
**Phụ thuộc:** `9.1 Khóa đào tạo` (training_courses cho related_course_id)  
**Căn cứ nghiệp vụ:** FEATURES.md §9.3

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `training_courses` table | ✅ Hoàn thành (9.1) | FK nguồn cho related_course_id |
| `employee_certificates` table | ❌ Chưa có | |
| API CRUD chứng chỉ | ❌ Chưa có | |
| API expiry alert | ❌ Chưa có | |
| Tab Chứng chỉ trong `TrainingView.vue` | ❌ Chưa có (placeholder) | |

---

## Phạm vi

Theo FEATURES.md §9.3:
> Quản lý chứng chỉ sau đào tạo: tên, ngày cấp, ngày hết hạn  
> Cảnh báo chứng chỉ sắp hết hạn  
> Lưu file chứng chỉ

**Trong phạm vi:**
- CRUD chứng chỉ nhân viên (gắn tùy chọn với khóa đào tạo)
- Upload/download file chứng chỉ qua MinIO
- Tính trạng thái hết hạn: `valid`, `expiring_soon`, `expired`, `no_expiry`
- Filter theo `expiry_status`, phòng ban, ngày cấp, tìm kiếm tên
- Cảnh báo banner khi có chứng chỉ sắp hết hạn
- Lịch sử chứng chỉ theo nhân viên (`/employees/{id}/training/certificates`)

**Ngoài phạm vi:**
- Tự động gửi email nhắc nhở hết hạn (thuộc module thông báo)
- Phê duyệt chứng chỉ đa cấp

---

## Thiết kế data model

### Bảng `employee_certificates`

| Cột | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `employee_id` | INTEGER | FK employees(id) CASCADE NOT NULL | |
| `certificate_name` | VARCHAR(500) | NOT NULL | Tên chứng chỉ |
| `issuing_organization` | VARCHAR(300) | nullable | Tổ chức cấp |
| `issued_date` | DATE | NOT NULL | Ngày cấp |
| `expiry_date` | DATE | nullable | NULL = không hết hạn / vĩnh viễn |
| `related_course_id` | INTEGER | FK training_courses(id) SET NULL, nullable | Khóa đào tạo liên quan |
| `note` | TEXT | nullable | Ghi chú |
| `file_path` | TEXT | nullable | MinIO object path |
| `file_name` | VARCHAR(300) | nullable | Tên file gốc |
| `file_size` | INTEGER | nullable | Kích thước file (bytes) |
| `mime_type` | VARCHAR(100) | nullable | MIME type |
| `created_by_id` | INTEGER | FK users(id) SET NULL, nullable | |
| `created_at` | TIMESTAMP | NOT NULL, default now() | |
| `updated_at` | TIMESTAMP | NOT NULL, default now(), onupdate | |

**Indexes:**
- `ix_employee_certificates_employee_id` trên `(employee_id)`
- `ix_employee_certificates_expiry_date` trên `(expiry_date)` — phục vụ query cảnh báo hết hạn

**Migration file:** `alembic/versions/0029_create_employee_certificates.py`

---

## Thiết kế API

### Endpoints

```
GET    /training/certificates
       ?employee_id=&expiry_status=expiring_soon|expired|valid|no_expiry
       &department_id=&from_issued=&to_issued=&search=
       &page=1&page_size=20
       → CertificateListPage

POST   /training/certificates
       Content-Type: multipart/form-data
       body: str (JSON CertificateCreate)
       file: UploadFile (optional)
       → CertificateRead

GET    /training/certificates/{id}
       → CertificateRead

PUT    /training/certificates/{id}
       Content-Type: multipart/form-data
       body: str (JSON CertificateUpdate)
       file: UploadFile (optional, thay thế file cũ nếu có)
       → CertificateRead

DELETE /training/certificates/{id}
       → 204 No Content (+ xóa file khỏi MinIO nếu có)

GET    /training/certificates/{id}/download
       → FileResponse / StreamingResponse

# Lịch sử theo nhân viên
GET    /employees/{employee_id}/training/certificates
       → list[CertificateRead]
```

### Query parameters chi tiết

| Param | Kiểu | Mô tả |
|---|---|---|
| `employee_id` | int, optional | Lọc theo nhân viên cụ thể |
| `expiry_status` | enum, optional | `valid` / `expiring_soon` / `expired` / `no_expiry` |
| `department_id` | int, optional | Lọc theo phòng ban |
| `from_issued` | date, optional | Ngày cấp từ |
| `to_issued` | date, optional | Ngày cấp đến |
| `search` | str, optional | Tìm theo tên chứng chỉ, tên NV, mã NV |
| `page` | int, default=1 | |
| `page_size` | int, default=20 | |

### Permissions

| Endpoint | Permission |
|---|---|
| GET list / GET by id / GET employee history | `training:view` |
| POST / PUT / DELETE / download | `training:manage_certificates` |

---

## Schemas

### `CertificateRead`

```python
class CertificateRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str | None

    certificate_name: str
    issuing_organization: str | None
    issued_date: date
    expiry_date: date | None

    # Computed fields
    expiry_status: Literal["valid", "expiring_soon", "expired", "no_expiry"]
    days_until_expiry: int | None   # None nếu no_expiry hoặc đã hết hạn

    related_course_id: int | None
    related_course_name: str | None

    note: str | None
    has_file: bool
    file_name: str | None
    file_size: int | None

    created_by_name: str | None
    created_at: datetime
```

### `CertificateCreate`

```python
class CertificateCreate(BaseModel):
    employee_id: int
    certificate_name: str           # min_length=1, max_length=500
    issuing_organization: str | None = None
    issued_date: date
    expiry_date: date | None = None
    related_course_id: int | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_expiry_after_issued(self) -> "CertificateCreate":
        if self.expiry_date is not None and self.expiry_date <= self.issued_date:
            raise ValueError("expiry_date phải sau issued_date")
        return self
```

### `CertificateUpdate`

```python
class CertificateUpdate(BaseModel):
    certificate_name: str | None = None
    issuing_organization: str | None = None
    issued_date: date | None = None
    expiry_date: date | None = None
    related_course_id: int | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_expiry_after_issued(self) -> "CertificateUpdate":
        if (
            self.expiry_date is not None
            and self.issued_date is not None
            and self.expiry_date <= self.issued_date
        ):
            raise ValueError("expiry_date phải sau issued_date")
        return self
```

### `CertificateListPage`

```python
class CertificateListPage(BaseModel):
    items: list[CertificateRead]
    total: int
    page: int
    page_size: int
```

### Logic tính `expiry_status`

```python
def compute_expiry_status(expiry_date: date | None, today: date) -> str:
    if expiry_date is None:
        return "no_expiry"
    if expiry_date < today:
        return "expired"
    if expiry_date <= today + timedelta(days=30):
        return "expiring_soon"
    return "valid"

def compute_days_until_expiry(expiry_date: date | None, today: date) -> int | None:
    if expiry_date is None or expiry_date < today:
        return None
    return (expiry_date - today).days
```

---

## Service logic

### `certificate_service.py`

**`get_certificates()`:**
1. Base query: `SELECT ec.*, e.employee_code, e.full_name, d.name AS department_name, tc.name AS course_name` FROM `employee_certificates ec JOIN employees e ON ec.employee_id = e.id LEFT JOIN departments d ON e.department_id = d.id LEFT JOIN training_courses tc ON ec.related_course_id = tc.id`
2. Apply filters: `employee_id`, `department_id`, `from_issued`, `to_issued`, `search` (ILIKE trên `certificate_name`, `employee_code`, `full_name`)
3. Filter `expiry_status`: tính điều kiện SQL từ `expiry_date`:
   - `no_expiry`: `expiry_date IS NULL`
   - `expired`: `expiry_date < :today`
   - `expiring_soon`: `expiry_date >= :today AND expiry_date <= :today_plus_30`
   - `valid`: `expiry_date > :today_plus_30`
4. Count total, apply pagination `OFFSET / LIMIT`
5. Map từng row sang `CertificateRead` (gọi `compute_expiry_status`, `compute_days_until_expiry`)

**`get_certificate_or_404(id)`:**
- Query single record + JOIN như trên
- Raise HTTP 404 nếu không tìm thấy

**`create_certificate(data, file, current_user)`:**
1. Parse `CertificateCreate` từ body JSON
2. Kiểm tra `employee_id` tồn tại (`_get_or_404`)
3. Nếu `related_course_id` có, kiểm tra tồn tại
4. Nếu có file upload: upload lên MinIO, lưu `file_path`, `file_name`, `file_size`, `mime_type`
5. Tạo `EmployeeCertificate` record, `session.add()`, `commit()`, `refresh()`
6. Trả `CertificateRead`

**`update_certificate(id, data, file, current_user)`:**
1. `_get_or_404(id)`
2. Apply các field thay đổi
3. Nếu có file mới: xóa file cũ khỏi MinIO (nếu có `file_path`), upload file mới
4. `commit()`, `refresh()`
5. Trả `CertificateRead`

**`delete_certificate(id)`:**
1. `_get_or_404(id)`
2. Nếu có `file_path`: gọi MinIO delete object
3. `session.delete(record)`, `commit()`

**`download_certificate_file(id)`:**
1. `_get_or_404(id)`
2. Nếu không có `file_path`: raise HTTP 404 "Chứng chỉ này không có file"
3. Lấy presigned URL từ MinIO hoặc stream file trực tiếp
4. Trả `StreamingResponse` với header `Content-Disposition: attachment; filename="{file_name}"`

**`get_employee_certificates(employee_id)`:**
1. Query tất cả chứng chỉ của `employee_id`, sắp xếp `issued_date DESC`
2. Trả `list[CertificateRead]`

---

## Thiết kế Frontend

### Tab "Chứng chỉ" trong `TrainingView.vue`

Thêm tab "Chứng chỉ" vào `TabView` hiện có, render component `CertificateTab.vue`.

### `CertificateTab.vue`

**Alert banner (đầu tab):**
- Gọi `GET /training/certificates?expiry_status=expiring_soon&page_size=1` khi mount
- Nếu `total > 0`: hiển thị `Message` severity="warn": `"Có {total} chứng chỉ sắp hết hạn trong 30 ngày tới"` với link filter

**Toolbar:**
- InputText: tìm kiếm theo tên chứng chỉ / mã NV / tên NV
- Select (filter prop): Phòng ban — tùy chọn "Tất cả" + danh sách phòng ban
- Select (filter prop): Trạng thái hết hạn — `[{ label: 'Tất cả', value: null }, { label: 'Còn hiệu lực', value: 'valid' }, { label: 'Sắp hết hạn', value: 'expiring_soon' }, { label: 'Đã hết hạn', value: 'expired' }, { label: 'Vĩnh viễn', value: 'no_expiry' }]`
- DatePicker: Ngày cấp từ
- DatePicker: Ngày cấp đến
- Button: "Thêm chứng chỉ" (icon: plus) → mở dialog

**DataTable:**

| Cột | Nội dung |
|---|---|
| Nhân viên | `{employee_code} — {employee_name}` |
| Phòng ban | `department_name` |
| Tên chứng chỉ | `certificate_name` |
| Tổ chức cấp | `issuing_organization` |
| Ngày cấp | `issued_date` format DD/MM/YYYY |
| Ngày hết hạn | `expiry_date` format DD/MM/YYYY hoặc "Vĩnh viễn" nếu null |
| Trạng thái | Tag màu theo `expiry_status` (xem bảng màu) |
| File | Icon download nếu `has_file = true` |
| Thao tác | Button edit (pencil), Button delete (trash) |

**Màu Tag `expiry_status`:**

| Giá trị | Severity PrimeVue | Label |
|---|---|---|
| `valid` | `success` | Còn hiệu lực |
| `expiring_soon` | `warn` | Sắp hết hạn |
| `expired` | `danger` | Đã hết hạn |
| `no_expiry` | `secondary` | Vĩnh viễn |

**Dialog "Thêm / Sửa chứng chỉ":**
- Select (filter): Nhân viên — `{employee_code} - {employee_name}` (required)
- InputText: Tên chứng chỉ (required)
- InputText: Tổ chức cấp (optional)
- DatePicker: Ngày cấp (required)
- DatePicker: Ngày hết hạn (optional, hiển thị placeholder "Để trống = Vĩnh viễn")
- Select (filter): Khóa đào tạo liên quan (optional) — danh sách từ `GET /training/courses`
- Textarea: Ghi chú (optional)
- FileUpload: Upload file chứng chỉ (PDF, JPG, PNG, max 10MB) — hiển thị tên file hiện tại nếu đang sửa

**Validation phía FE:**
- `expiry_date` không được trước `issued_date` (kiểm tra realtime khi DatePicker thay đổi)

**Pagination:** `Paginator` ở cuối bảng, `page_size` = 20

---

## Cấu trúc file mới / thay đổi

```
backend/
  alembic/versions/0029_create_employee_certificates.py   (NEW)
  app/models/training.py                                   (EDIT: thêm class EmployeeCertificate)
  app/schemas/training.py                                  (EDIT: thêm CertificateRead/Create/Update/ListPage)
  app/services/certificate_service.py                      (NEW)
  app/api/v1/endpoints/training.py                         (EDIT: thêm certificate endpoints)
  app/api/v1/router.py                                     (EDIT: thêm employee certificate history sub-route)
  tests/test_certificates.py                               (NEW)

frontend/
  src/services/trainingService.ts                          (EDIT: thêm certificate types + API calls)
  src/views/training/components/CertificateTab.vue         (NEW)
  src/views/training/TrainingView.vue                      (EDIT: thêm tab "Chứng chỉ")
  src/assets/styles/views/_training.scss                   (EDIT: thêm certificate styles)
```

---

## Kế hoạch theo slice

### Slice 1 — Backend: Certificates CRUD + Expiry

**Tasks:**
1. Migration `0029_create_employee_certificates.py`:
   - `op.create_table("employee_certificates", ...)` với tất cả cột
   - `op.create_index("ix_employee_certificates_employee_id", "employee_certificates", ["employee_id"])`
   - `op.create_index("ix_employee_certificates_expiry_date", "employee_certificates", ["expiry_date"])`
   - FK constraints với `ondelete="CASCADE"` cho employee, `ondelete="SET NULL"` cho course và user
2. Model `EmployeeCertificate(SQLModel, table=True)` trong `app/models/training.py`:
   - `id: Optional[int] = Field(default=None, primary_key=True)`
   - Tất cả cột theo thiết kế model
3. Schemas `CertificateRead`, `CertificateCreate`, `CertificateUpdate`, `CertificateListPage` trong `app/schemas/training.py`
   - Hàm helper `compute_expiry_status()` và `compute_days_until_expiry()`
   - `@model_validator` cho `CertificateCreate` và `CertificateUpdate`
4. Service `certificate_service.py`:
   - `get_certificates()` với tất cả filters + expiry_status SQL condition
   - `get_certificate_or_404()`
   - `create_certificate()` (có MinIO upload)
   - `update_certificate()` (thay thế file cũ)
   - `delete_certificate()` (xóa file MinIO)
   - `download_certificate_file()`
   - `get_employee_certificates()`
5. Endpoints trong `training.py`:
   - `GET /training/certificates` (require `training:view`)
   - `POST /training/certificates` multipart (require `training:manage_certificates`)
   - `GET /training/certificates/{id}` (require `training:view`)
   - `PUT /training/certificates/{id}` multipart (require `training:manage_certificates`)
   - `DELETE /training/certificates/{id}` (require `training:manage_certificates`)
   - `GET /training/certificates/{id}/download` (require `training:manage_certificates`)
6. Sub-route trong `router.py`:
   - `GET /employees/{employee_id}/training/certificates` (require `training:view`)

**Exit criteria:**
- `POST /training/certificates` tạo thành công với và không có file
- `GET /training/certificates?expiry_status=expiring_soon` trả đúng danh sách chứng chỉ trong 30 ngày tới
- `GET /training/certificates?expiry_status=expired` trả đúng chứng chỉ đã hết hạn
- `GET /training/certificates?expiry_status=no_expiry` trả đúng chứng chỉ không có ngày hết hạn
- Upload file, download file hoạt động
- `DELETE` xóa cả record lẫn file MinIO
- `GET /employees/{id}/training/certificates` trả danh sách đúng nhân viên

---

### Slice 2 — Frontend

**Tasks:**
1. Thêm types `CertificateRead`, `CertificateCreate`, `CertificateUpdate`, `CertificateListPage` vào `trainingService.ts`
2. Thêm API calls:
   - `getCertificates(params)` → GET /training/certificates
   - `createCertificate(data, file?)` → POST multipart
   - `updateCertificate(id, data, file?)` → PUT multipart
   - `deleteCertificate(id)` → DELETE
   - `downloadCertificateFile(id)` → GET download
3. Tạo `CertificateTab.vue`:
   - Alert banner expiring_soon (fetch khi mount)
   - Toolbar: search, dept Select, expiry_status Select, from/to DatePicker, nút "Thêm"
   - DataTable với tất cả cột, Tag màu expiry_status, icon download
   - Pagination
   - Dialog form tạo/sửa (validate expiry > issued phía FE)
   - Confirm dialog trước khi xóa
4. Edit `TrainingView.vue`: thêm TabPanel "Chứng chỉ" → render `<CertificateTab />`
5. Edit `_training.scss`: style alert banner, tag colors (dùng PrimeVue severity, không viết CSS riêng cho tag)

**Exit criteria:**
- Tab "Chứng chỉ" xuất hiện trong TrainingView
- Alert banner hiển thị khi có chứng chỉ sắp hết hạn
- Thêm mới chứng chỉ (có file + không có file) thành công
- Sửa chứng chỉ + thay file hoạt động
- Xóa chứng chỉ: file bị xóa khỏi MinIO, row biến khỏi bảng
- Download file hoạt động
- Tag màu đúng: success/warn/danger/secondary
- Filter expiry_status lọc đúng dữ liệu
- Validation FE: expiry_date trước issued_date → hiển thị lỗi, không submit

---

### Slice 3 — Tests

**Tasks:**

Tạo `tests/test_certificates.py`:

```
TestCertificateCRUD:
  - test_create_certificate_without_file
  - test_create_certificate_with_file
  - test_get_certificate_by_id
  - test_update_certificate
  - test_update_certificate_replace_file
  - test_delete_certificate_removes_file
  - test_get_nonexistent_certificate_returns_404

TestCertificateExpiry:
  - test_expiry_status_valid             (expiry_date = today + 60 days → "valid")
  - test_expiry_status_expiring_soon     (expiry_date = today + 15 days → "expiring_soon")
  - test_expiry_status_expiring_boundary (expiry_date = today + 30 days → "expiring_soon")
  - test_expiry_status_expired           (expiry_date = yesterday → "expired")
  - test_expiry_status_no_expiry         (expiry_date = None → "no_expiry")
  - test_days_until_expiry_computed_correctly

TestCertificateFilter:
  - test_filter_by_expiry_status_expiring_soon
  - test_filter_by_expiry_status_expired
  - test_filter_by_expiry_status_no_expiry
  - test_filter_by_expiry_status_valid
  - test_filter_by_employee_id
  - test_filter_by_department_id
  - test_search_by_certificate_name
  - test_search_by_employee_code

TestCertificateValidation:
  - test_create_expiry_before_issued_raises_422
  - test_update_expiry_before_issued_raises_422
  - test_expiry_same_as_issued_raises_422

TestEmployeeCertificateHistory:
  - test_get_employee_certificates_returns_only_that_employee
  - test_get_employee_certificates_nonexistent_employee_returns_404
```

**Exit criteria:**
- Tất cả test pass: `docker exec hrms-backend-1 pytest tests/test_certificates.py -v`
- Coverage expiry_status logic: 5 cases
- Validation errors trả HTTP 422 đúng message

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| MinIO unavailable khi test | Trung bình | Mock MinIO client trong unit tests; integration test dùng MinIO test bucket |
| `expiry_status` filter SQL không tương thích timezone | Thấp | Dùng `date.today()` (Python) truyền làm bind param; không dùng `CURRENT_DATE` SQL |
| File lớn (PDF > 10MB) | Thấp | Validate file size ở endpoint trước khi upload; trả HTTP 413 |
| Xóa file MinIO fail sau khi đã xóa DB record | Thấp | Log warning, không rollback DB (file orphan acceptable); dọn dẹp định kỳ nếu cần |
| `related_course_id` FK null khi khóa bị xóa | Thấp | `SET NULL` ondelete; FE hiển thị "—" nếu `related_course_name = null` |
| Boundary expiring_soon = 30 ngày có thể thay đổi nghiệp vụ | Trung bình | Đặt hằng số `EXPIRY_SOON_DAYS = 30` trong config, dễ thay đổi sau |
