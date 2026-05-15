# Kế hoạch thực hiện — 3.7. Import/Export nhân viên

**Phạm vi:** Import hàng loạt + Export danh sách + Export hồ sơ cá nhân  
**Phụ thuộc:** `1.2 RBAC` ✅ · `3.1 Thông tin cá nhân` ✅ · `3.3 Hồ sơ công việc` ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| `openpyxl` (đọc/ghi Excel) | ❌ Chưa có — phải thêm vào requirements |
| Pattern import hàng loạt | ✅ Tham chiếu: `administrative_import_service.py` |
| Endpoint list employees (filter: keyword, status, is_active) | ✅ Đã có |
| Endpoint `GET /employees/{id}` kèm sub-resources | ✅ Đã có |
| Frontend ImportHistoryView | ✅ Tham chiếu: `AdministrativeImportHistoryView.vue` |

---

## Phạm vi 3.7

| Tính năng | Chi tiết |
|---|---|
| **Import danh sách** | Upload Excel theo mẫu → tạo hàng loạt nhân viên + job record |
| **Export danh sách** | Tải về Excel tất cả nhân viên theo filter hiện tại |
| **Export hồ sơ đầy đủ** | 1 file Excel nhiều sheet cho 1 nhân viên |
| PDF | ❌ Defer — không có thư viện phù hợp, phức tạp; Excel đã đủ cho HR |

---

## Thư viện

Chỉ dùng **`openpyxl`** — đủ để đọc file upload và ghi file download, không cần pandas.

```
# Thêm vào requirements.txt:
openpyxl>=3.1.0
```

Sau khi thêm: `docker compose build backend` (hoặc `pip install openpyxl` trong container đang chạy để dev nhanh).

---

## Thiết kế: Import

### Template Excel (file mẫu)

**Sheet "Nhân viên"** — mỗi hàng = 1 nhân viên. Row 1 = header cố định.

| Cột | Tên cột header | Trường | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| A | Họ và tên | `full_name` | ✅ | |
| B | Họ | `last_name` | ✅ | |
| C | Tên | `first_name` | ✅ | |
| D | Ngày sinh | `date_of_birth` | ✅ | dd/mm/yyyy |
| E | Giới tính | `gender` | ✅ | nam / nữ / khác |
| F | Số CCCD/CMND | `id_number` | ✅ | |
| G | Ngày cấp CCCD | `id_issued_on` | ✅ | dd/mm/yyyy |
| H | Nơi cấp CCCD | `id_issued_by` | ✅ | |
| I | Trạng thái | `status` | ✅ | probation / official / long_leave |
| J | Ngày vào làm | `start_date` | ✅ | dd/mm/yyyy |
| K | Số điện thoại | `phone_number` | | |
| L | Email cá nhân | `personal_email` | | |
| M | Mã số thuế | `personal_tax_code` | | |
| N | Số BHXH | `bhxh_code` | | |
| O | Phòng ban (mã hoặc tên) | → `department_id` | | Tra cứu từ catalog |
| P | Chức danh (tên) | → `job_title_id` | | Tra cứu từ catalog |
| Q | Ngày bắt đầu thử việc | `probation_start_date` | | dd/mm/yyyy |
| R | Ngày kết thúc thử việc | `probation_end_date` | | dd/mm/yyyy |

**Sheet "Hướng dẫn"** — giải thích từng cột, giá trị hợp lệ, ví dụ.

### API endpoint tải mẫu

```
GET /api/v1/employees/import/template
→ StreamingResponse (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
→ Filename: mau_import_nhan_vien.xlsx
→ Quyền: employees:edit
```

### API endpoint upload import

```
POST /api/v1/employees/import
→ multipart/form-data: file (UploadFile .xlsx)
→ Response 200: ImportResult
→ Quyền: employees:edit
→ Audit: IMPORT_EMPLOYEES
```

### Schema kết quả import

```python
class ImportRowError(BaseModel):
    row:     int     # số dòng trong Excel (bắt đầu từ 2)
    column:  str     # tên cột, VD: "Ngày sinh"
    message: str     # mô tả lỗi

class ImportResult(BaseModel):
    total:   int
    success: int
    failed:  int
    errors:  list[ImportRowError]
    created_ids: list[int]   # ID các nhân viên đã tạo thành công
```

### Logic import

```
1. Đọc file, bỏ qua dòng trống
2. Validate từng dòng:
   - Trường bắt buộc không rỗng
   - Định dạng ngày hợp lệ (dd/mm/yyyy → date)
   - gender trong {nam, nữ, khác} → map sang {male, female, other}
   - status trong {probation, official, long_leave}
   - id_number chưa tồn tại trong DB (kiểm tra trước khi insert)
   - department: tra cứu theo code rồi name (case-insensitive)
   - job_title: tra cứu theo name (case-insensitive)
3. Collect errors — không dừng khi gặp lỗi
4. Với dòng hợp lệ: tạo Employee + (nếu có dept) tạo EmployeeJobRecord
5. Commit trong transaction per row (lỗi 1 row không rollback cả batch)
6. Trả về ImportResult
```

**Lưu ý:** Không có bảng import history riêng — kết quả trả về trực tiếp trong response. Nếu cần lịch sử, lưu vào audit_log với action `IMPORT_EMPLOYEES` và new_data = tổng kết.

---

## Thiết kế: Export danh sách

### API

```
GET /api/v1/employees/export
    Query params: keyword, status, is_active (giống /employees list)
→ StreamingResponse (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
→ Filename: danh_sach_nhan_vien_{date}.xlsx
→ Quyền: employees:view
```

### Cấu trúc file Excel

**1 sheet "Danh sách nhân viên"**

| Cột | Nội dung |
|---|---|
| A | Mã nhân viên (display_code) |
| B | Họ và tên |
| C | Ngày sinh |
| D | Giới tính |
| E | Số CCCD/CMND |
| F | Điện thoại |
| G | Email |
| H | Trạng thái |
| I | Ngày vào làm |
| J | Phòng ban hiện tại |
| K | Chức danh hiện tại |
| L | Ngày nghỉ việc |

Phòng ban + chức danh lấy từ `current_job` (JOIN employee_job_records WHERE is_current=TRUE).

**Giới hạn:** Tối đa 5.000 nhân viên một lần export (ngăn OOM). Nếu vượt → trả 400 với thông báo hướng dẫn dùng filter.

---

## Thiết kế: Export hồ sơ đầy đủ

### API

```
GET /api/v1/employees/{id}/export
→ StreamingResponse (.xlsx)
→ Filename: ho_so_{display_code}_{full_name}.xlsx
→ Quyền: employees:view
```

### Cấu trúc file Excel (multi-sheet)

| Sheet | Nội dung |
|---|---|
| Thông tin cá nhân | Họ tên, ngày sinh, CCCD, hộ chiếu, liên lạc, thuế |
| Công việc | Lịch sử bản ghi công việc (phòng ban, chức danh, ngày hiệu lực) |
| Học vấn | Trường, ngành, trình độ, năm tốt nghiệp |
| Người thân | Danh sách người thân |
| Tài khoản ngân hàng | Số TK, ngân hàng, chi nhánh |

---

## Cấu trúc file backend

```
backend/app/services/employee_import_service.py   (NEW)
backend/app/services/employee_export_service.py   (NEW)
backend/app/schemas/employee_import.py             (NEW)
backend/app/api/v1/endpoints/employee_io.py        (NEW)  ← "io" = import/output
```

Đăng ký vào `router.py` với prefix `/employees`.

> **Lý do file riêng:** `employees.py` đã lớn (~1000 dòng). Tách import/export ra `employee_io.py` để tránh conflict và dễ review.

---

## Frontend

### Tích hợp vào EmployeeListView

Thêm 2 nút vào header của `EmployeeListView.vue`:

```
[▼ Tải về Excel]   [↑ Import Excel]
```

**Export:** Click → gọi service → trình duyệt download file (dùng `<a>` blob hoặc direct URL với JWT header).

**Import:**
- Dialog upload file
- Sau khi upload: hiển thị kết quả (bảng lỗi nếu có, summary thành công/thất bại)
- Nút "Tải file mẫu" trong dialog

### Component mới

```
frontend/src/views/employees/ImportDialog.vue
```

Layout dialog:

```
┌─────────────────────────────────────────────────────┐
│ Import nhân viên từ Excel                      [×]  │
├─────────────────────────────────────────────────────┤
│ [Tải file mẫu .xlsx]                               │
│                                                     │
│ ┌──────────────────────────────────────────────┐   │
│ │   📂 Chọn file .xlsx hoặc kéo thả vào đây   │   │
│ │         tên_file.xlsx (125 KB)               │   │
│ └──────────────────────────────────────────────┘   │
│                                                     │
│                        [Hủy]  [Tải lên & Import]   │
├─────────────────────────────────────────────────────┤
│ KẾT QUẢ (sau khi upload):                          │
│ ✅ Thành công: 45 nhân viên                        │
│ ❌ Lỗi: 3 dòng                                     │
│                                                     │
│ Dòng │ Cột        │ Lỗi                            │
│  3   │ Ngày sinh  │ Định dạng không hợp lệ         │
│  7   │ Giới tính  │ Giá trị phải là nam/nữ/khác    │
│ 12   │ Số CCCD    │ Đã tồn tại trong hệ thống      │
└─────────────────────────────────────────────────────┘
```

### Service bổ sung `employeeService.ts`

```typescript
export interface ImportRowError {
  row:     number
  column:  string
  message: string
}

export interface ImportResult {
  total:       number
  success:     number
  failed:      number
  errors:      ImportRowError[]
  created_ids: number[]
}

// Methods bổ sung:
importEmployees:       (formData: FormData) => api.post<ImportResult>('/employees/import', formData, ...)
downloadImportTemplate: () => /* trigger download of /employees/import/template */
exportEmployees:       (params) => /* trigger download of /employees/export */
exportEmployeeProfile: (id: number) => /* trigger download of /employees/{id}/export */
```

**Download pattern:** Vì các endpoint trả `StreamingResponse` nhưng cần JWT header, không thể dùng `window.open()`. Dùng `api.get(..., { responseType: 'blob' })` rồi tạo Object URL và click `<a>`.

---

## `employeeService.ts` — download helper

```typescript
async function downloadBlob(url: string, filename: string, params?: object) {
  const res = await api.get(url, { responseType: 'blob', params })
  const href = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = href; a.download = filename; a.click()
  URL.revokeObjectURL(href)
}
```

---

## Tests

File: `backend/tests/test_employee_io.py`

```
# Import
test_download_template_200              → GET /import/template → 200, content-type xlsx
test_import_success                     → upload valid xlsx → success = N, failed = 0
test_import_partial_errors              → some invalid rows → success + failed + errors
test_import_duplicate_id_number         → row có id_number đã tồn tại → error dòng đó
test_import_missing_required_field      → full_name rỗng → error
test_import_invalid_date_format         → ngày sinh sai format → error
test_import_invalid_gender              → gender = "xyz" → error
test_import_unknown_department          → dept không tìm thấy → tạo employee nhưng không tạo job record (warn)
test_import_viewer_403                  → employees:view không được import → 403

# Export list
test_export_list_200                    → GET /export → 200, content-type xlsx
test_export_list_with_filter            → ?status=probation → chỉ export probation
test_export_list_too_many_422           → > 5000 employees → 400

# Export profile
test_export_profile_200                 → GET /{id}/export → 200, content-type xlsx
test_export_profile_404                 → id không tồn tại → 404
```

---

## Thứ tự triển khai

### Bước 1 — Cài đặt thư viện
1. Thêm `openpyxl>=3.1.0` vào `requirements.txt`
2. Rebuild backend container

### Bước 2 — Backend service & endpoints
1. Tạo `backend/app/schemas/employee_import.py` — `ImportRowError`, `ImportResult`
2. Tạo `backend/app/services/employee_import_service.py`:
   - `generate_template()` → `Workbook` (file mẫu 2 sheet)
   - `process_import(session, file_bytes)` → `ImportResult`
3. Tạo `backend/app/services/employee_export_service.py`:
   - `export_employee_list(session, filters)` → `Workbook`
   - `export_employee_profile(session, employee_id)` → `Workbook`
4. Tạo `backend/app/api/v1/endpoints/employee_io.py` — 4 endpoints
5. Đăng ký vào `router.py`

### Bước 3 — Backend tests
1. Tạo `backend/tests/test_employee_io.py`
2. Chạy pytest → tất cả pass

### Bước 4 — Frontend
1. Thêm helper `downloadBlob()` + 4 service methods vào `employeeService.ts`
2. Tạo `frontend/src/views/employees/ImportDialog.vue` (không scoped style)
3. Thêm nút "Tải về Excel" + "Import Excel" vào `EmployeeListView.vue`

### Bước 5 — Verify
1. Download template → mở Excel kiểm tra sheet Hướng dẫn
2. Import file mẫu có lỗi → xem bảng lỗi hiển thị đúng
3. Export list → mở Excel kiểm tra cột phòng ban/chức danh
4. Export profile → mở Excel kiểm tra đủ sheet

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| File Excel lớn gây OOM | Đọc từng row bằng `openpyxl` read-only mode (`read_only=True`); giới hạn 1000 rows/import |
| Export list quá nhiều | Giới hạn 5000 nhân viên; thông báo lỗi nếu vượt |
| Encoding tên file UTF-8 trong Content-Disposition | Dùng `filename*=UTF-8''...` (RFC 5987) hoặc encode latin-1 với replace |
| Import tạo employee nhưng thiếu dept → job record không được tạo | Ghi warning trong ImportRowError với column="Phòng ban", không fail row |
| Race condition id_number trùng lặp khi import song song | DB có unique constraint trên id_number → catch IntegrityError → đánh dấu failed |
| Người dùng upload file không phải .xlsx | Kiểm tra content-type + extension trước khi parse |

---

## Kết quả mong đợi sau 3.7

- HR tải file mẫu Excel, điền danh sách nhân viên mới, upload → hệ thống tạo hàng loạt
- Lỗi từng dòng được báo rõ (dòng bao nhiêu, cột nào, lỗi gì) — không mất dữ liệu hợp lệ
- Xuất toàn bộ danh sách nhân viên ra Excel để đối soát
- Xuất hồ sơ đầy đủ 1 nhân viên ra Excel nhiều sheet để in ấn / lưu trữ
