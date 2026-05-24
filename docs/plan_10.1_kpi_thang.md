# Kế hoạch triển khai — 10.1. KPI Tháng

**Phạm vi:** Nhập và quản lý điểm KPI hàng tháng cho từng nhân viên · Import Excel  
**Phụ thuộc:** `1.1 Cơ cấu tổ chức` (departments) · `3.1 Hồ sơ nhân viên` (employees)  
**Căn cứ nghiệp vụ:** FEATURES.md §10.1

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `employees` table | ✅ Hoàn thành (3.1) | |
| `departments` table | ✅ Hoàn thành (1.1) | |
| `employee_kpi_monthly` table | ✅ Hoàn thành (10.1 Slice 1) | migration 0030 |
| API CRUD KPI tháng | ✅ Hoàn thành (10.1 Slice 1) | GET/POST/PUT/DELETE /performance/kpi |
| API import Excel KPI | ❌ Chưa có | Slice 2 |
| Tab KPI trong `PerformanceView.vue` | ❌ Chưa có | Slice 3 |

---

## Phạm vi

Theo FEATURES.md §10.1:
> Nhân sự nhập tay hoặc import file Excel điểm KPI hàng tháng cho từng nhân viên  
> Thông tin bao gồm: mã nhân viên, họ tên, năm, tháng, điểm KPI, ghi chú, người nhập

**Trong phạm vi:**
- CRUD điểm KPI tháng (nhập tay từng bản ghi)
- Import hàng loạt từ file Excel (.xlsx)
- Export template Excel để nhân sự tải về nhập liệu
- Unique constraint: mỗi nhân viên chỉ có 1 bản ghi KPI cho mỗi (năm, tháng)
- Filter danh sách theo năm, tháng, phòng ban, tìm kiếm tên/mã NV

**Ngoài phạm vi:**
- Tính toán xếp loại cuối năm (thuộc 10.2)
- Phê duyệt quy trình KPI đa cấp
- KPI nhóm / KPI theo mục tiêu (OKR)

---

## Thiết kế data model

### Bảng `employee_kpi_monthly`

| Cột | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `employee_id` | INTEGER | FK employees(id) CASCADE NOT NULL | |
| `year` | SMALLINT | NOT NULL | Năm (VD: 2026) |
| `month` | SMALLINT | NOT NULL | Tháng (1–12) |
| `score` | NUMERIC(5,2) | NOT NULL | Điểm KPI (0–100) |
| `note` | TEXT | nullable | Ghi chú |
| `created_by_id` | INTEGER | FK users(id) SET NULL, nullable | Người nhập |
| `created_at` | TIMESTAMP | NOT NULL, default now() | |
| `updated_at` | TIMESTAMP | NOT NULL, default now() | |

**Unique constraint:** `uq_employee_kpi_year_month` trên `(employee_id, year, month)`

**Indexes:**
- `ix_employee_kpi_monthly_employee_id` trên `(employee_id)`
- `ix_employee_kpi_monthly_year_month` trên `(year, month)`

**Migration file:** `alembic/versions/0030_create_employee_kpi_monthly.py`

---

## Thiết kế API

### Endpoints

```
GET    /performance/kpi
       ?year=&month=&department_id=&search=&page=1&page_size=20
       → KpiMonthlyListPage

POST   /performance/kpi
       body: KpiMonthlyCreate (JSON)
       → KpiMonthlyRead

GET    /performance/kpi/{id}
       → KpiMonthlyRead

PUT    /performance/kpi/{id}
       body: KpiMonthlyUpdate (JSON)
       → KpiMonthlyRead

DELETE /performance/kpi/{id}
       → 204 No Content

POST   /performance/kpi/import
       Content-Type: multipart/form-data
       file: UploadFile (.xlsx)
       ?year=&month=
       → KpiImportResult

GET    /performance/kpi/template
       → StreamingResponse (.xlsx) — file mẫu import
```

### Query parameters chi tiết

| Param | Kiểu | Mô tả |
|---|---|---|
| `year` | int, optional | Lọc theo năm |
| `month` | int (1–12), optional | Lọc theo tháng |
| `department_id` | int, optional | Lọc theo phòng ban |
| `search` | str, optional | Tìm theo tên NV, mã NV |
| `page` | int, default=1 | |
| `page_size` | int, default=20 | |

### Permissions

| Endpoint | Permission |
|---|---|
| GET list / GET by id | `performance:view` |
| POST / PUT / DELETE / import | `performance:manage_kpi` |
| GET template | `performance:view` |

---

## Schemas

### `KpiMonthlyRead`

```python
class KpiMonthlyRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str | None
    year: int
    month: int
    score: Decimal          # NUMERIC(5,2)
    note: str | None
    created_by_name: str | None
    created_at: datetime
    updated_at: datetime
```

### `KpiMonthlyCreate`

```python
class KpiMonthlyCreate(BaseModel):
    employee_id: int
    year: int               = Field(ge=2000, le=2100)
    month: int              = Field(ge=1, le=12)
    score: Decimal          = Field(ge=0, le=100)
    note: str | None = None
```

### `KpiMonthlyUpdate`

```python
class KpiMonthlyUpdate(BaseModel):
    score: Decimal | None   = Field(default=None, ge=0, le=100)
    note: str | None = None
```

### `KpiMonthlyListPage`

```python
class KpiMonthlyListPage(BaseModel):
    items: list[KpiMonthlyRead]
    total: int
    page: int
    page_size: int
```

### `KpiImportResult`

```python
class KpiImportResult(BaseModel):
    created: int        # số bản ghi tạo mới
    updated: int        # số bản ghi cập nhật (đã tồn tại → ghi đè)
    skipped: int        # số dòng bỏ qua (lỗi dữ liệu)
    errors: list[str]   # mô tả lỗi từng dòng bị bỏ qua
```

---

## Format file Excel import

### Template file (GET /performance/kpi/template)

Sheet "KPI_Tháng":

| Cột A | Cột B | Cột C | Cột D | Cột E |
|---|---|---|---|---|
| Mã nhân viên (*) | Họ và tên | Năm (*) | Tháng (*) | Điểm KPI (*) |
| VD: HH001 | Nguyễn Văn A | 2026 | 1 | 85.5 |

- Hàng 1: header (bold, nền `#1F4E79`, chữ trắng)
- Hàng 2+: dữ liệu mẫu màu xám nhạt (hướng dẫn)
- Cột "Họ và tên": chỉ tham khảo, không dùng để import — hệ thống tra theo mã NV
- Cột bắt buộc đánh dấu `(*)` trong header

### Logic xử lý import

1. Đọc sheet đầu tiên của file `.xlsx`
2. Bỏ qua hàng 1 (header)
3. Với mỗi hàng dữ liệu:
   - Tra `employee_id` từ `employee_code` (mã NV) — nếu không tìm thấy: ghi lỗi, skip
   - Validate `year` (2000–2100), `month` (1–12), `score` (0–100) — nếu sai: ghi lỗi, skip
   - Nếu đã tồn tại `(employee_id, year, month)`: **UPDATE** score + note
   - Nếu chưa tồn tại: **INSERT** mới
4. Trả `KpiImportResult` với counts và danh sách lỗi

---

## Service logic

### `kpi_service.py`

**`get_kpi_list()`:**
1. JOIN `employee_kpi_monthly` + `employees` + `employee_job_records (is_current)` + `departments`
2. Apply filters: `year`, `month`, `department_id`, `search` (ILIKE tên NV, mã NV)
3. COUNT total, paginate OFFSET/LIMIT
4. Trả `KpiMonthlyListPage`

**`create_kpi(data, created_by_id)`:**
1. Kiểm tra `employee_id` tồn tại
2. Kiểm tra unique `(employee_id, year, month)` — nếu trùng: raise HTTP 409 "Đã tồn tại điểm KPI tháng {month}/{year} của nhân viên này"
3. INSERT, trả `KpiMonthlyRead`

**`update_kpi(id, data)`:**
1. `_get_or_404(id)`
2. Apply `score`, `note` nếu có
3. UPDATE `updated_at`, trả `KpiMonthlyRead`

**`delete_kpi(id)`:**
1. `_get_or_404(id)`, DELETE

**`import_kpi_excel(file, created_by_id)`:**
1. Đọc workbook `openpyxl.load_workbook(BytesIO(await file.read()))`
2. Lấy sheet đầu tiên
3. Build `employee_code_map: dict[str, int]` từ bảng `employees` (tra một lần)
4. Xử lý từng hàng, build upsert list
5. Batch upsert qua `INSERT ... ON CONFLICT (employee_id, year, month) DO UPDATE SET score=..., note=..., updated_at=...`
6. Trả `KpiImportResult`

**`get_kpi_template()`:**
- Tạo workbook Excel mẫu với openpyxl, trả bytes

---

## Thiết kế Frontend

### `PerformanceView.vue` (NEW)

View chính của module 10, cấu trúc `Tabs`:
- Tab "KPI Tháng" → `KpiMonthlyTab.vue`
- Tab "Đánh giá Cuối năm" → `YearlyReviewTab.vue` (10.2)
- Tab "Báo cáo" → `PerformanceReportTab.vue` (10.4)

Route: `/performance`

### `KpiMonthlyTab.vue`

**Toolbar:**
- Select (filter): Năm — danh sách năm từ năm hiện tại về trước
- Select (filter): Tháng — "Tất cả" + 1–12
- Select (filter): Phòng ban — "Tất cả" + danh sách phòng ban
- InputText: Tìm kiếm tên NV / mã NV
- Button: "Nhập KPI" (icon: plus) → mở dialog
- Button: "Import Excel" (icon: upload) → mở dialog import
- Button: "Tải mẫu" (icon: download) → gọi `GET /performance/kpi/template`

**DataTable:**

| Cột | Nội dung |
|---|---|
| Mã NV | `employee_code` |
| Họ và tên | `employee_name` |
| Phòng ban | `department_name` |
| Năm | `year` |
| Tháng | `month` |
| Điểm KPI | `score` (1 chữ số thập phân) |
| Ghi chú | `note` (truncate 50 ký tự) |
| Người nhập | `created_by_name` |
| Thao tác | Button edit (pencil), Button delete (trash) |

**Dialog "Nhập / Sửa KPI":**
- Select (filter): Nhân viên — `{employee_code} - {employee_name}` (disabled khi sửa)
- InputNumber: Năm (required, ge=2000)
- Select: Tháng (required, 1–12)
- InputNumber: Điểm KPI (required, 0–100, step=0.1)
- Textarea: Ghi chú (optional)

**Dialog "Import Excel":**
- FileUpload: chọn file `.xlsx` (max 5MB)
- Hiển thị kết quả sau import: "Đã tạo {created}, cập nhật {updated}, bỏ qua {skipped}"
- Nếu có `errors`: hiển thị danh sách lỗi trong Message severity="warn"

**Pagination:** `Paginator` cuối bảng, `page_size` = 20

---

## Cấu trúc file mới / thay đổi

```
backend/
  alembic/versions/0030_create_employee_kpi_monthly.py   (NEW)
  app/models/performance.py                               (NEW)
  app/schemas/performance.py                              (NEW)
  app/services/kpi_service.py                             (NEW)
  app/api/v1/endpoints/performance.py                     (NEW)
  app/api/v1/router.py                                    (EDIT: đăng ký router /performance)
  tests/test_kpi_monthly.py                               (NEW)

frontend/
  src/services/performanceService.ts                      (NEW)
  src/views/performance/PerformanceView.vue               (NEW)
  src/views/performance/components/KpiMonthlyTab.vue      (NEW)
  src/router/index.ts                                     (EDIT: thêm route /performance)
  src/assets/styles/views/_performance.scss               (NEW)
```

---

## Kế hoạch theo slice

### Slice 1 — Backend: CRUD KPI Tháng

**Tasks:**
1. Migration `0030_create_employee_kpi_monthly.py`
2. Model `EmployeeKpiMonthly(SQLModel, table=True)` trong `app/models/performance.py`
3. Schemas `KpiMonthlyRead`, `KpiMonthlyCreate`, `KpiMonthlyUpdate`, `KpiMonthlyListPage` trong `app/schemas/performance.py`
4. Service `kpi_service.py`: `get_kpi_list`, `get_kpi`, `create_kpi`, `update_kpi`, `delete_kpi`
5. Endpoints `GET/POST /performance/kpi`, `GET/PUT/DELETE /performance/kpi/{id}`
6. Đăng ký router trong `router.py`

**Exit criteria:**
- POST tạo bản ghi KPI thành công
- POST trùng (employee_id, year, month) → HTTP 409
- GET list filter theo năm/tháng/dept đúng
- PUT/DELETE hoạt động
- Validate score 0–100 → 422 nếu sai

---

### Slice 2 — Backend: Import Excel + Template

**Tasks:**
1. Thêm `KpiImportResult` schema
2. Thêm `import_kpi_excel()` vào service (đọc xlsx, batch upsert)
3. Thêm `get_kpi_template()` service (tạo file mẫu)
4. Endpoint `POST /performance/kpi/import` (multipart)
5. Endpoint `GET /performance/kpi/template`

**Exit criteria:**
- Import file hợp lệ: đúng `created` + `updated` + `skipped`
- Mã NV không tồn tại → dòng vào `skipped`, không crash
- Score ngoài 0–100 → dòng vào `skipped`
- Import file có dòng đã tồn tại → cập nhật (upsert), không duplicate
- GET template → file .xlsx tải được, có đúng cấu trúc header

---

### Slice 3 — Frontend

**Tasks:**
1. Tạo `performanceService.ts` với types + API calls
2. Tạo `PerformanceView.vue` với Tabs (3 tabs placeholder cho 10.2, 10.4)
3. Tạo `KpiMonthlyTab.vue`: toolbar, DataTable, dialog nhập/sửa, dialog import
4. Thêm route `/performance` vào `router/index.ts`
5. Tạo `_performance.scss` (styles toàn module)

**Exit criteria:**
- Route `/performance` navigate được
- Tab "KPI Tháng" hiển thị danh sách, filter đúng
- Nhập KPI tay, sửa, xóa hoạt động
- Import Excel: hiển thị kết quả sau import
- Tải file mẫu thành công

---

### Slice 4 — Tests

Tạo `tests/test_kpi_monthly.py`:

```
TestKpiCRUD:
  - test_create_kpi_success
  - test_create_kpi_duplicate_returns_409
  - test_create_kpi_invalid_score_returns_422   (score = 150)
  - test_create_kpi_invalid_month_returns_422   (month = 13)
  - test_update_kpi_score
  - test_delete_kpi
  - test_get_nonexistent_returns_404

TestKpiList:
  - test_list_filter_by_year
  - test_list_filter_by_month
  - test_list_filter_by_department
  - test_list_search_by_employee_code
  - test_pagination

TestKpiImport:
  - test_import_creates_new_records
  - test_import_updates_existing_records         (upsert)
  - test_import_skips_invalid_employee_code
  - test_import_skips_invalid_score
  - test_import_result_counts_correct
  - test_import_non_xlsx_returns_422
```

**Exit criteria:**
- Tất cả test pass: `docker exec hrms-backend-1 pytest tests/test_kpi_monthly.py -v`

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| Import file Excel định dạng không đúng cột | Trung bình | Validate header row; trả lỗi rõ ràng nếu thiếu cột bắt buộc |
| Import >1000 dòng → chậm | Trung bình | Dùng batch INSERT ON CONFLICT, không loop từng record |
| `score` nhập sai format (dấu phẩy thay dấu chấm trong Excel VN) | Trung bình | Normalize giá trị: `str(cell).replace(",", ".")` trước khi parse |
| Unique constraint fail không bắt được ở service | Thấp | Dùng `INSERT ... ON CONFLICT DO UPDATE` thay vì check-then-insert |
| Xóa KPI tháng ảnh hưởng đến đánh giá cuối năm đã lưu | Thấp | Điểm cuối năm tính on-the-fly (không lưu denorm) — xóa KPI tháng sẽ tự động ảnh hưởng |
