# Kế hoạch triển khai — 12.1. Import dữ liệu hàng loạt

**Phạm vi:** Import hợp đồng · Import nghỉ phép · Import bảo hiểm  
**Phụ thuộc:** 3.7 Import nhân viên ✅ · 4.1 Hợp đồng ✅ · 5.3 Nghỉ phép ✅ · 6.1 Bảo hiểm ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §12.1  
**Đặc điểm:** Không sửa import nhân viên (3.7 đã hoàn thành); mở rộng sang các module còn lại

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Import nhân viên (`/employees/import`) | ✅ Hoàn thành | Plan 3.7 — tham chiếu làm mẫu |
| `employee_import_service.py` | ✅ Hoàn thành | Pattern validate + collect errors |
| `ImportResult`, `ImportRowError` schemas | ✅ Hoàn thành | Tái dùng cho module mới |
| Import hợp đồng | ❌ Chưa có | |
| Import nghỉ phép (leave records) | ❌ Chưa có | |
| Import bảo hiểm (insurance profiles) | ❌ Chưa có | |
| Frontend import UI (tab mới) | ❌ Chưa có | |

---

## Phạm vi 12.1

### Trong phạm vi

- **Import hợp đồng lao động** — tạo `EmployeeContract` hàng loạt từ Excel: mã nhân viên, loại HĐ, ngày hiệu lực, ngày hết hạn
- **Import nghỉ phép** — tạo `LeaveRecord` hàng loạt: mã NV, loại phép, ngày bắt đầu, ngày kết thúc
- **Import bảo hiểm** — tạo/cập nhật `EmployeeInsuranceProfile`: mã NV, mã BHXH, mức lương đóng, ngày tham gia
- File mẫu Excel có sheet "Hướng dẫn" cho mỗi loại import
- Validation trước khi import: báo lỗi theo dòng, không fail-fast
- Kết quả import: tổng dòng, thành công, thất bại, danh sách lỗi chi tiết
- Permission riêng cho từng loại import

### Ngoài phạm vi

- Import nhân viên (đã có ở 3.7)
- Import danh mục (catalog) — đã có ở admin UI
- Import lương BHXH theo kỳ (thuộc module 7)
- Import KPI scores (thuộc module 10)

---

## API Design

### Endpoints — prefix `/api/v1/imports`

```
GET  /imports/contracts/template          → Download file mẫu Excel hợp đồng
POST /imports/contracts                   → Upload + xử lý import hợp đồng
     Body: multipart/form-data { file: .xlsx }
     Response: ImportResult

GET  /imports/leave-records/template     → Download file mẫu Excel nghỉ phép
POST /imports/leave-records              → Upload + xử lý import nghỉ phép
     Response: ImportResult

GET  /imports/insurance/template         → Download file mẫu Excel bảo hiểm
POST /imports/insurance                  → Upload + xử lý import bảo hiểm
     Response: ImportResult
```

### Permissions

| Endpoint | Permission |
|---|---|
| Import hợp đồng | `contracts:edit` |
| Import nghỉ phép | `leaves:edit` |
| Import bảo hiểm | `insurance:edit` |

---

## Template Excel — Hợp đồng

**File mẫu:** `mau_import_hop_dong.xlsx`  
**Sheet "Hợp đồng"** — mỗi hàng = 1 hợp đồng.

| Cột | Header | Trường | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| A | Mã nhân viên | → `employee_id` | ✅ | Tra theo `display_code` hoặc `employee_seq` |
| B | Số hợp đồng | `contract_number` | ✅ | Unique |
| C | Loại văn bản | `document_kind` | ✅ | `labor_contract` / `contract_appendix` |
| D | Mã loại HĐ | `contract_category_code` | ✅ | Tra từ `contract_categories.code` |
| E | Ngày ký | `signed_date` | ✅ | dd/mm/yyyy |
| F | Ngày hiệu lực | `effective_from` | ✅ | dd/mm/yyyy |
| G | Ngày hết hạn | `effective_to` | | dd/mm/yyyy — bỏ trống = vô thời hạn |
| H | Mức lương BHXH | `insurance_salary` | | Số, đơn vị VNĐ |

**Sheet "Hướng dẫn"** — giải thích từng cột, giá trị hợp lệ.

### Validation rules hợp đồng

| Rule | Chi tiết |
|---|---|
| Mã NV tồn tại | Tra `employees` theo display_code; nếu không tìm thấy → lỗi dòng |
| Số HĐ duy nhất | Nếu `contract_number` đã tồn tại → lỗi trùng |
| `effective_from` ≤ `effective_to` | Nếu có cả 2, phải đúng thứ tự |
| `contract_category_code` hợp lệ | Tra từ `contract_categories` |
| `document_kind` hợp lệ | Chỉ `labor_contract` / `contract_appendix` |

---

## Template Excel — Nghỉ phép

**File mẫu:** `mau_import_nghi_phep.xlsx`

| Cột | Header | Trường | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| A | Mã nhân viên | → `employee_id` | ✅ | Tra theo `display_code` |
| B | Mã loại phép | → `leave_type_id` | ✅ | Tra từ `leave_types.code` |
| C | Ngày bắt đầu | `start_date` | ✅ | dd/mm/yyyy |
| D | Ngày kết thúc | `end_date` | ✅ | dd/mm/yyyy |
| E | Nửa ngày | `half_day_type` | | `morning` / `afternoon` / bỏ trống |
| F | Ghi chú | `notes` | | Tối đa 500 ký tự |

### Validation rules nghỉ phép

| Rule | Chi tiết |
|---|---|
| Mã NV tồn tại | Tra employees |
| Mã loại phép hợp lệ | Tra leave_types |
| `start_date` ≤ `end_date` | |
| Không trùng lịch nghỉ | Nếu NV đã có record active trong khoảng ngày → cảnh báo (warning, không chặn) |

---

## Template Excel — Bảo hiểm

**File mẫu:** `mau_import_bao_hiem.xlsx`

| Cột | Header | Trường | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| A | Mã nhân viên | → `employee_id` | ✅ | |
| B | Mã BHXH | `bhxh_code` | ✅ | |
| C | Ngày tham gia | `participation_date` | ✅ | dd/mm/yyyy |
| D | Mức lương đóng | `insurance_salary` | ✅ | Số, VNĐ |
| E | Mã bệnh viện KCB | `bhyt_clinic_code` | | Tra từ `bhyt_clinics.code` |
| F | Trạng thái | `status` | | `active` / `suspended` (mặc định: `active`) |

### Validation rules bảo hiểm

| Rule | Chi tiết |
|---|---|
| Mã NV tồn tại và active | |
| Mã BHXH unique | Nếu đã tồn tại → update thay vì tạo mới (upsert by `bhxh_code`) |
| `insurance_salary` > 0 | |
| Bệnh viện KCB hợp lệ | Nếu có, tra từ `bhyt_clinics` |

---

## Service Logic

### Tái dùng `ImportResult` schema từ `employee_import.py`

```python
# Tái dùng từ app/schemas/employee_import.py
class ImportResult(BaseModel):
    total_rows: int
    success_count: int
    error_count: int
    warning_count: int
    errors: list[ImportRowError]    # [{row, field, message}]
    warnings: list[ImportRowError]
```

### Các service mới

```
backend/app/services/
├── contract_import_service.py     ← NEW
│   ├── generate_template() → io.BytesIO
│   └── process_import(session, file_bytes) → ImportResult
├── leave_record_import_service.py ← NEW
│   ├── generate_template() → io.BytesIO
│   └── process_import(session, file_bytes) → ImportResult
└── insurance_import_service.py    ← NEW
    ├── generate_template() → io.BytesIO
    └── process_import(session, file_bytes) → ImportResult
```

### Pattern xử lý (copy từ employee_import_service.py)

```python
async def process_import(session, file_bytes: bytes) -> ImportResult:
    wb = load_workbook(BytesIO(file_bytes))
    ws = wb.active
    errors, warnings, success = [], [], 0

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not any(row):        # dòng trống → skip
            continue
        try:
            obj = _validate_and_build(session, row)
            session.add(obj)
            await session.flush()
            success += 1
        except ValidationError as e:
            errors.append(ImportRowError(row=row_idx, ...))

    await session.commit()
    return ImportResult(total_rows=..., success_count=success, ...)
```

### Giới hạn

- Max **1000 dòng/lần** — nhất quán với employee import
- File size max: **5MB**
- Chỉ nhận `.xlsx`, không nhận `.xls` hay `.csv`

---

## Endpoint mới — `app/api/v1/endpoints/data_imports.py`

```python
router = APIRouter()

@router.get("/contracts/template")
async def download_contract_template(
    _: User = require_permission("contracts:edit"),
) -> StreamingResponse:
    buf = contract_import_service.generate_template()
    return StreamingResponse(buf, media_type=XLSX_MIME,
        headers={"Content-Disposition": 'attachment; filename="mau_import_hop_dong.xlsx"'})

@router.post("/contracts", response_model=ImportResult)
async def import_contracts(
    file: UploadFile = File(...),
    _: User = require_permission("contracts:edit"),
    session: AsyncSession = Depends(get_session),
) -> ImportResult:
    data = await file.read()
    return await contract_import_service.process_import(session, data)
```

Đăng ký trong `router.py`:
```python
from app.api.v1.endpoints import data_imports
router.include_router(data_imports.router, prefix="/imports", tags=["Import dữ liệu"])
```

---

## Frontend Design

### Route mới

```
/data/import   →   DataImportView.vue
```

### Layout

```
┌─ TabView ────────────────────────────────────────┐
│ [Nhân viên] [Hợp đồng] [Nghỉ phép] [Bảo hiểm]  │
├──────────────────────────────────────────────────┤
│ Hướng dẫn: Tải mẫu → Điền dữ liệu → Upload      │
│                                                   │
│ [↓ Tải file mẫu]                                 │
│                                                   │
│ ┌─ FileUpload ────────────────────────────────┐  │
│ │ Kéo thả hoặc chọn file .xlsx (tối đa 5MB)  │  │
│ └─────────────────────────────────────────────┘  │
│                                                   │
│ [Xem trước dữ liệu] [Bắt đầu import]            │
│                                                   │
│ ┌─ Kết quả (sau khi import) ──────────────────┐  │
│ │ ✅ Thành công: 47 dòng                       │  │
│ │ ❌ Lỗi: 3 dòng                               │  │
│ │ [Dòng 5] Mã NV "NV-001" không tồn tại       │  │
│ │ [Dòng 12] Số HĐ "HD-2024-001" đã tồn tại   │  │
│ └─────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

**PrimeVue components:** `TabView`, `TabPanel`, `FileUpload`, `DataTable` (preview), `Message`

### Service `dataImportService.ts` (file mới)

```typescript
const BASE = '/imports'
export default {
  downloadContractTemplate: () =>
    api.get(`${BASE}/contracts/template`, { responseType: 'blob' }),
  importContracts: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<ImportResult>(`${BASE}/contracts`, form)
  },
  // ... tương tự cho leave-records, insurance
}
```

---

## Cấu trúc file

```
backend/app/
├── services/
│   ├── contract_import_service.py      ← NEW
│   ├── leave_record_import_service.py  ← NEW
│   └── insurance_import_service.py     ← NEW
├── api/v1/endpoints/
│   └── data_imports.py                 ← NEW (6 endpoints)
└── api/v1/router.py                    ← UPDATE (đăng ký /imports)

frontend/src/
├── services/
│   └── dataImportService.ts            ← NEW
├── views/data/
│   └── DataImportView.vue              ← NEW (tab per module)
└── router/index.ts                     ← UPDATE (thêm /data/import)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend Contract Import

**Việc cần làm:**
1. Tạo `contract_import_service.py`:
   - `generate_template()` — 2 sheet (Data + Hướng dẫn)
   - `process_import(session, file_bytes)` — validate + create EmployeeContract
   - Validation: mã NV, contract_number unique, contract_category, date order
2. Tạo `data_imports.py` endpoint — 2 routes: template + import
3. Đăng ký router prefix `/imports`
4. Viết `tests/test_contract_import.py`:
   - `test_import_success` — 5 hợp đồng valid → all succeed
   - `test_import_invalid_employee` — mã NV sai → lỗi dòng
   - `test_import_duplicate_contract_number` → lỗi dòng
   - `test_import_date_order_error` — effective_to < effective_from → lỗi
   - `test_template_download` → 200, xlsx content-type

**Verify:** `pytest tests/test_contract_import.py -v` pass.

---

### Slice 2 — Backend Leave Records + Insurance Import

**Việc cần làm:**
1. Tạo `leave_record_import_service.py`:
   - `generate_template()` — 2 sheet
   - `process_import()` — validate + create LeaveRecord
   - Validation: mã NV, leave_type, date order, cảnh báo trùng lịch
2. Tạo `insurance_import_service.py`:
   - `generate_template()` — 2 sheet
   - `process_import()` — upsert EmployeeInsuranceProfile by bhxh_code
   - Validation: mã NV active, insurance_salary > 0, bhyt_clinic hợp lệ
3. Bổ sung endpoints vào `data_imports.py`
4. Bổ sung tests:
   - `test_leave_import_success` — 3 records valid
   - `test_leave_import_date_order_error`
   - `test_insurance_import_upsert` — bhxh_code đã tồn tại → update
   - `test_insurance_import_inactive_employee` → lỗi

**Verify:** `pytest tests/test_contract_import.py tests/test_leave_record_import.py tests/test_insurance_import.py -v` pass.

---

### Slice 3 — Frontend Import UI

**Việc cần làm:**
1. Tạo `dataImportService.ts` — 6 functions (3 template download + 3 upload)
2. Tạo `DataImportView.vue`:
   - TabView 4 tab: Nhân viên (link đến 3.7 UI), Hợp đồng, Nghỉ phép, Bảo hiểm
   - Mỗi tab: hướng dẫn, FileUpload, preview DataTable (5 dòng đầu), kết quả
   - Loading state khi đang xử lý
   - Error panel hiển thị lỗi theo dòng (DataTable: row, field, message)
3. Cập nhật router + AppMenu
4. Chạy `vue-tsc --noEmit` — clean

**Verify:** Upload file thử, kết quả hiển thị đúng.

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| File Excel sai format (user upload file khác) | Validate file extension + magic bytes; trả 400 với message rõ |
| Mã NV không nhất quán (dùng nhiều format) | Tra cứu theo `display_code` + fallback theo `employee_seq`; hướng dẫn trong sheet mẫu |
| Import nhiều hơn 1000 dòng | Chặn với message "Tối đa 1000 dòng/lần, chia nhỏ file" |
| Partial commit (một số thành công, một số lỗi) | Dùng `flush()` per row, commit toàn bộ thành công khi kết thúc; rollback chỉ dòng lỗi |
| Đồng thời 2 user import cùng module | Không lock — chấp nhận race condition ở mức business logic; validate unique sau mỗi flush |

---

## Checklist trước khi đánh dấu hoàn thành

### Backend

- [ ] `pytest tests/test_contract_import.py` pass
- [ ] `pytest tests/test_leave_record_import.py` pass
- [ ] `pytest tests/test_insurance_import.py` pass
- [ ] Endpoint trả đúng lỗi khi không có permission
- [ ] File mẫu có sheet Hướng dẫn rõ ràng

### Frontend

- [ ] `vue-tsc --noEmit` clean
- [ ] Tab Hợp đồng / Nghỉ phép / Bảo hiểm load đúng
- [ ] Upload file thành công → hiển thị kết quả đúng
- [ ] Upload file lỗi → hiển thị lỗi từng dòng rõ ràng
- [ ] Responsive mobile
